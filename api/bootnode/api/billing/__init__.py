"""Billing API - Usage tracking, subscription management, and Commerce integration."""

import json
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from bootnode.api.deps import DbDep, ProjectDep
from bootnode.config import get_settings
from bootnode.core.billing import (
    TIER_LIMITS,
    CommerceError,
    Invoice,
    PricingTier,
    UsageSummary,
    billing_service,
    commerce_client,
    get_tier_limits,
    usage_sync_worker,
    usage_tracker,
    webhook_handler,
)
from bootnode.db.models import Subscription

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class UsageResponse(BaseModel):
    """Current usage response."""

    project_id: uuid.UUID
    tier: str
    current_cu: int
    limit_cu: int
    remaining_cu: int | None
    percentage_used: float
    rate_limit_per_second: int
    billing_cycle_start: datetime | None
    billing_cycle_end: datetime | None


class UsageSummaryResponse(BaseModel):
    """Usage summary response."""

    project_id: uuid.UUID
    period_start: date
    period_end: date
    total_cu: int
    total_requests: int
    cu_by_method: dict[str, int]
    cu_by_chain: dict[str, int]
    daily_usage: list[dict[str, Any]]
    estimated_cost_cents: int

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    id: uuid.UUID
    project_id: uuid.UUID
    tier: str
    monthly_cu_limit: int
    rate_limit_per_second: int
    max_apps: int
    max_webhooks: int
    current_cu_used: int
    billing_cycle_start: datetime
    billing_cycle_end: datetime
    scheduled_tier: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TierResponse(BaseModel):
    """Pricing tier response."""

    name: str
    monthly_cu: int
    rate_limit_per_second: int
    max_apps: int
    max_webhooks: int
    price_per_million_cu: int
    features: list[str]


class UpgradeRequest(BaseModel):
    """Upgrade subscription request."""

    tier: PricingTier
    hanzo_subscription_id: str | None = None


class InvoiceResponse(BaseModel):
    """Invoice response."""

    id: uuid.UUID
    project_id: uuid.UUID
    period_start: date
    period_end: date
    total_cu: int
    tier: str
    base_cost_cents: int
    overage_cost_cents: int
    total_cost_cents: int
    status: str
    hanzo_invoice_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class LimitsCheckResponse(BaseModel):
    """Limits check response."""

    tier: str
    quota_ok: bool
    rate_allowed: bool
    rate_remaining: int
    current_cu: int
    limit_cu: int
    remaining_cu: int | None
    percentage_used: float
    rate_limit_per_second: int


class CheckoutRequest(BaseModel):
    """Commerce Checkout request (Square payment via Commerce)."""

    tier: PricingTier
    nonce: str | None = None  # Square payment nonce
    source_id: str | None = None  # Square card on file
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutResponse(BaseModel):
    """Commerce Checkout response."""

    order_id: str | None = None
    checkout_url: str | None = None
    authorization_id: str | None = None


class CaptureRequest(BaseModel):
    """Capture an authorized payment."""

    pass


class SyncStatusResponse(BaseModel):
    """Usage sync status response."""

    running: bool
    interval_seconds: int
    last_sync: str | None
    lock_held: bool


# =============================================================================
# Usage & Subscription Endpoints (unchanged — payment-agnostic)
# =============================================================================


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    project: ProjectDep,
    db: DbDep,
) -> UsageResponse:
    """Get current compute unit usage for the project."""
    subscription = await billing_service.get_or_create_subscription(project.id, db)
    tier = PricingTier(subscription.tier)

    stats = await usage_tracker.get_usage_stats(project.id, tier)

    return UsageResponse(
        project_id=project.id,
        tier=subscription.tier,
        current_cu=stats["current_cu"],
        limit_cu=stats["limit_cu"],
        remaining_cu=stats["remaining_cu"],
        percentage_used=stats["percentage_used"],
        rate_limit_per_second=stats["rate_limit_per_second"],
        billing_cycle_start=subscription.billing_cycle_start,
        billing_cycle_end=subscription.billing_cycle_end,
    )


@router.get("/usage/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    project: ProjectDep,
    db: DbDep,
    year: int | None = None,
    month: int | None = None,
) -> UsageSummary:
    """Get detailed usage summary for a billing period.

    If year/month not specified, returns current billing period.
    """
    period = date(year, month, 1) if year and month else date.today().replace(day=1)
    return await billing_service.get_usage_summary(project.id, period, db)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    project: ProjectDep,
    db: DbDep,
) -> Subscription:
    """Get subscription details for the project."""
    subscription = await billing_service.get_or_create_subscription(project.id, db)
    return subscription


