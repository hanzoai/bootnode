"""DataStore async client — OLAP analytics backend."""

from typing import Any
from urllib.parse import urlparse

import structlog
from aiochclient import ChClient
from aiohttp import ClientSession

from bootnode.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class DataStoreClient:
    """Async DataStore client for high-performance analytics queries."""

    def __init__(self) -> None:
        self._client: ChClient | None = None
        self._session: ClientSession | None = None
        self._url: str = ""
        self._database: str = "bootnode"
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the DataStore connection."""
        if self._initialized:
            return

        url = settings.datastore_url
        if not url:
            logger.warning("DataStore URL not configured, skipping initialization")
            return

        # Parse connection URL: clickhouse://user:pass@host:port/database
        parsed = urlparse(url)
        self._url = f"http://{parsed.hostname}:{parsed.port or 8123}"
        self._database = parsed.path.lstrip("/") or "bootnode"

        self._session = ClientSession()
        self._client = ChClient(
            self._session,
            url=self._url,
            database=self._database,
            user=parsed.username or "default",
            password=parsed.password or "",
        )

        # Test connection
        try:
            _ = await self._client.fetch("SELECT 1")
            logger.info(
                "DataStore connected",
                url=self._url,
                database=self._database,
            )
            self._initialized = True
        except Exception as e:
            logger.error("DataStore connection failed", error=str(e))
            raise

    async def close(self) -> None:
        """Close the connection."""
        if self._session:
            await self._session.close()
            self._session = None
            self._client = None
            self._initialized = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to DataStore."""
        return self._initialized and self._client is not None

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> None:
        """Execute a query without returning results."""
        if not self._client:
            raise RuntimeError("DataStore not initialized")
        await self._client.execute(query, params or {})

    async def fetch(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a query and return results as list of dicts."""
        if not self._client:
            raise RuntimeError("DataStore not initialized")
        rows = await self._client.fetch(query, params or {})
        return [dict(row) for row in rows]

    async def fetchone(
        self, query: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Execute a query and return first result."""
        results = await self.fetch(query, params)
        return results[0] if results else None

    async def fetchval(
        self, query: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Execute a query and return single value."""
        if not self._client:
            raise RuntimeError("DataStore not initialized")
        return await self._client.fetchval(query, params or {})

    async def insert(
        self,
        table: str,
        data: list[dict[str, Any]],
    ) -> None:
        """Insert rows into a table."""
        if not self._client or not data:
            return

        columns = list(data[0].keys())
        values_list = [[row[col] for col in columns] for row in data]

        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES"
        await self._client.execute(query, *values_list)

    async def insert_one(self, table: str, data: dict[str, Any]) -> None:
        """Insert a single row."""
        await self.insert(table, [data])


# Global singleton instance
datastore_client = DataStoreClient()
