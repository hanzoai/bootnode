"""Real-time usage tracking with Redis.

Tracks compute units in Redis for real-time rate limiting and quota checks.
Batches writes to ClickHouse for analytics and billing.
"""

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from bootnode.core.billing.compute_units import get_compute_units
from bootnode.core.billing.tiers import PricingTier, get_tier_limits
from bootnode.core.cache import redis_client
from bootnode.core.datastore import datastore_client

logger = structlog.get_logger()

# Redis key prefixes
CU_USAGE_KEY = "cu:usage:{project_id}:{period}"  # Monthly CU counter
RATE_LIMIT_KEY = "rate:{project_id}:{window}"  # Per-second rate limit
CU_BUFFER_KEY = "cu:buffer:{project_id}"  # Batch buffer for ClickHouse


class UsageTracker:
    """Track compute units in Redis, batch to ClickHouse."""

    def __init__(self) -> None:
        self._batch_size = 100  # Flush to ClickHouse after N records
        self._batch_interval = 60  # Flush to ClickHouse after N seconds

    def _get_period_key(self, project_id: uuid.UUID) -> str:
        """Get the current billing period key (YYYY-MM)."""
        now = datetime.now(UTC)
        period = now.strftime("%Y-%m")
        return CU_USAGE_KEY.format(project_id=project_id, period=period)

    def _get_rate_key(self, project_id: uuid.UUID) -> str:
        """Get the current rate limit window key."""
        window = int(time.time())  # 1-second windows
        return RATE_LIMIT_KEY.format(project_id=project_id, window=window)

    async def track(
        self,
        project_id: uuid.UUID,
        method: str,
        compute_units: int | None = None,
        api_key_id: uuid.UUID | None = None,
        chain_id: int = 1,
        network: str = "mainnet",
        response_time_ms: int = 0,
        status_code: int = 200,
        ip_address: str = "",
        user_agent: str = "",
    ) -> None:
        """Track API usage.

        Args:
            project_id: The project ID
            method: The RPC method called
            compute_units: Override CU cost (auto-calculated if None)
            api_key_id: The API key used
            chain_id: The chain ID
            network: The network name
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            ip_address: Client IP address
            user_agent: Client user agent
        """
        if compute_units is None:
            compute_units = get_compute_units(method)

        # Increment monthly CU counter in Redis
        period_key = self._get_period_key(project_id)
        try:
            pipe = redis_client.client.pipeline()
            pipe.incrby(period_key, compute_units)
            # Set expiry to 35 days (covers billing period + grace)
            pipe.expire(period_key, 35 * 24 * 60 * 60)
            await pipe.execute()
        except Exception as e:
            logger.error("Failed to track usage in Redis", error=str(e))

        # Buffer for ClickHouse batch insert
        usage_record = {
            "project_id": str(project_id),
            "api_key_id": str(api_key_id) if api_key_id else None,
            "chain_id": chain_id,
            "network": network,
            "endpoint": f"/rpc/{network}",
            "method": method,
            "compute_units": compute_units,
            "response_time_ms": response_time_ms,
            "status_code": status_code,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Add to buffer and check if we should flush
        buffer_key = CU_BUFFER_KEY.format(project_id=project_id)
        try:
            await redis_client.client.rpush(buffer_key, json.dumps(usage_record))
            buffer_len = await redis_client.client.llen(buffer_key)

            if buffer_len >= self._batch_size:
                await self._flush_buffer(project_id)
        except Exception as e:
            logger.error("Failed to buffer usage", error=str(e))

    async def _flush_buffer(self, project_id: uuid.UUID) -> None:
        """Flush buffered usage records to ClickHouse."""
        if not datastore_client.is_connected:
            return

        buffer_key = CU_BUFFER_KEY.format(project_id=project_id)

        try:
            # Get and clear buffer atomically
            pipe = redis_client.client.pipeline()
            pipe.lrange(buffer_key, 0, -1)
            pipe.delete(buffer_key)
            results = await pipe.execute()

            records_raw = results[0]
            if not records_raw:
                return

            # Parse records and insert to ClickHouse
            records: list[dict[str, Any]] = []
            for record_str in records_raw:
                try:
                    record = json.loads(record_str)
                    records.append(record)
                except Exception:
                    continue

            if records:
                await datastore_client.insert("api_usage", records)
                logger.debug(
                    "Flushed usage to ClickHouse",
                    project_id=str(project_id),
                    count=len(records),
                )

        except Exception as e:
            logger.error("Failed to flush buffer to ClickHouse", error=str(e))

    async def get_current_usage(self, project_id: uuid.UUID) -> int:
        """Get current compute units used this billing period.

        Args:
            project_id: The project ID

        Returns:
            Total CU used this billing period
        """
        period_key = self._get_period_key(project_id)
        try:
            value = await redis_client.get(period_key)
            return int(value) if value else 0
        except Exception:
            return 0

    async def check_quota(self, project_id: uuid.UUID, tier: PricingTier) -> bool:
        """Check if project is within CU quota.

        Args:
            project_id: The project ID
            tier: The project's pricing tier

        Returns:
            True if within quota, False if exceeded
        """
        limits = get_tier_limits(tier)

        # Unlimited tiers always pass
        if limits.monthly_cu == 0:
            return True

        current_usage = await self.get_current_usage(project_id)
        return current_usage < limits.monthly_cu

    async def check_rate_limit(
        self,
        project_id: uuid.UUID,
        tier: PricingTier,
    ) -> tuple[bool, int]:
        """Check if project is within rate limit.

        Args:
            project_id: The project ID
            tier: The project's pricing tier

        Returns:
            Tuple of (allowed, remaining requests)
        """
        limits = get_tier_limits(tier)
        rate_key = self._get_rate_key(project_id)

        try:
            allowed, remaining = await redis_client.rate_limit_check(
                rate_key,
                limits.rate_limit_per_second,
                window_seconds=1,
            )
            return allowed, remaining
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e))
            # Fail open to avoid blocking legitimate traffic
            return True, limits.rate_limit_per_second

    async def get_usage_stats(
        self,
        project_id: uuid.UUID,
        tier: PricingTier,
    ) -> dict[str, Any]:
        """Get current usage statistics.

        Args:
            project_id: The project ID
            tier: The project's pricing tier

        Returns:
            Dict with usage statistics
        """
        limits = get_tier_limits(tier)
        current_usage = await self.get_current_usage(project_id)

        # Calculate percentage (0 for unlimited tiers)
        percentage = (current_usage / limits.monthly_cu * 100) if limits.monthly_cu > 0 else 0

        return {
            "current_cu": current_usage,
            "limit_cu": limits.monthly_cu,
            "remaining_cu": max(0, limits.monthly_cu - current_usage) if limits.monthly_cu > 0 else None,
            "percentage_used": round(percentage, 2),
            "rate_limit_per_second": limits.rate_limit_per_second,
            "tier": tier.value,
        }

    async def flush_all_buffers(self) -> None:
        """Flush all project buffers to ClickHouse. Called on shutdown."""
        try:
            # Find all buffer keys
            cursor = 0
            while True:
                cursor, keys = await redis_client.client.scan(
                    cursor, match="cu:buffer:*", count=100
                )
                for key in keys:
                    # Extract project_id from key
                    project_id_str = key.split(":")[-1]
                    try:
                        project_id = uuid.UUID(project_id_str)
                        await self._flush_buffer(project_id)
                    except ValueError:
                        continue

                if cursor == 0:
                    break
        except Exception as e:
            logger.error("Failed to flush all buffers", error=str(e))


# Global singleton
usage_tracker = UsageTracker()
