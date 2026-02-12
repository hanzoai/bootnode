"""Unified Hanzo IAM + Commerce integration.

Links IAM users (hanzo.id, zoo.id, lux.id, pars.id) to Commerce customers
for seamless authentication and billing across the Hanzo ecosystem.

Flow:
1. User authenticates via Hanzo IAM (JWT token)
2. On first billing access, auto-create/link Commerce customer
3. Store mapping: IAM user.id <-> Commerce customer.hanzo_id
4. All billing operations use the linked customer
"""

from datetime import datetime, UTC
from typing import Any
from uuid import UUID

import httpx
import structlog
from pydantic import BaseModel

from bootnode.config import get_settings
from bootnode.core.billing.commerce import CommerceError
from bootnode.core.iam import IAMUser

logger = structlog.get_logger()


class UnifiedUser(BaseModel):
    """Unified user with IAM identity and Commerce customer."""

    # IAM Identity
    iam_id: str
    email: str
    name: str
    org: str  # hanzo, zoo, lux, pars

    # Commerce Customer (created on first billing access)
    commerce_customer_id: str | None = None
    square_customer_id: str | None = None

    # Billing Status
    has_payment_method: bool = False
    default_payment_method: str | None = None

    @classmethod
    def from_iam_user(cls, iam_user: IAMUser, commerce_data: dict | None = None) -> "UnifiedUser":
        """Create unified user from IAM user with optional Commerce data."""
        user = cls(
            iam_id=iam_user.id,
            email=iam_user.email,
            name=iam_user.name,
            org=iam_user.org,
        )

        if commerce_data:
            user.commerce_customer_id = commerce_data.get("id")
            # Square customer ID is nested under accounts
            accounts = commerce_data.get("accounts", {})
            if isinstance(accounts, dict):
                user.square_customer_id = accounts.get("square")
            user.has_payment_method = commerce_data.get("has_payment_method", False)
            user.default_payment_method = commerce_data.get("default_payment_method")

        return user


