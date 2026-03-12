"""DataStore client for high-performance analytics."""

from .client import DataStoreClient, datastore_client
from .queries import (
    get_address_activity,
    get_api_usage,
    get_blocks,
    get_nft_transfers,
    get_token_transfers,
    get_transactions,
    record_api_usage,
)

__all__ = [
    "DataStoreClient",
    "datastore_client",
    "get_blocks",
    "get_transactions",
    "get_token_transfers",
    "get_nft_transfers",
    "get_address_activity",
    "get_api_usage",
    "record_api_usage",
]
