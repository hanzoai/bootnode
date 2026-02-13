"""Billing module - Alchemy-style compute unit billing system.

Exports:
- Compute unit definitions and helpers
- Pricing tiers and limits
- Real-time usage tracking (Redis)
- Billing service for subscriptions
- Hanzo Commerce integration (Square-based payments)
- Unified IAM + Commerce integration
"""

from bootnode.core.billing.commerce import (
    CommerceError,
    HanzoCommerceClient,
    commerce_client,
)
from bootnode.core.billing.compute_units import (
    COMPUTE_UNITS,
    DEFAULT_COMPUTE_UNITS,
    get_batch_compute_units,
    get_compute_units,
)
from bootnode.core.billing.models import (
    Customer,
    Invoice as CommerceInvoice,
    InvoiceStatus,
    PlanLimits,
    PlanTier,
    ProjectBilling,
    Subscription as CommerceSubscription,
    SubscriptionStatus,
    UsageRecord,
    WebhookEvent,
)
from bootnode.core.billing.service import (
    BillingService,
    Invoice,
    UsageSummary,
    billing_service,
)
from bootnode.core.billing.sync import UsageSyncWorker, usage_sync_worker
from bootnode.core.billing.tiers import (
    TIER_LIMITS,
    PricingTier,
    TierLimits,
    calculate_monthly_cost,
    get_tier_limits,
)
from bootnode.core.billing.tracker import UsageTracker, usage_tracker
from bootnode.core.billing.webhooks import (
    CommerceWebhookHandler,
    WebhookVerificationError,
    webhook_handler,
)
from bootnode.core.billing.unified import (
    UnifiedBillingClient,
    UnifiedUser,
    get_unified_billing_client,
)
from bootnode.core.billing.cloud_billing import (
    CloudBillingService,
    cloud_billing_service,
)

__all__ = [
    # Compute units
    "COMPUTE_UNITS",
    "DEFAULT_COMPUTE_UNITS",
    "get_compute_units",
    "get_batch_compute_units",
    # Tiers
    "PricingTier",
    "TierLimits",
    "TIER_LIMITS",
    "get_tier_limits",
    "calculate_monthly_cost",
    # Tracking
    "UsageTracker",
    "usage_tracker",
    # Service
    "BillingService",
    "billing_service",
    "UsageSummary",
    "Invoice",
    # Hanzo Commerce (Square-based payments)
    "HanzoCommerceClient",
    "commerce_client",
    "CommerceError",
    # Commerce Models
    "Customer",
    "CommerceSubscription",
    "CommerceInvoice",
    "SubscriptionStatus",
    "InvoiceStatus",
    "PlanTier",
    "PlanLimits",
    "ProjectBilling",
    "UsageRecord",
    "WebhookEvent",
    # Usage Sync
    "UsageSyncWorker",
    "usage_sync_worker",
    # Commerce Webhooks
    "CommerceWebhookHandler",
    "webhook_handler",
    "WebhookVerificationError",
    # Unified IAM + Commerce
    "UnifiedBillingClient",
    "UnifiedUser",
    "get_unified_billing_client",
    # Cloud compute billing
    "CloudBillingService",
    "cloud_billing_service",
]