@router.post("/subscription/upgrade", response_model=SubscriptionResponse)
async def upgrade_subscription(
    request: UpgradeRequest,
    project: ProjectDep,
    db: DbDep,
) -> Subscription:
    """Upgrade subscription to a new tier.

    For paid tiers, a hanzo_subscription_id from Commerce is required.
    """
    current = await billing_service.get_or_create_subscription(project.id, db)
    current_tier = PricingTier(current.tier)

    # Validate upgrade path
    tier_order = [PricingTier.FREE, PricingTier.PAY_AS_YOU_GO, PricingTier.GROWTH, PricingTier.ENTERPRISE]
    current_idx = tier_order.index(current_tier)
    new_idx = tier_order.index(request.tier)

    if new_idx < current_idx:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /subscription/downgrade for tier downgrades",
        )

    if new_idx == current_idx:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already on this tier",
        )

    # Require payment info for paid tiers
    if request.tier != PricingTier.FREE and not request.hanzo_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="hanzo_subscription_id required for paid tiers",
        )

    return await billing_service.upgrade_tier(
        project.id,
        request.tier,
        db,
        hanzo_subscription_id=request.hanzo_subscription_id,
    )


@router.post("/subscription/downgrade", response_model=SubscriptionResponse)
async def downgrade_subscription(
    request: UpgradeRequest,
    project: ProjectDep,
    db: DbDep,
) -> Subscription:
    """Schedule a subscription downgrade.

    Downgrade takes effect at the end of the current billing period.
    """
    current = await billing_service.get_or_create_subscription(project.id, db)
    current_tier = PricingTier(current.tier)

    tier_order = [PricingTier.FREE, PricingTier.PAY_AS_YOU_GO, PricingTier.GROWTH, PricingTier.ENTERPRISE]
    current_idx = tier_order.index(current_tier)
    new_idx = tier_order.index(request.tier)

    if new_idx >= current_idx:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /subscription/upgrade for tier upgrades",
        )

    return await billing_service.downgrade_tier(project.id, request.tier, db)


@router.get("/invoices", response_model=list[InvoiceResponse])
async def get_invoices(
    project: ProjectDep,
    db: DbDep,
    limit: int = 12,
) -> list[Invoice]:
    """Get invoices for the project."""
    return await billing_service.get_invoices(project.id, db, limit=limit)


@router.get("/tiers", response_model=list[TierResponse])
async def get_tiers() -> list[TierResponse]:
    """Get available pricing tiers."""
    return [
        TierResponse(
            name=tier.value,
            monthly_cu=limits.monthly_cu,
            rate_limit_per_second=limits.rate_limit_per_second,
            max_apps=limits.max_apps,
            max_webhooks=limits.max_webhooks,
            price_per_million_cu=limits.price_per_million_cu,
            features=limits.features,
        )
        for tier, limits in TIER_LIMITS.items()
    ]


@router.get("/tiers/{tier_name}", response_model=TierResponse)
async def get_tier(tier_name: str) -> TierResponse:
    """Get details for a specific pricing tier."""
    try:
        tier = PricingTier(tier_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown tier: {tier_name}",
        )

    limits = get_tier_limits(tier)
    return TierResponse(
        name=tier.value,
        monthly_cu=limits.monthly_cu,
        rate_limit_per_second=limits.rate_limit_per_second,
        max_apps=limits.max_apps,
        max_webhooks=limits.max_webhooks,
        price_per_million_cu=limits.price_per_million_cu,
        features=limits.features,
    )


@router.get("/limits", response_model=LimitsCheckResponse)
async def check_limits(
    project: ProjectDep,
    db: DbDep,
) -> LimitsCheckResponse:
    """Check current limits and quotas for the project."""
    result = await billing_service.check_limits(project.id, db)
    return LimitsCheckResponse(**result)


# =============================================================================
# Commerce Checkout (Square payments via Commerce API)
# =============================================================================


