"""Shared Pydantic models for Lux fleet management.

This module is the single source of truth for data structures shared between:
  - HelmDeployer (core/deploy/helm.py)
  - Lux Fleet API (api/lux/__init__.py)
  - Lux Chain Manager (core/chains/lux.py)
  - Dashboard (web/app/dashboard/infrastructure/lux/)

All four components import from here. No model duplication.

The models map 1:1 to the Helm chart values in lux/devops/charts/lux/values.yaml
so that API request bodies can be translated directly to helm --set flags or
values override files without lossy conversion.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LuxNetwork(str, Enum):
    """Lux network identifier. Maps to values.network in the Helm chart."""

    MAINNET = "mainnet"
    TESTNET = "testnet"
    DEVNET = "devnet"


class LuxFleetStatus(str, Enum):
    """Lifecycle state of a fleet (Helm release)."""

    PENDING = "pending"          # Request accepted, not yet applied
    DEPLOYING = "deploying"      # helm install/upgrade in progress
    RUNNING = "running"          # All pods healthy
    DEGRADED = "degraded"        # Some pods not ready
    UPDATING = "updating"        # Rolling update in progress
    ERROR = "error"              # Helm or K8s error
    DESTROYING = "destroying"    # helm uninstall in progress
    DESTROYED = "destroyed"      # Release removed


class LuxNodeStatus(str, Enum):
    """Status of an individual luxd pod within a fleet."""

    PENDING = "pending"
    INIT = "init"                # Init container running
    STARTING = "starting"        # luxd process starting
    BOOTSTRAPPING = "bootstrapping"  # RLP import / chain sync
    HEALTHY = "healthy"          # Health endpoint responding
    UNHEALTHY = "unhealthy"      # Failed liveness/readiness
    TERMINATED = "terminated"


# ---------------------------------------------------------------------------
# Helm chart value sub-models
# These mirror the YAML structure in charts/lux/values.yaml exactly.
# ---------------------------------------------------------------------------

class LuxNetworkConfig(BaseModel):
    """Per-network constants. Read-only reference data, not user input."""

    network_id: int
    chain_id: int
    http_port: int
    staking_port: int
    namespace: str


# Canonical network parameters. Must match values.yaml .networks.*
NETWORK_CONFIGS: dict[LuxNetwork, LuxNetworkConfig] = {
    LuxNetwork.MAINNET: LuxNetworkConfig(
        network_id=1,
        chain_id=96369,
        http_port=9630,
        staking_port=9631,
        namespace="lux-mainnet",
    ),
    LuxNetwork.TESTNET: LuxNetworkConfig(
        network_id=2,
        chain_id=96368,
        http_port=9640,
        staking_port=9641,
        namespace="lux-testnet",
    ),
    LuxNetwork.DEVNET: LuxNetworkConfig(
        network_id=3,
        chain_id=96370,
        http_port=9650,
        staking_port=9651,
        namespace="lux-devnet",
    ),
}


class RLPImportConfig(BaseModel):
    """C-chain RLP block import settings. Maps to values.bootstrap.rlpImport."""

    enabled: bool = False
    base_url: str = ""
    rlp_filename: str = ""
    multi_part: bool = False
    parts: list[str] = Field(default_factory=list)
    min_height: int = 1
    timeout: int = 7200


class BootstrapConfig(BaseModel):
    """Bootstrap node configuration. Maps to values.bootstrap."""

    node_ids: list[str] = Field(default_factory=list)
    use_hostnames: bool = True
    external_ips: list[str] = Field(default_factory=list)
    rlp_import: RLPImportConfig = Field(default_factory=RLPImportConfig)

    @field_validator("node_ids")
    @classmethod
    def validate_node_ids(cls, v: list[str]) -> list[str]:
        for nid in v:
            if not nid.startswith("NodeID-"):
                raise ValueError(f"Invalid node ID format: {nid!r} (must start with 'NodeID-')")
        return v


class ConsensusConfig(BaseModel):
    """Consensus tuning. Maps to values.consensus."""

    sample_size: int = 5
    quorum_size: int = 4
    sybil_protection_enabled: bool = False
    require_validator_to_connect: bool = False
    allow_private_ips: bool = True


class ChainTrackingConfig(BaseModel):
    """Subnet/chain tracking. Maps to values.chainTracking."""

    track_all_chains: bool = True
    tracked_chains: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(
        default_factory=lambda: ["zoo", "hanzo", "spc", "pars"],
    )


class ImageConfig(BaseModel):
    """Container image reference. Maps to values.image."""

    repository: str = "registry.digitalocean.com/hanzo/bootnode"
    tag: str = "luxd-v1.23.11"
    pull_policy: str = "Always"


class ResourceSpec(BaseModel):
    """K8s resource request/limit pair."""

    memory: str = "1Gi"
    cpu: str = "500m"


class ResourceConfig(BaseModel):
    """Maps to values.resources."""

    requests: ResourceSpec = Field(default_factory=lambda: ResourceSpec(memory="1Gi", cpu="500m"))
    limits: ResourceSpec = Field(default_factory=lambda: ResourceSpec(memory="4Gi", cpu="2"))


class StorageConfig(BaseModel):
    """Maps to values.storage."""

    size: str = "100Gi"
    storage_class: str = "do-block-storage"


class NodeServicesConfig(BaseModel):
    """Maps to values.nodeServices."""

    enabled: bool = True
    type: str = "LoadBalancer"
    annotations: dict[str, str] = Field(default_factory=dict)


class APIConfig(BaseModel):
    """Maps to values.api."""

    admin_enabled: bool = True
    metrics_enabled: bool = True
    index_enabled: bool = True
    http_allowed_hosts: str = "*"


# ---------------------------------------------------------------------------
# API request/response models
# ---------------------------------------------------------------------------

class LuxFleetCreate(BaseModel):
    """Request body: create a new Lux fleet (Helm release).

    Used by: POST /lux/fleets
    Consumed by: HelmDeployer, LuxChainManager
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z][a-z0-9-]*$",
        description="Helm release name. Must be a valid K8s name.",
    )
    cluster_id: str = Field(
        ...,
        description="Target K8s cluster ID (from /infra/clusters).",
    )
    network: LuxNetwork = LuxNetwork.DEVNET
    replicas: int = Field(default=5, ge=1, le=20)

    # Optional overrides -- None means use chart defaults
    image: Optional[ImageConfig] = None
    bootstrap: Optional[BootstrapConfig] = None
    consensus: Optional[ConsensusConfig] = None
    chain_tracking: Optional[ChainTrackingConfig] = None
    resources: Optional[ResourceConfig] = None
    storage: Optional[StorageConfig] = None
    node_services: Optional[NodeServicesConfig] = None
    api: Optional[APIConfig] = None
    log_level: str = "info"
    db_type: str = "badgerdb"

    @field_validator("replicas")
    @classmethod
    def quorum_safety(cls, v: int) -> int:
        """Warn-level: consensus requires >= 4 for BFT quorum of 5."""
        # Validation only; warning handled at the API layer.
        return v


