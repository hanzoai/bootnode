"""Usage sync worker for Commerce billing.

Periodically syncs compute unit usage from Redis to Hanzo Commerce
for PAYG (pay-as-you-go) metered billing. Commerce handles invoicing via Square.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bootnode.config import get_settings
from bootnode.core.billing.commerce import CommerceError, commerce_client
from bootnode.core.billing.tiers import PricingTier
from bootnode.core.billing.tracker import usage_tracker
from bootnode.core.cache import redis_client
from bootnode.db.models import Subscription
from bootnode.db.session import async_session

logger = structlog.get_logger()

# Redis key for tracking sync state
SYNC_LOCK_KEY = "billing:sync:lock"
SYNC_CURSOR_KEY = "billing:sync:cursor:{project_id}"
LAST_SYNC_KEY = "billing:sync:last"


class UsageSyncWorker:
    """Periodically sync usage from Redis to Hanzo Commerce."""

    def __init__(self, interval_seconds: int = 3600) -> None:
        """Initialize sync worker.

        Args:
            interval_seconds: Sync interval (default: 1 hour)
        """
        self.interval = interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None

    async def _acquire_lock(self, ttl: int = 300) -> bool:
        """Acquire distributed lock for sync operation."""
        result = await redis_client.client.set(
            SYNC_LOCK_KEY,
            datetime.now(UTC).isoformat(),
            nx=True,  # Only set if not exists
            ex=ttl,  # Expire after TTL
        )
        return result is not None

    async def _release_lock(self) -> None:
        """Release distributed lock."""
        await redis_client.delete(SYNC_LOCK_KEY)

    async def _get_payg_subscriptions(
        self, db: AsyncSession
    ) -> list[tuple[uuid.UUID, str, str]]:
        """Get all active PAYG subscriptions.

        Returns list of (project_id, hanzo_subscription_id, hanzo_customer_id) tuples.
        """
        result = await db.execute(
            select(
                Subscription.project_id,
                Subscription.hanzo_subscription_id,
                Subscription.hanzo_customer_id,
            ).where(
                Subscription.tier == PricingTier.PAY_AS_YOU_GO.value,
                Subscription.hanzo_subscription_id.isnot(None),
                Subscription.hanzo_customer_id.isnot(None),
            )
        )
        return [(row[0], row[1], row[2]) for row in result.all()]

    async def _get_unsync_usage(self, project_id: uuid.UUID) -> int:
        """Get compute units accumulated since last sync."""
        key = f"billing:unsync:cu:{project_id}"
        value = await redis_client.get(key)
        return int(value) if value else 0

    async def _mark_synced(self, project_id: uuid.UUID, compute_units: int) -> None:
        """Mark usage as synced by decrementing counter."""
        key = f"billing:unsync:cu:{project_id}"
        # Decrement by the amount we synced
        await redis_client.client.decrby(key, compute_units)
        # Ensure we don't go negative
        current = await redis_client.get(key)
        if current and int(current) < 0:
            await redis_client.set(key, "0")

    async def _sync_project(
        self,
        project_id: uuid.UUID,
        subscription_id: str,
        customer_id: str,
    ) -> dict[str, Any]:
        """Sync usage for a single project.

        Reports compute units to Commerce, which handles metered invoicing via Square.
        """
        result = {
            "project_id": str(project_id),
            "subscription_id": subscription_id,
            "compute_units": 0,
            "synced": False,
            "error": None,
        }

        try:
            # Get unsync'd usage
            compute_units = await self._get_unsync_usage(project_id)

            if compute_units <= 0:
                result["synced"] = True
                return result

            result["compute_units"] = compute_units

            # Generate idempotency key for this sync
            sync_time = datetime.now(UTC)
            idempotency_key = f"{project_id}:{sync_time.strftime('%Y-%m-%d-%H')}"

            # Report to Commerce (uses subscription_id, Commerce handles Square invoicing)
            await commerce_client.report_usage(
                subscription_id=subscription_id,
                compute_units=compute_units,
                timestamp=sync_time,
                idempotency_key=idempotency_key,
            )

            # Mark as synced
            await self._mark_synced(project_id, compute_units)

            result["synced"] = True
            logger.info(
                "Usage synced to Commerce",
                project_id=str(project_id),
                compute_units=compute_units,
            )

        except CommerceError as e:
            result["error"] = e.message
            logger.error(
                "Failed to sync usage to Commerce",
                project_id=str(project_id),
                error=e.message,
            )

        except Exception as e:
            result["error"] = str(e)
            logger.error(
                "Unexpected error syncing usage",
                project_id=str(project_id),
                error=str(e),
            )

        return result

    async def sync_all_projects(self) -> dict[str, Any]:
        """Sync usage for all active PAYG subscriptions.

        Returns summary of sync operation.
        """
        summary = {
            "started_at": datetime.now(UTC).isoformat(),
            "total_projects": 0,
            "synced": 0,
            "failed": 0,
            "total_cu": 0,
            "errors": [],
        }

        # Acquire lock
        if not await self._acquire_lock():
            logger.warning("Could not acquire sync lock, another sync in progress")
            summary["error"] = "Lock not acquired"
            return summary

        try:
            async with async_session() as db:
                # Get all PAYG subscriptions
                subscriptions = await self._get_payg_subscriptions(db)
                summary["total_projects"] = len(subscriptions)

                for project_id, subscription_id, customer_id in subscriptions:
                    result = await self._sync_project(project_id, subscription_id, customer_id)

                    if result["synced"]:
                        summary["synced"] += 1
                        summary["total_cu"] += result["compute_units"]
                    else:
                        summary["failed"] += 1
                        if result["error"]:
                            summary["errors"].append(
                                {
                                    "project_id": str(project_id),
                                    "error": result["error"],
                                }
                            )

            # Record last sync time
            await redis_client.set(LAST_SYNC_KEY, datetime.now(UTC).isoformat())
            summary["completed_at"] = datetime.now(UTC).isoformat()

            logger.info(
                "Usage sync completed",
                synced=summary["synced"],
                failed=summary["failed"],
                total_cu=summary["total_cu"],
            )

        finally:
            await self._release_lock()

        return summary

    async def sync_project(self, project_id: uuid.UUID) -> dict[str, Any]:
        """Sync usage for a specific project immediately.

        Useful for on-demand sync before subscription changes.
        """
        async with async_session() as db:
            result = await db.execute(
                select(
                    Subscription.hanzo_subscription_id,
                    Subscription.hanzo_customer_id,
                ).where(
                    Subscription.project_id == project_id
                )
            )
            row = result.first()

            if not row or not row[0] or not row[1]:
                return {
                    "project_id": str(project_id),
                    "synced": False,
                    "error": "No Commerce subscription found",
                }

            return await self._sync_project(project_id, row[0], row[1])

    async def run(self) -> None:
        """Run the sync loop."""
        self._running = True
        logger.info("Usage sync worker started", interval=self.interval)

        while self._running:
            try:
                await self.sync_all_projects()
            except Exception as e:
                logger.error("Usage sync failed", error=str(e))

            # Wait for next interval
            await asyncio.sleep(self.interval)

    async def start(self) -> None:
        """Start the sync worker as a background task."""
        if self._task is not None:
            logger.warning("Sync worker already running")
            return

        self._task = asyncio.create_task(self.run())
        logger.info("Usage sync worker task started")

    async def stop(self) -> None:
        """Stop the sync worker."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Usage sync worker stopped")

    async def get_status(self) -> dict[str, Any]:
        """Get sync worker status."""
        last_sync = await redis_client.get(LAST_SYNC_KEY)
        lock_holder = await redis_client.get(SYNC_LOCK_KEY)

        return {
            "running": self._running,
            "interval_seconds": self.interval,
            "last_sync": last_sync,
            "lock_held": lock_holder is not None,
        }


# Global singleton
usage_sync_worker = UsageSyncWorker()
