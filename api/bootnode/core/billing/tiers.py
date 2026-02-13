"""Pricing tiers and limits for compute unit billing."""

from enum import Enum

from pydantic import BaseModel


class PricingTier(str, Enum):
    """Available pricing tiers."""

    FREE = "free"
    PAY_AS_YOU_GO = "payg"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class TierLimits(BaseModel):
    """Limits and pricing for a tier."""

    monthly_cu: int  # 0 = unlimited
    rate_limit_per_second: int
    max_apps: int  # 0 = unlimited
    max_webhooks: int
    price_per_million_cu: int  # cents, 0 = free or custom pricing
    overage_price_per_million_cu: int  # cents for overage (PAYG tiers)
    support_level: str
    features: list[str]


# Tier definitions matching Alchemy-style pricing
TIER_LIMITS: dict[PricingTier, TierLimits] = {
    PricingTier.FREE: TierLimits(
        monthly_cu=30_000_000,  # 30M CU/month
        rate_limit_per_second=25,
        max_apps=5,
        max_webhooks=5,
        price_per_million_cu=0,
        overage_price_per_million_cu=0,  # Hard limit, no overage
        support_level="community",
        features=[
            "30M compute units/month",
            "25 requests/second",
            "5 apps",
            "5 webhooks",
            "Standard APIs",
            "Community support",
        ],
    ),
    PricingTier.PAY_AS_YOU_GO: TierLimits(
        monthly_cu=0,  # Unlimited with PAYG
        rate_limit_per_second=300,
        max_apps=30,
        max_webhooks=100,
        price_per_million_cu=40,  # $0.40 per million CU
        overage_price_per_million_cu=40,
        support_level="email",
        features=[
            "Pay as you go",
            "300 requests/second",
            "30 apps",
            "100 webhooks",
            "Enhanced APIs",
            "Email support",
            "Usage analytics",
        ],
    ),
    PricingTier.GROWTH: TierLimits(
        monthly_cu=100_000_000,  # 100M CU included
        rate_limit_per_second=500,
        max_apps=50,
        max_webhooks=250,
        price_per_million_cu=35,  # $0.35 per million (discounted)
        overage_price_per_million_cu=35,
        support_level="priority",
        features=[
            "100M compute units included",
            "500 requests/second",
            "50 apps",
            "250 webhooks",
            "All Enhanced APIs",
            "Priority support",
            "Advanced analytics",
            "Custom webhooks",
        ],
    ),
    PricingTier.ENTERPRISE: TierLimits(
        monthly_cu=0,  # Custom
        rate_limit_per_second=1000,
        max_apps=0,  # Unlimited
        max_webhooks=500,
        price_per_million_cu=0,  # Custom pricing
        overage_price_per_million_cu=0,
        support_level="dedicated",
        features=[
            "Custom compute units",
            "Custom rate limits",
            "Unlimited apps",
            "500+ webhooks",
            "All APIs + custom",
            "Dedicated support",
            "SLA guarantee",
            "Private endpoints",
            "Custom integrations",
        ],
    ),
}


def get_tier_limits(tier: PricingTier) -> TierLimits:
    """Get limits for a pricing tier.

    Args:
        tier: The pricing tier

    Returns:
        TierLimits for the specified tier
    """
    return TIER_LIMITS[tier]


class CloudComputeLimits(BaseModel):
    """Cloud compute limits per tier."""

    max_linux_instances: int  # 0 = not allowed
    max_windows_instances: int
    max_macos_instances: int
    max_compute_hours_monthly: int  # 0 = unlimited
    monthly_budget_cents: int  # 0 = unlimited
    linux_hourly_cents: int  # per-hour cost
    windows_hourly_cents: int
    macos_hourly_cents: int


# Cloud compute quotas per tier
CLOUD_COMPUTE_LIMITS: dict[PricingTier, CloudComputeLimits] = {
    PricingTier.FREE: CloudComputeLimits(
        max_linux_instances=1,
        max_windows_instances=0,
        max_macos_instances=0,
        max_compute_hours_monthly=20,  # 20 hours free
        monthly_budget_cents=0,
        linux_hourly_cents=1,  # $0.01/hr (free tier absorbed)
        windows_hourly_cents=10,
        macos_hourly_cents=120,
    ),
    PricingTier.PAY_AS_YOU_GO: CloudComputeLimits(
        max_linux_instances=5,
        max_windows_instances=2,
        max_macos_instances=1,
        max_compute_hours_monthly=0,  # unlimited, pay per use
        monthly_budget_cents=50000,  # $500 soft cap
        linux_hourly_cents=1,  # $0.01/hr
        windows_hourly_cents=10,  # $0.10/hr
        macos_hourly_cents=120,  # $1.20/hr
    ),
    PricingTier.GROWTH: CloudComputeLimits(
        max_linux_instances=20,
        max_windows_instances=5,
        max_macos_instances=3,
        max_compute_hours_monthly=0,  # unlimited
        monthly_budget_cents=200000,  # $2000 soft cap
        linux_hourly_cents=1,
        windows_hourly_cents=8,  # discounted
        macos_hourly_cents=100,  # discounted
    ),
    PricingTier.ENTERPRISE: CloudComputeLimits(
        max_linux_instances=100,
        max_windows_instances=20,
        max_macos_instances=10,
        max_compute_hours_monthly=0,  # unlimited
        monthly_budget_cents=0,  # custom
        linux_hourly_cents=1,
        windows_hourly_cents=6,  # volume discount
        macos_hourly_cents=80,  # volume discount
    ),
}


def get_cloud_compute_limits(tier: PricingTier) -> CloudComputeLimits:
    """Get cloud compute limits for a pricing tier."""
    return CLOUD_COMPUTE_LIMITS[tier]


def calculate_monthly_cost(tier: PricingTier, compute_units_used: int) -> int:
    """Calculate the monthly cost in cents.

    Args:
        tier: The pricing tier
        compute_units_used: Total CU used in the billing period

    Returns:
        Cost in cents
    """
    limits = TIER_LIMITS[tier]

    if tier == PricingTier.FREE:
        return 0

    if tier == PricingTier.ENTERPRISE:
        # Custom pricing, handled separately
        return 0

    # Calculate billable CU (minus included CU for Growth tier)
    included_cu = limits.monthly_cu
    billable_cu = max(0, compute_units_used - included_cu)

    # Convert to millions and calculate cost
    millions = billable_cu / 1_000_000
    cost_cents = int(millions * limits.price_per_million_cu)

    return cost_cents