class LuxFleetUpdate(BaseModel):
    """Request body: update (helm upgrade) an existing fleet.

    Used by: PATCH /lux/fleets/{fleet_id}
    Only non-None fields are applied as overrides.
    """

    replicas: Optional[int] = Field(default=None, ge=1, le=20)
    image: Optional[ImageConfig] = None
    consensus: Optional[ConsensusConfig] = None
    chain_tracking: Optional[ChainTrackingConfig] = None
    resources: Optional[ResourceConfig] = None
    log_level: Optional[str] = None


class LuxNodeInfo(BaseModel):
    """Status of a single luxd pod within a fleet.

    Populated by LuxChainManager from K8s pod status + RPC probes.
    """

    pod_name: str
    pod_index: int
    node_id: Optional[str] = None
    status: LuxNodeStatus = LuxNodeStatus.PENDING
    external_ip: Optional[str] = None
    http_port: int = 9650
    staking_port: int = 9651
    # RPC-derived metrics (populated lazily)
    is_bootstrapped: Optional[bool] = None
    peers: Optional[int] = None
    c_chain_height: Optional[int] = None
    p_chain_height: Optional[int] = None
    uptime_pct: Optional[float] = None
    # K8s resource usage
    cpu_usage: Optional[float] = None
    memory_usage_mb: Optional[float] = None


class LuxFleetResponse(BaseModel):
    """Response body: full fleet state.

    Used by: GET /lux/fleets/{fleet_id}, POST /lux/fleets
    """

    id: str = Field(description="Fleet ID (= Helm release name + network).")
    name: str
    cluster_id: str
    network: LuxNetwork
    status: LuxFleetStatus = LuxFleetStatus.PENDING
    replicas: int
    ready_replicas: int = 0
    image: ImageConfig = Field(default_factory=ImageConfig)
    namespace: str = ""
    helm_revision: Optional[int] = None
    rpc_endpoint: Optional[str] = None
    staking_endpoint: Optional[str] = None
    nodes: list[LuxNodeInfo] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: Optional[str] = None
    error: Optional[str] = None


class LuxFleetSummary(BaseModel):
    """Lightweight fleet summary for list endpoints.

    Used by: GET /lux/fleets
    """

    id: str
    name: str
    network: LuxNetwork
    status: LuxFleetStatus
    replicas: int
    ready_replicas: int = 0
    cluster_id: str
    created_at: str


