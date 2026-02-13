"""Cloud compute billing service.

Handles authorization, quota checks, and usage metering for
cloud instances provisioned by the agents control-plane.
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bootnode.core.billing.tiers import (
    CLOUD_COMPUTE_LIMITS,
    CloudComputeLimits,
    PricingTier,
    get_cloud_compute_limits,
)
from bootnode.core.billing.tracker import usage_tracker
from bootnode.db.models import Subscription

logger = structlog.get_logger()


class CloudAuthResponse(BaseModel):
    """Response for cloud provisioning authorization."""

    authorized: bool
    tier: str
    hourly_rate_cents: int
    reason: str = ""
    billing_account_id: str = ""


class CloudQuotaResponse(BaseModel):
    """Cloud compute quota for a team."""

    tier: str
    max_linux_instances: int
    max_windows_instances: int
    max_macos_instances: int
    max_compute_hours_monthly: int
    used_linux: int
    used_windows: int
    used_macos: int
    used_compute_hours: float
    monthly_budget_cents: int
    used_budget_cents: int


class CloudUsageReport(BaseModel):
    """Usage report from the control-plane."""

    instance_id: str
    platform: str
    compute_hours: float
    hourly_rate_cents: int


class CloudBillingService:
    """Service for cloud compute billing operations."""

    async def authorize_provisioning(
        self,
        team_id: str,
        platform: str,
        instance_type: str,
        db: AsyncSession,
    ) -> CloudAuthResponse:
        """Check if a team can provision a cloud instance.

        Args:
            team_id: The team/project ID
            platform: linux, windows, or macos
            instance_type: Instance type requested
            db: Database session

        Returns:
            Authorization response with tier and hourly rate
        """
        # Get the team's subscription tier.
        subscription = await self._get_team_subscription(team_id, db)
        tier = PricingTier(subscription.tier) if subscription else PricingTier.FREE
        limits = get_cloud_compute_limits(tier)

        # Check platform-specific instance limit.
        max_for_platform = self._max_instances_for_platform(limits, platform)
        if max_for_platform == 0:
            return CloudAuthResponse(
                authorized=False,
                tier=tier.value,
                hourly_rate_cents=0,
                reason=f"{platform} instances not available on {tier.value} tier",
            )

        # Check current usage against quota.
        current_count = await self._count_active_instances(team_id, platform, db)
        if current_count >= max_for_platform:
            return CloudAuthResponse(
                authorized=False,
                tier=tier.value,
                hourly_rate_cents=0,
                reason=f"max {platform} instances ({max_for_platform}) reached for {tier.value} tier",
            )

        # Check monthly budget (if set).
        if limits.monthly_budget_cents > 0:
            used = await self._get_monthly_cloud_spend(team_id, db)
            if used >= limits.monthly_budget_cents:
                return CloudAuthResponse(
                    authorized=False,
                    tier=tier.value,
                    hourly_rate_cents=0,
                    reason=f"monthly cloud budget (${limits.monthly_budget_cents / 100:.0f}) exceeded",
                )

        # Get hourly rate for platform.
        hourly = self._hourly_rate_for_platform(limits, platform)

        # Check free tier compute hours.
        if tier == PricingTier.FREE and limits.max_compute_hours_monthly > 0:
            used_hours = await self._get_monthly_compute_hours(team_id, db)
            if used_hours >= limits.max_compute_hours_monthly:
                return CloudAuthResponse(
                    authorized=False,
                    tier=tier.value,
                    hourly_rate_cents=hourly,
                    reason=f"free tier compute hours ({limits.max_compute_hours_monthly}h) exhausted",
                )

        customer_id = subscription.hanzo_customer_id if subscription else ""

        logger.info(
            "cloud provisioning authorized",
            team_id=team_id,
            platform=platform,
            tier=tier.value,
            hourly_cents=hourly,
        )

        return CloudAuthResponse(
            authorized=True,
            tier=tier.value,
            hourly_rate_cents=hourly,
            billing_account_id=customer_id or "",
        )

    async def get_team_quota(
        self,
        team_id: str,
        db: AsyncSession,
    ) -> CloudQuotaResponse:
        """Get cloud compute quota and usage for a team."""
        subscription = await self._get_team_subscription(team_id, db)
        tier = PricingTier(subscription.tier) if subscription else PricingTier.FREE
        limits = get_cloud_compute_limits(tier)

        used_linux = await self._count_active_instances(team_id, "linux", db)
        used_windows = await self._count_active_instances(team_id, "windows", db)
        used_macos = await self._count_active_instances(team_id, "macos", db)
        used_hours = await self._get_monthly_compute_hours(team_id, db)
        used_budget = await self._get_monthly_cloud_spend(team_id, db)

        return CloudQuotaResponse(
            tier=tier.value,
            max_linux_instances=limits.max_linux_instances,
            max_windows_instances=limits.max_windows_instances,
            max_macos_instances=limits.max_macos_instances,
            max_compute_hours_monthly=limits.max_compute_hours_monthly,
            used_linux=used_linux,
            used_windows=used_windows,
            used_macos=used_macos,
            used_compute_hours=used_hours,
            monthly_budget_cents=limits.monthly_budget_cents,
            used_budget_cents=used_budget,
        )

    async def report_usage(
        self,
        report: CloudUsageReport,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Record cloud compute usage for billing.

        Called by the control-plane monitor on each tick for running instances.
        """
        cost_cents = int(report.compute_hours * report.hourly_rate_cents)

        # Track in Redis for real-time aggregation.
        key = f"cloud:usage:{report.instance_id}"
        month_key = f"cloud:monthly:{datetime.now(UTC).strftime('%Y-%m')}"

        await usage_tracker.redis.incrbyfloat(key, report.compute_hours)
        await usage_tracker.redis.incrby(f"{month_key}:cost_cents", cost_cents)

        logger.debug(
            "cloud usage recorded",
            instance_id=report.instance_id,
            platform=report.platform,
            hours=report.compute_hours,
            cost_cents=cost_cents,
        )

        return {"recorded": True, "cost_cents": cost_cents}

    # --- Internal helpers ---

    async def _get_team_subscription(
        self, team_id: str, db: AsyncSession
    ) -> Subscription | None:
        """Get subscription for a team/project."""
        try:
            from uuid import UUID
            project_id = UUID(team_id)
            result = await db.execute(
                select(Subscription).where(Subscription.project_id == project_id)
            )
            return result.scalar_one_or_none()
        except (ValueError, Exception):
            return None

    async def _count_active_instances(
        self, team_id: str, platform: str, db: AsyncSession
    ) -> int:
        """Count active (non-terminated) instances for a team+platform.

        Uses Redis counter set by the control-plane, or returns 0 if unavailable.
        """
        key = f"cloud:active:{team_id}:{platform}"
        try:
            val = await usage_tracker.redis.get(key)
            return int(val) if val else 0
        except Exception:
            return 0

    async def _get_monthly_compute_hours(
        self, team_id: str, db: AsyncSession
    ) -> float:
        """Get total compute hours used this month."""
        month = datetime.now(UTC).strftime("%Y-%m")
        key = f"cloud:hours:{team_id}:{month}"
        try:
            val = await usage_tracker.redis.get(key)
            return float(val) if val else 0.0
        except Exception:
            return 0.0

    async def _get_monthly_cloud_spend(
        self, team_id: str, db: AsyncSession
    ) -> int:
        """Get total cloud spend in cents this month."""
        month = datetime.now(UTC).strftime("%Y-%m")
        key = f"cloud:spend:{team_id}:{month}"
        try:
            val = await usage_tracker.redis.get(key)
            return int(val) if val else 0
        except Exception:
            return 0

    def _max_instances_for_platform(
        self, limits: CloudComputeLimits, platform: str
    ) -> int:
        """Get max instances for a platform from tier limits."""
        match platform:
            case "linux":
                return limits.max_linux_instances
            case "windows":
                return limits.max_windows_instances
            case "macos":
                return limits.max_macos_instances
            case _:
                return 0

    def _hourly_rate_for_platform(
        self, limits: CloudComputeLimits, platform: str
    ) -> int:
        """Get hourly rate in cents for a platform."""
        match platform:
            case "linux":
                return limits.linux_hourly_cents
            case "windows":
                return limits.windows_hourly_cents
            case "macos":
                return limits.macos_hourly_cents
            case _:
                return 10


# Global singleton
cloud_billing_service = CloudBillingService()
