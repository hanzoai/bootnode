"""Database models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    type_annotation_map = {
        dict[str, Any]: JSONB,
    }


class User(Base):
    """User model for local authentication."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    roles: Mapped[list[str] | None] = mapped_column(JSONB, default=["user"])
    permissions: Mapped[list[str] | None] = mapped_column(JSONB, default=["read", "write"])
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Project(Base):
    """Project/Organization model.

    Each project belongs to an IAM org (hanzo, lux, zoo, pars, etc.)
    and has access to specific clusters.
    """

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    org_id: Mapped[str] = mapped_column(String(100), nullable=False, default="hanzo")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    allowed_chains: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="project")
    webhooks: Mapped[list["Webhook"]] = relationship(back_populates="project")
    subscription: Mapped["Subscription | None"] = relationship(back_populates="project", uselist=False)
    clusters: Mapped[list["OrgCluster"]] = relationship(back_populates="project")


class ApiKey(Base):
    """API Key model."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)  # First chars for display
    rate_limit: Mapped[int] = mapped_column(Integer, default=100)  # requests per minute
    compute_units_limit: Mapped[int] = mapped_column(Integer, default=1000)  # CU per minute
    allowed_origins: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    allowed_chains: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="api_keys")


class Webhook(Base):
    """Webhook subscription model."""

    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    chain: Mapped[str] = mapped_column(String(50), nullable=False)
    network: Mapped[str] = mapped_column(String(50), nullable=False, default="mainnet")
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)  # For HMAC signing
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="webhooks")
    deliveries: Mapped[list["WebhookDelivery"]] = relationship(back_populates="webhook")


class WebhookDelivery(Base):
    """Webhook delivery attempt model."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    webhook: Mapped["Webhook"] = relationship(back_populates="deliveries")


class Usage(Base):
    """API usage tracking model."""

    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True
    )
    chain: Mapped[str] = mapped_column(String(50), nullable=False)
    network: Mapped[str] = mapped_column(String(50), nullable=False)
    method: Mapped[str] = mapped_column(String(100), nullable=False)
    compute_units: Mapped[int] = mapped_column(Integer, default=1)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SmartWallet(Base):
    """ERC-4337 Smart Wallet model."""

    __tablename__ = "smart_wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    address: Mapped[str] = mapped_column(String(42), nullable=False, unique=True)
    owner_address: Mapped[str] = mapped_column(String(42), nullable=False)
    factory_address: Mapped[str] = mapped_column(String(42), nullable=False)
    chain: Mapped[str] = mapped_column(String(50), nullable=False)
    network: Mapped[str] = mapped_column(String(50), nullable=False, default="mainnet")
    salt: Mapped[str] = mapped_column(String(66), nullable=False)  # bytes32 hex
    is_deployed: Mapped[bool] = mapped_column(Boolean, default=False)
    wallet_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TeamMember(Base):
    """Team member model for project collaboration."""

    __tablename__ = "team_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    invite_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class GasPolicy(Base):
    """Gas sponsorship policy model."""

    __tablename__ = "gas_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    chain: Mapped[str] = mapped_column(String(50), nullable=False)
    network: Mapped[str] = mapped_column(String(50), nullable=False, default="mainnet")
    rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    max_gas_per_op: Mapped[int] = mapped_column(Integer, default=1000000)  # gas units
    max_spend_per_day_usd: Mapped[int] = mapped_column(Integer, default=100)  # in cents
    allowed_contracts: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    allowed_methods: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Subscription(Base):
    """Subscription model for billing and quotas."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    tier: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    hanzo_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hanzo_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Limits (can be overridden from tier defaults)
    monthly_cu_limit: Mapped[int] = mapped_column(Integer, default=30_000_000)
    rate_limit_per_second: Mapped[int] = mapped_column(Integer, default=25)
    max_apps: Mapped[int] = mapped_column(Integer, default=5)
    max_webhooks: Mapped[int] = mapped_column(Integer, default=5)

    # Usage tracking (real-time in Redis, snapshot here)
    current_cu_used: Mapped[int] = mapped_column(Integer, default=0)

    # Billing cycle
    billing_cycle_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    billing_cycle_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Scheduled changes (for downgrades)
    scheduled_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="subscription")


class OrgCluster(Base):
    """Org-to-cluster mapping. Controls which clusters each org/project can manage.

    When a project has OrgCluster entries, fleet operations are scoped to those
    clusters only. When no entries exist, the project has no cluster access
    (except admin projects which bypass this check).
    """

    __tablename__ = "org_clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    cluster_id: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    cluster_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="digitalocean",
    )
    region: Mapped[str] = mapped_column(String(50), nullable=False, default="sfo3")
    allowed_chains: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    allowed_namespaces: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="clusters")