class UnifiedBillingClient:
    """Unified client for IAM + Commerce integration.

    Automatically links IAM users to Commerce customers and provides
    a single interface for all billing operations.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.iam_url = settings.iam_url
        self.commerce_url = settings.commerce_url
        self.commerce_api_key = settings.commerce_api_key
        self._timeout = httpx.Timeout(30.0)

    def _commerce_headers(self) -> dict[str, str]:
        """Get Commerce API headers."""
        return {
            "Authorization": f"Bearer {self.commerce_api_key}",
            "Content-Type": "application/json",
            "X-Source": "bootnode",
        }

    async def get_or_create_customer(self, iam_user: IAMUser) -> UnifiedUser:
        """Get or create Commerce customer for IAM user.

        This is the main entry point for linking IAM users to Commerce.
        Called automatically on first billing access.
        """
        # First, try to find existing customer by hanzo_id
        customer = await self._find_customer_by_hanzo_id(iam_user.id)

        if customer:
            logger.info(
                "Found existing Commerce customer",
                iam_id=iam_user.id,
                customer_id=customer.get("id"),
            )
            return UnifiedUser.from_iam_user(iam_user, customer)

        # No customer found, create one
        customer = await self._create_customer(iam_user)

        logger.info(
            "Created Commerce customer for IAM user",
            iam_id=iam_user.id,
            customer_id=customer.get("id"),
            org=iam_user.org,
        )

        return UnifiedUser.from_iam_user(iam_user, customer)

    async def _find_customer_by_hanzo_id(self, hanzo_id: str) -> dict | None:
        """Find Commerce customer by Hanzo IAM ID."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(
                    f"{self.commerce_url}/api/v1/user",
                    params={"hanzo_id": hanzo_id},
                    headers=self._commerce_headers(),
                )

                if response.status_code == 200:
                    data = response.json()
                    customers = data.get("data", [])
                    if customers:
                        return customers[0]
                    # Single-object response
                    if data.get("id"):
                        return data

                return None

            except httpx.RequestError as e:
                logger.warning("Failed to lookup Commerce customer", error=str(e))
                return None

    async def _create_customer(self, iam_user: IAMUser) -> dict:
        """Create Commerce customer linked to IAM user."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self.commerce_url}/api/v1/user",
                json={
                    "email": iam_user.email,
                    "name": iam_user.name,
                    "first_name": iam_user.name.split()[0] if iam_user.name else "",
                    "last_name": " ".join(iam_user.name.split()[1:]) if iam_user.name else "",
                    "hanzo_id": iam_user.id,  # Link to IAM
                    "org": iam_user.org,
                    "metadata": {
                        "iam_id": iam_user.id,
                        "iam_org": iam_user.org,
                        "source": "bootnode",
                        "created_via": "unified_billing",
                    },
                },
                headers=self._commerce_headers(),
            )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                logger.error(
                    "Failed to create Commerce customer",
                    status=response.status_code,
                    error=error_data,
                )
                raise CommerceError(
                    message=error_data.get("message", "Failed to create Commerce customer"),
                    status_code=response.status_code,
                    details=error_data,
                )

            return response.json()

    async def get_customer_subscriptions(self, iam_user: IAMUser) -> list[dict]:
        """Get all subscriptions for IAM user across Commerce."""
        unified_user = await self.get_or_create_customer(iam_user)

        if not unified_user.commerce_customer_id:
            return []

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self.commerce_url}/api/v1/user/{unified_user.commerce_customer_id}/orders",
                headers=self._commerce_headers(),
            )

            if response.status_code == 200:
                return response.json().get("data", [])

            return []

    async def get_customer_invoices(self, iam_user: IAMUser) -> list[dict]:
        """Get all invoices for IAM user."""
        unified_user = await self.get_or_create_customer(iam_user)

        if not unified_user.commerce_customer_id:
            return []

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self.commerce_url}/api/v1/user/{unified_user.commerce_customer_id}/orders",
                params={"type": "invoice"},
                headers=self._commerce_headers(),
            )

            if response.status_code == 200:
                return response.json().get("data", [])

            return []

    async def get_customer_payment_methods(self, iam_user: IAMUser) -> list[dict]:
        """Get payment methods for IAM user (Square cards via Commerce)."""
        unified_user = await self.get_or_create_customer(iam_user)

        if not unified_user.commerce_customer_id:
            return []

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self.commerce_url}/api/v1/user/{unified_user.commerce_customer_id}/paymentmethods",
                headers=self._commerce_headers(),
            )

            if response.status_code == 200:
                return response.json().get("data", [])

            return []

    async def create_subscription(
        self,
        iam_user: IAMUser,
        plan_id: str,
        project_id: UUID,
    ) -> dict:
        """Create subscription for IAM user.

        This creates a subscription in Commerce linked to the IAM user,
        and stores the bootnode project_id in metadata for tracking.
        """
        unified_user = await self.get_or_create_customer(iam_user)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self.commerce_url}/api/v1/subscribe",
                json={
                    "customer_id": unified_user.commerce_customer_id,
                    "plan_id": plan_id,
                    "metadata": {
                        "bootnode_project_id": str(project_id),
                        "iam_id": iam_user.id,
                        "iam_org": iam_user.org,
                    },
                },
                headers=self._commerce_headers(),
            )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                raise CommerceError(
                    message=error_data.get("message", "Failed to create subscription"),
                    status_code=response.status_code,
                    details=error_data,
                )

            return response.json()

    async def report_usage(
        self,
        iam_user: IAMUser,
        subscription_id: str,
        compute_units: int,
        timestamp: datetime,
    ) -> None:
        """Report metered usage for PAYG billing."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self.commerce_url}/api/v1/subscribe/{subscription_id}/usage",
                json={
                    "quantity": compute_units,
                    "unit": "compute_units",
                    "timestamp": timestamp.isoformat(),
                    "metadata": {
                        "iam_id": iam_user.id,
                        "source": "bootnode",
                    },
                },
                headers=self._commerce_headers(),
            )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                logger.error(
                    "Failed to report usage",
                    subscription_id=subscription_id,
                    status=response.status_code,
                )
                raise CommerceError(
                    message=error_data.get("message", "Failed to report usage"),
                    status_code=response.status_code,
                    details=error_data,
                )

    async def sync_iam_to_commerce(self, iam_user: IAMUser) -> dict:
        """Sync IAM user data to Commerce customer.

        Updates Commerce customer with latest IAM data (name, email, etc).
        Called periodically or on profile update.
        """
        unified_user = await self.get_or_create_customer(iam_user)

        if not unified_user.commerce_customer_id:
            return {}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.patch(
                f"{self.commerce_url}/api/v1/user/{unified_user.commerce_customer_id}",
                json={
                    "email": iam_user.email,
                    "name": iam_user.name,
                    "metadata": {
                        "iam_id": iam_user.id,
                        "iam_org": iam_user.org,
                        "iam_roles": iam_user.roles,
                        "last_sync": datetime.now(UTC).isoformat(),
                    },
                },
                headers=self._commerce_headers(),
            )

            if response.status_code == 200:
                logger.info(
                    "Synced IAM user to Commerce",
                    iam_id=iam_user.id,
                    customer_id=unified_user.commerce_customer_id,
                )
                return response.json()

            return {}


# Global instance
_unified_client: UnifiedBillingClient | None = None


def get_unified_billing_client() -> UnifiedBillingClient:
    """Get unified billing client singleton."""
    global _unified_client
    if _unified_client is None:
        _unified_client = UnifiedBillingClient()
    return _unified_client
