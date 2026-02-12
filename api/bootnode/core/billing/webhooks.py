"""Hanzo Commerce webhook handler.

Handles webhooks from Hanzo Commerce (Square-based) for:
- Order events (authorize, complete, cancel)
- Subscription lifecycle events
- Invoice events
- Payment events (paid, failed, refunded)
"""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bootnode.config import get_settings
from bootnode.core.billing.models import PlanTier, SubscriptionStatus
from bootnode.core.billing.tiers import PricingTier, get_tier_limits
from bootnode.core.cache import redis_client
from bootnode.db.models import Project, Subscription
from bootnode.db.session import async_session

logger = structlog.get_logger()

# Map Commerce plan slugs to internal tiers
PLAN_TO_TIER = {
    "bootnode-free": PricingTier.FREE,
    "bootnode-payg": PricingTier.PAY_AS_YOU_GO,
    "bootnode-growth": PricingTier.GROWTH,
    "bootnode-enterprise": PricingTier.ENTERPRISE,
}


class WebhookVerificationError(Exception):
    """Webhook signature verification failed."""

    pass


class CommerceWebhookHandler:
    """Handle webhooks from Hanzo Commerce."""

    def __init__(self) -> None:
        settings = get_settings()
        self.webhook_secret = settings.commerce_webhook_secret

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify HMAC-SHA256 signature from Commerce.

        Args:
            payload: Raw request body bytes
            signature: X-Commerce-Signature header value

        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def handle_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Route webhook event to appropriate handler.

        Args:
            event: Parsed webhook event

        Returns:
            Handler result
        """
        event_type = event.get("type", "")
        event_id = event.get("id", "unknown")
        data = event.get("data", {})

        logger.info(
            "Processing Commerce webhook",
            event_type=event_type,
            event_id=event_id,
        )

        handlers = {
            # Order events
            "order.completed": self.handle_order_completed,
            "order.cancelled": self.handle_order_cancelled,
            # Subscription lifecycle
            "subscription.created": self.handle_subscription_created,
            "subscription.updated": self.handle_subscription_updated,
            "subscription.cancelled": self.handle_subscription_cancelled,
            "subscription.reactivated": self.handle_subscription_reactivated,
            # Invoice events
            "invoice.paid": self.handle_invoice_paid,
            "invoice.payment_failed": self.handle_invoice_failed,
            # Payment events (forwarded through Commerce from Square)
            "payment.paid": self.handle_payment_paid,
            "payment.failed": self.handle_payment_failed,
            "payment.refunded": self.handle_payment_refunded,
            # Customer events
            "customer.created": self.handle_customer_created,
            "customer.updated": self.handle_customer_updated,
        }

        handler = handlers.get(event_type)
        if handler:
            try:
                result = await handler(data)
                return {"handled": True, "event_type": event_type, "result": result}
            except Exception as e:
                logger.error(
                    "Webhook handler failed",
                    event_type=event_type,
                    error=str(e),
                )
                return {"handled": False, "event_type": event_type, "error": str(e)}
        else:
            logger.debug("Unhandled webhook event type", event_type=event_type)
            return {"handled": False, "event_type": event_type, "reason": "unknown_type"}

    # =========================================================================
    # Subscription Handlers
    # =========================================================================

    async def handle_subscription_created(self, data: dict[str, Any]) -> dict:
        """
        Handle subscription.created event - provision resources.

        Updates local subscription record with Commerce subscription ID.
        """
        subscription_id = data.get("id")
        customer_id = data.get("customer_id")
        plan_slug = data.get("plan_slug", "bootnode-free")
        metadata = data.get("metadata", {})
        project_id_str = metadata.get("project_id")

        if not project_id_str:
            logger.warning("No project_id in subscription metadata", sub_id=subscription_id)
            return {"error": "missing_project_id"}

        try:
            project_id = UUID(project_id_str)
        except ValueError:
            logger.error("Invalid project_id format", project_id=project_id_str)
            return {"error": "invalid_project_id"}

        # Map plan to tier
        tier = PLAN_TO_TIER.get(plan_slug, PricingTier.FREE)
        limits = get_tier_limits(tier)

        async with async_session() as db:
            # Get or create subscription
            result = await db.execute(
                select(Subscription).where(Subscription.project_id == project_id)
            )
            subscription = result.scalar_one_or_none()

            if subscription:
                # Update existing subscription
                subscription.hanzo_subscription_id = subscription_id
                subscription.hanzo_customer_id = customer_id
                subscription.tier = tier.value
                subscription.monthly_cu_limit = limits.monthly_cu
                subscription.rate_limit_per_second = limits.rate_limit_per_second
                subscription.max_apps = limits.max_apps
                subscription.max_webhooks = limits.max_webhooks
            else:
                # Create new subscription
                subscription = Subscription(
                    project_id=project_id,
                    tier=tier.value,
                    hanzo_subscription_id=subscription_id,
                    hanzo_customer_id=customer_id,
                    monthly_cu_limit=limits.monthly_cu,
                    rate_limit_per_second=limits.rate_limit_per_second,
                    max_apps=limits.max_apps,
                    max_webhooks=limits.max_webhooks,
                    billing_cycle_start=datetime.now(UTC),
                    billing_cycle_end=datetime.fromisoformat(
                        data.get("current_period_end", datetime.now(UTC).isoformat())
                    ),
                )
                db.add(subscription)

            await db.commit()

        # Invalidate cached subscription data
        await self._invalidate_cache(project_id)

        logger.info(
            "Subscription created/updated from webhook",
            project_id=str(project_id),
            subscription_id=subscription_id,
            tier=tier.value,
        )

        return {"project_id": str(project_id), "tier": tier.value}

    async def handle_subscription_updated(self, data: dict[str, Any]) -> dict:
        """
        Handle subscription.updated event - update limits.

        Called when plan changes or subscription is modified.
        """
        subscription_id = data.get("id")
        plan_slug = data.get("plan_slug", "bootnode-free")
        status = data.get("status", "active")

        # Map plan to tier
        tier = PLAN_TO_TIER.get(plan_slug, PricingTier.FREE)
        limits = get_tier_limits(tier)

        async with async_session() as db:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.hanzo_subscription_id == subscription_id
                )
            )
            subscription = result.scalar_one_or_none()

            if not subscription:
                logger.warning(
                    "Subscription not found for update",
                    subscription_id=subscription_id,
                )
                return {"error": "subscription_not_found"}

            # Update tier and limits
            subscription.tier = tier.value
            subscription.monthly_cu_limit = limits.monthly_cu
            subscription.rate_limit_per_second = limits.rate_limit_per_second
            subscription.max_apps = limits.max_apps
            subscription.max_webhooks = limits.max_webhooks

            # Update billing period if provided
            if data.get("current_period_end"):
                subscription.billing_cycle_end = datetime.fromisoformat(
                    data["current_period_end"]
                )

            await db.commit()

            # Invalidate cache
            await self._invalidate_cache(subscription.project_id)

        logger.info(
            "Subscription updated from webhook",
            subscription_id=subscription_id,
            tier=tier.value,
        )

        return {"subscription_id": subscription_id, "tier": tier.value}

    async def handle_subscription_cancelled(self, data: dict[str, Any]) -> dict:
        """
        Handle subscription.cancelled event - downgrade to free.

        Downgrades the project to free tier when subscription is cancelled.
        """
        subscription_id = data.get("id")
        immediately = data.get("immediately", False)

        async with async_session() as db:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.hanzo_subscription_id == subscription_id
                )
            )
            subscription = result.scalar_one_or_none()

            if not subscription:
                logger.warning(
                    "Subscription not found for cancellation",
                    subscription_id=subscription_id,
                )
                return {"error": "subscription_not_found"}

            if immediately:
                # Immediate downgrade to free
                free_limits = get_tier_limits(PricingTier.FREE)
                subscription.tier = PricingTier.FREE.value
                subscription.monthly_cu_limit = free_limits.monthly_cu
                subscription.rate_limit_per_second = free_limits.rate_limit_per_second
                subscription.max_apps = free_limits.max_apps
                subscription.max_webhooks = free_limits.max_webhooks
                subscription.hanzo_subscription_id = None
            else:
                # Schedule downgrade at end of period
                subscription.scheduled_tier = PricingTier.FREE.value

            await db.commit()

            # Invalidate cache
            await self._invalidate_cache(subscription.project_id)

        logger.info(
            "Subscription cancelled from webhook",
            subscription_id=subscription_id,
            immediately=immediately,
        )

        return {"subscription_id": subscription_id, "immediately": immediately}

    async def handle_subscription_reactivated(self, data: dict[str, Any]) -> dict:
        """Handle subscription.reactivated event."""
        subscription_id = data.get("id")
        plan_slug = data.get("plan_slug", "bootnode-free")

        tier = PLAN_TO_TIER.get(plan_slug, PricingTier.FREE)
        limits = get_tier_limits(tier)

        async with async_session() as db:
            result = await db.execute(
                select(Subscription).where(
                    Subscription.hanzo_subscription_id == subscription_id
                )
            )
            subscription = result.scalar_one_or_none()

            if not subscription:
                return {"error": "subscription_not_found"}

            # Restore tier
            subscription.tier = tier.value
            subscription.monthly_cu_limit = limits.monthly_cu
            subscription.rate_limit_per_second = limits.rate_limit_per_second
            subscription.max_apps = limits.max_apps
            subscription.max_webhooks = limits.max_webhooks
            subscription.scheduled_tier = None

            await db.commit()
            await self._invalidate_cache(subscription.project_id)

        logger.info(
            "Subscription reactivated from webhook",
            subscription_id=subscription_id,
            tier=tier.value,
        )

        return {"subscription_id": subscription_id, "tier": tier.value}

    # =========================================================================
    # Order Handlers
    # =========================================================================

    async def handle_order_completed(self, data: dict[str, Any]) -> dict:
        """Handle order.completed — payment captured successfully.

        May trigger subscription provisioning if order is for a plan upgrade.
        """
        order_id = data.get("id")
        customer_id = data.get("customer_id")
        metadata = data.get("metadata", {})
        plan_slug = metadata.get("plan_slug")
        project_id_str = metadata.get("project_id")

        logger.info(
            "Order completed",
            order_id=order_id,
            customer_id=customer_id,
            plan_slug=plan_slug,
        )

        # If order is for a plan subscription, provision it
        if plan_slug and project_id_str:
            try:
                project_id = UUID(project_id_str)
            except ValueError:
                return {"order_id": order_id, "error": "invalid_project_id"}

            tier = PLAN_TO_TIER.get(plan_slug, PricingTier.FREE)
            limits = get_tier_limits(tier)
            subscription_id = data.get("subscription_id")

            async with async_session() as db:
                result = await db.execute(
                    select(Subscription).where(Subscription.project_id == project_id)
                )
                subscription = result.scalar_one_or_none()

                if subscription:
                    subscription.tier = tier.value
                    subscription.monthly_cu_limit = limits.monthly_cu
                    subscription.rate_limit_per_second = limits.rate_limit_per_second
                    subscription.max_apps = limits.max_apps
                    subscription.max_webhooks = limits.max_webhooks
                    if subscription_id:
                        subscription.hanzo_subscription_id = subscription_id
                    if customer_id:
                        subscription.hanzo_customer_id = customer_id
                else:
                    subscription = Subscription(
                        project_id=project_id,
                        tier=tier.value,
                        hanzo_subscription_id=subscription_id,
                        hanzo_customer_id=customer_id,
                        monthly_cu_limit=limits.monthly_cu,
                        rate_limit_per_second=limits.rate_limit_per_second,
                        max_apps=limits.max_apps,
                        max_webhooks=limits.max_webhooks,
                        billing_cycle_start=datetime.now(UTC),
                        billing_cycle_end=datetime.fromisoformat(
                            data.get("current_period_end", datetime.now(UTC).isoformat())
                        ),
                    )
                    db.add(subscription)

                await db.commit()

            await self._invalidate_cache(project_id)

        return {"order_id": order_id, "plan_slug": plan_slug}

    async def handle_order_cancelled(self, data: dict[str, Any]) -> dict:
        """Handle order.cancelled — payment authorization voided."""
        order_id = data.get("id")
        reason = data.get("reason", "unknown")

        logger.info(
            "Order cancelled",
            order_id=order_id,
            reason=reason,
        )

        return {"order_id": order_id, "reason": reason}

    # =========================================================================
    # Invoice Handlers
    # =========================================================================

    async def handle_invoice_paid(self, data: dict[str, Any]) -> dict:
        """
        Handle invoice.paid event - record payment.

        Can be used for internal tracking or notifications.
        """
        invoice_id = data.get("id")
        customer_id = data.get("customer_id")
        amount_paid = data.get("amount_paid", 0)

        logger.info(
            "Invoice paid",
            invoice_id=invoice_id,
            customer_id=customer_id,
            amount_cents=amount_paid,
        )

        # Could send notification, update internal records, etc.
        return {
            "invoice_id": invoice_id,
            "amount_paid": amount_paid,
        }

    async def handle_invoice_failed(self, data: dict[str, Any]) -> dict:
        """
        Handle invoice.payment_failed - notify user, maybe downgrade.

        After multiple failures, Commerce will cancel the subscription,
        which triggers handle_subscription_cancelled.
        """
        invoice_id = data.get("id")
        customer_id = data.get("customer_id")
        subscription_id = data.get("subscription_id")
        attempt_count = data.get("attempt_count", 1)

        logger.warning(
            "Invoice payment failed",
            invoice_id=invoice_id,
            customer_id=customer_id,
            attempt_count=attempt_count,
        )

        # Could send notification email, create alert, etc.
        # The actual downgrade happens when Commerce cancels the subscription

        return {
            "invoice_id": invoice_id,
            "subscription_id": subscription_id,
            "attempt_count": attempt_count,
        }

    # =========================================================================
    # Customer Handlers
    # =========================================================================

    async def handle_customer_created(self, data: dict[str, Any]) -> dict:
        """Handle customer.created event."""
        customer_id = data.get("id")
        email = data.get("email")

        logger.info(
            "Customer created in Commerce",
            customer_id=customer_id,
            email=email,
        )

        return {"customer_id": customer_id}

    async def handle_customer_updated(self, data: dict[str, Any]) -> dict:
        """Handle customer.updated event."""
        customer_id = data.get("id")

        logger.info(
            "Customer updated in Commerce",
            customer_id=customer_id,
        )

        return {"customer_id": customer_id}

    # =========================================================================
    # Payment Handlers (forwarded from Square via Commerce)
    # =========================================================================

    async def handle_payment_paid(self, data: dict[str, Any]) -> dict:
        """Handle payment.paid — successful payment via Square."""
        payment_id = data.get("id")
        order_id = data.get("order_id")
        amount = data.get("amount", 0)

        logger.info(
            "Payment received",
            payment_id=payment_id,
            order_id=order_id,
            amount_cents=amount,
        )

        return {"payment_id": payment_id, "amount": amount}

    async def handle_payment_failed(self, data: dict[str, Any]) -> dict:
        """Handle payment.failed — Square payment declined."""
        payment_id = data.get("id")
        order_id = data.get("order_id")
        error_code = data.get("error_code", "unknown")

        logger.warning(
            "Payment failed",
            payment_id=payment_id,
            order_id=order_id,
            error_code=error_code,
        )

        return {"payment_id": payment_id, "error_code": error_code}

    async def handle_payment_refunded(self, data: dict[str, Any]) -> dict:
        """Handle payment.refunded — refund processed via Square."""
        payment_id = data.get("id")
        refund_id = data.get("refund_id")
        amount = data.get("amount", 0)

        logger.info(
            "Payment refunded",
            payment_id=payment_id,
            refund_id=refund_id,
            amount_cents=amount,
        )

        return {"payment_id": payment_id, "refund_id": refund_id, "amount": amount}

    # =========================================================================
    # Helpers
    # =========================================================================

    async def _invalidate_cache(self, project_id: UUID) -> None:
        """Invalidate cached subscription data."""
        cache_key = f"billing:subscription:{project_id}"
        await redis_client.delete(cache_key)


# Global singleton
webhook_handler = CommerceWebhookHandler()