TIER_TO_PLAN_SLUG: dict[PricingTier, str] = {
    PricingTier.FREE: "bootnode-free",
    PricingTier.PAY_AS_YOU_GO: "bootnode-payg",
    PricingTier.GROWTH: "bootnode-growth",
    PricingTier.ENTERPRISE: "bootnode-enterprise",
}


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    project: ProjectDep,
    db: DbDep,
) -> CheckoutResponse:
    """Create a Commerce checkout session (Square payment).

    Returns an order_id and checkout_url for the user to complete payment.
    After payment, Commerce webhooks handle provisioning.
    """
    settings = get_settings()

    if request.tier in (PricingTier.FREE, PricingTier.ENTERPRISE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Checkout not available for {request.tier.value} tier",
        )

    subscription = await billing_service.get_or_create_subscription(project.id, db)
    customer_id = subscription.hanzo_customer_id

    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Use /billing/account to set up billing first.",
        )

    plan_slug = TIER_TO_PLAN_SLUG.get(request.tier, "bootnode-payg")
    success_url = request.success_url or f"{settings.frontend_url}/billing?checkout=success"
    cancel_url = request.cancel_url or f"{settings.frontend_url}/billing?checkout=cancelled"

    try:
        result = await commerce_client.create_checkout(
            customer_id=customer_id,
            plan_slug=plan_slug,
            project_id=project.id,
            nonce=request.nonce,
            source_id=request.source_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return CheckoutResponse(
            order_id=result.get("order_id"),
            checkout_url=result.get("checkout_url"),
            authorization_id=result.get("authorization_id"),
        )
    except CommerceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


@router.post("/checkout/capture/{order_id}")
async def capture_checkout(
    order_id: str,
) -> dict:
    """Capture an authorized Commerce payment."""
    try:
        result = await commerce_client.capture_checkout(order_id)
        return result
    except CommerceError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


# =============================================================================
# Commerce Webhooks
# =============================================================================


@router.post("/webhooks/commerce")
async def commerce_webhook(request: Request) -> dict:
    """Handle Hanzo Commerce webhooks.

    Verifies HMAC signature and processes subscription/order/payment events.
    """
    payload = await request.body()
    signature = request.headers.get("X-Commerce-Signature", "")

    if not webhook_handler.verify_signature(payload, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    result = await webhook_handler.handle_event(event)
    return {"received": True, **result}


# =============================================================================
# Usage Sync (to Commerce for metered billing)
# =============================================================================


@router.post("/sync")
async def sync_usage(
    project: ProjectDep,
) -> dict:
    """Manually sync usage to Commerce.

    Reports accumulated compute units to Commerce for metered billing.
    Commerce handles invoicing via Square.
    """
    result = await usage_sync_worker.sync_project(project.id)
    return result


@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status() -> SyncStatusResponse:
    """Get usage sync worker status."""
    status_data = await usage_sync_worker.get_status()
    return SyncStatusResponse(**status_data)


# =============================================================================
# Unified IAM + Commerce Billing
# =============================================================================

from bootnode.core.billing.unified import get_unified_billing_client
from bootnode.core.iam import IAMUser, get_current_user


class UnifiedUserResponse(BaseModel):
    """Unified user with IAM and Commerce billing data."""

    iam_id: str
    email: str
    name: str
    org: str
    commerce_customer_id: str | None
    square_customer_id: str | None
    has_payment_method: bool
    default_payment_method: str | None


class PaymentMethodResponse(BaseModel):
    """Payment method response."""

    id: str
    type: str
    brand: str | None
    last4: str | None
    exp_month: int | None
    exp_year: int | None
    is_default: bool


@router.get("/account", response_model=UnifiedUserResponse)
async def get_billing_account(
    user: IAMUser = Depends(get_current_user),
) -> UnifiedUserResponse:
    """Get billing account for authenticated user.

    Links IAM user to Commerce customer. Creates Commerce customer if needed.
    """
    unified = get_unified_billing_client()
    unified_user = await unified.get_or_create_customer(user)

    return UnifiedUserResponse(
        iam_id=unified_user.iam_id,
        email=unified_user.email,
        name=unified_user.name,
        org=unified_user.org,
        commerce_customer_id=unified_user.commerce_customer_id,
        square_customer_id=unified_user.square_customer_id,
        has_payment_method=unified_user.has_payment_method,
        default_payment_method=unified_user.default_payment_method,
    )


@router.get("/account/subscriptions")
async def get_account_subscriptions(
    user: IAMUser = Depends(get_current_user),
) -> list[dict]:
    """Get all Commerce subscriptions for authenticated user."""
    unified = get_unified_billing_client()
    return await unified.get_customer_subscriptions(user)


@router.get("/account/invoices")
async def get_account_invoices(
    user: IAMUser = Depends(get_current_user),
) -> list[dict]:
    """Get all Commerce invoices for authenticated user."""
    unified = get_unified_billing_client()
    return await unified.get_customer_invoices(user)


@router.get("/account/payment-methods", response_model=list[PaymentMethodResponse])
async def get_account_payment_methods(
    user: IAMUser = Depends(get_current_user),
) -> list[PaymentMethodResponse]:
    """Get payment methods for authenticated user (Square cards via Commerce)."""
    unified = get_unified_billing_client()
    methods = await unified.get_customer_payment_methods(user)
    return [
        PaymentMethodResponse(
            id=m.get("id", ""),
            type=m.get("type", "card"),
            brand=m.get("card", {}).get("brand") if isinstance(m.get("card"), dict) else None,
            last4=m.get("card", {}).get("last4") if isinstance(m.get("card"), dict) else None,
            exp_month=m.get("card", {}).get("exp_month") if isinstance(m.get("card"), dict) else None,
            exp_year=m.get("card", {}).get("exp_year") if isinstance(m.get("card"), dict) else None,
            is_default=m.get("is_default", False),
        )
        for m in methods
    ]


@router.post("/account/sync")
async def sync_iam_to_commerce(
    user: IAMUser = Depends(get_current_user),
) -> dict:
    """Sync IAM user data to Commerce customer.

    Updates Commerce customer with latest IAM profile data.
    """
    unified = get_unified_billing_client()
    result = await unified.sync_iam_to_commerce(user)
    return {"synced": True, "result": result}
