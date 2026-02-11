"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Bootnode"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/v1"

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://bootnode:bootnode@localhost:5432/bootnode"
    )
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    # Authentication
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours
    api_key_salt: str = Field(default="change-me-in-production")

    # Hanzo IAM Integration (hanzo.id, zoo.id, lux.id, pars.id)
    iam_url: str = "https://iam.hanzo.ai"
    iam_client_id: str = ""
    iam_client_secret: str = ""
    enable_multi_tenant: bool = True
    allowed_orgs: list[str] = ["hanzo", "zoo", "lux", "pars"]
    frontend_url: str = "http://localhost:3001"
    allowed_origins: list[str] = []  # Extra CORS origins (comma-separated in env)

    # Rate Limiting
    rate_limit_requests: int = 100  # per minute
    rate_limit_compute_units: int = 1000  # per minute

    # Chain RPCs (upstream nodes)
    eth_mainnet_rpc: str = ""
    eth_sepolia_rpc: str = ""
    eth_holesky_rpc: str = ""
    polygon_mainnet_rpc: str = ""
    polygon_amoy_rpc: str = ""
    arbitrum_mainnet_rpc: str = ""
    arbitrum_sepolia_rpc: str = ""
    optimism_mainnet_rpc: str = ""
    optimism_sepolia_rpc: str = ""
    base_mainnet_rpc: str = ""
    base_sepolia_rpc: str = ""
    avalanche_mainnet_rpc: str = ""
    avalanche_fuji_rpc: str = ""
    bsc_mainnet_rpc: str = ""
    bsc_testnet_rpc: str = ""
    lux_mainnet_rpc: str = ""
    lux_testnet_rpc: str = ""
    lux_devnet_rpc: str = ""
    solana_mainnet_rpc: str = ""
    solana_devnet_rpc: str = ""
    btc_mainnet_rpc: str = ""
    btc_testnet_rpc: str = ""
    btc_rpc_user: str = "bootnode"
    btc_rpc_password: str = ""

    # DataStore (ClickHouse)
    datastore_url: str = "clickhouse://bootnode:bootnode@localhost:8123/bootnode"
    datastore_pool_size: int = 10

    # Vector Search (Qdrant)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Full-Text Search (Meilisearch)
    meilisearch_url: str = "http://localhost:7700"
    meilisearch_api_key: str = ""

    # Lux Indexer (Omnichain data)
    indexer_url: str = "http://localhost:5000"

    # Cloudflare (Edge Caching)
    cloudflare_zone_id: str = ""
    cloudflare_api_token: str = ""

    # Message Queue (Redis-based, @hanzo/mq compatible)
    # Uses the same Redis instance as cache - different db index for isolation
    mq_redis_db: int = 1  # Redis DB index for MQ (separate from cache at db 0)

    # External Services
    ipfs_gateway: str = "https://ipfs.io/ipfs/"

    # Webhooks
    webhook_timeout: int = 30
    webhook_max_retries: int = 5

    # Hanzo Commerce (Stripe-based billing)
    hanzo_commerce_url: str = "https://commerce.hanzo.ai"
    hanzo_commerce_api_key: str = ""
    hanzo_commerce_webhook_secret: str = ""

    # ERC-4337 Bundler
    bundler_private_key: str = ""
    bundler_beneficiary: str = ""

    # ZAP Server (native Cap'n Proto RPC)
    zap_enabled: bool = True
    zap_host: str = "0.0.0.0"
    zap_port: int = 9999

    # Deployment Target
    deploy_target: Literal["docker", "process", "kubernetes"] = "docker"
    deploy_compose_file: str = "infra/compose.yml"
    deploy_k8s_namespace: str = "bootnode"
    deploy_k8s_context: str = ""

    # Helm / Lux Fleet
    helm_chart_path: str = "/opt/charts/lux"
    helm_binary: str = "helm"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