class LuxFleetStats(BaseModel):
    """Aggregate fleet statistics.

    Used by: GET /lux/stats
    """

    total_fleets: int = 0
    total_nodes: int = 0
    healthy_nodes: int = 0
    fleets_by_network: dict[str, int] = Field(default_factory=dict)
    fleets_by_status: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helm values translation
# ---------------------------------------------------------------------------

def fleet_create_to_helm_values(req: LuxFleetCreate) -> dict:
    """Convert a LuxFleetCreate request into a flat dict suitable for
    helm install --set or a values override YAML file.

    This is the canonical translation layer. HelmDeployer calls this;
    no other component should build Helm values dicts directly.
    """
    vals: dict = {
        "network": req.network.value,
        "replicas": req.replicas,
        "logLevel": req.log_level,
        "dbType": req.db_type,
    }

    if req.image:
        vals["image.repository"] = req.image.repository
        vals["image.tag"] = req.image.tag
        vals["image.pullPolicy"] = req.image.pull_policy

    if req.bootstrap:
        b = req.bootstrap
        vals["bootstrap.useHostnames"] = b.use_hostnames
        if b.node_ids:
            # Helm list: pass as JSON or comma-separated via --set-json
            vals["bootstrap.nodeIDs"] = b.node_ids
        if b.external_ips:
            vals["bootstrap.externalIPs"] = b.external_ips
        r = b.rlp_import
        vals["bootstrap.rlpImport.enabled"] = r.enabled
        vals["bootstrap.rlpImport.baseUrl"] = r.base_url
        vals["bootstrap.rlpImport.rlpFilename"] = r.rlp_filename
        vals["bootstrap.rlpImport.multiPart"] = r.multi_part
        if r.parts:
            vals["bootstrap.rlpImport.parts"] = r.parts
        vals["bootstrap.rlpImport.minHeight"] = r.min_height
        vals["bootstrap.rlpImport.timeout"] = r.timeout

    if req.consensus:
        c = req.consensus
        vals["consensus.sampleSize"] = c.sample_size
        vals["consensus.quorumSize"] = c.quorum_size
        vals["consensus.sybilProtectionEnabled"] = c.sybil_protection_enabled
        vals["consensus.requireValidatorToConnect"] = c.require_validator_to_connect
        vals["consensus.allowPrivateIPs"] = c.allow_private_ips

    if req.chain_tracking:
        ct = req.chain_tracking
        vals["chainTracking.trackAllChains"] = ct.track_all_chains
        if ct.tracked_chains:
            vals["chainTracking.trackedChains"] = ct.tracked_chains
        if ct.aliases:
            vals["chainTracking.aliases"] = ct.aliases

    if req.resources:
        vals["resources.requests.memory"] = req.resources.requests.memory
        vals["resources.requests.cpu"] = req.resources.requests.cpu
        vals["resources.limits.memory"] = req.resources.limits.memory
        vals["resources.limits.cpu"] = req.resources.limits.cpu

    if req.storage:
        vals["storage.size"] = req.storage.size
        vals["storage.storageClass"] = req.storage.storage_class

    if req.node_services:
        vals["nodeServices.enabled"] = req.node_services.enabled
        vals["nodeServices.type"] = req.node_services.type

    if req.api:
        vals["api.adminEnabled"] = req.api.admin_enabled
        vals["api.metricsEnabled"] = req.api.metrics_enabled
        vals["api.indexEnabled"] = req.api.index_enabled
        vals["api.httpAllowedHosts"] = req.api.http_allowed_hosts

    return vals


def fleet_update_to_helm_values(req: LuxFleetUpdate) -> dict:
    """Convert a LuxFleetUpdate into a partial Helm values dict.

    Only non-None fields are included.
    """
    vals: dict = {}

    if req.replicas is not None:
        vals["replicas"] = req.replicas
    if req.log_level is not None:
        vals["logLevel"] = req.log_level
    if req.image:
        vals["image.repository"] = req.image.repository
        vals["image.tag"] = req.image.tag
        vals["image.pullPolicy"] = req.image.pull_policy
    if req.consensus:
        c = req.consensus
        vals["consensus.sampleSize"] = c.sample_size
        vals["consensus.quorumSize"] = c.quorum_size
        vals["consensus.sybilProtectionEnabled"] = c.sybil_protection_enabled
    if req.chain_tracking:
        ct = req.chain_tracking
        vals["chainTracking.trackAllChains"] = ct.track_all_chains
        if ct.tracked_chains:
            vals["chainTracking.trackedChains"] = ct.tracked_chains
    if req.resources:
        vals["resources.requests.memory"] = req.resources.requests.memory
        vals["resources.requests.cpu"] = req.resources.requests.cpu
        vals["resources.limits.memory"] = req.resources.limits.memory
        vals["resources.limits.cpu"] = req.resources.limits.cpu

    return vals
