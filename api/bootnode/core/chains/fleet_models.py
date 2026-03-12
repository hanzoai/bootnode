"""Fleet models — generic blockchain node fleet management.

Single source of truth for data structures shared between:
  - Bootnode Operator CRDs (operator/src/crd.rs Cluster)
  - Fleet API endpoints (api/lux/, api/ethereum/, etc.)
  - Fleet Manager (core/chains/fleet_manager.py)
  - Dashboard

All components import from here. No model duplication.
Models map to the Cluster CRD (bootnode.dev/v1alpha1).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FleetStatus(str, Enum):
    """Lifecycle state of a node fleet."""

    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    DEGRADED = "degraded"
    UPDATING = "updating"
    ERROR = "error"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"


class NodeStatus(str, Enum):
    """Status of an individual node pod within a fleet."""

    PENDING = "pending"
    INIT = "init"
    STARTING = "starting"
    BOOTSTRAPPING = "bootstrapping"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    TERMINATED = "terminated"


# ---------------------------------------------------------------------------
# Chain network configs — per-chain reference data
# ---------------------------------------------------------------------------

class NetworkConfig(BaseModel):
    """Per-network constants for a specific chain. Read-only reference data."""

    chain: str
    network_id: int
    chain_id: int = 0
    http_port: int
    staking_port: int = 0
    namespace: str


# Registry: chain → network → config
CHAIN_NETWORKS: dict[str, dict[str, NetworkConfig]] = {
    "lux": {
        "mainnet": NetworkConfig(
            chain="lux", network_id=1, chain_id=96369,
            http_port=9630, staking_port=9631, namespace="lux-mainnet",
        ),
        "testnet": NetworkConfig(
            chain="lux", network_id=2, chain_id=96368,
            http_port=9640, staking_port=9641, namespace="lux-testnet",
        ),
        "devnet": NetworkConfig(
            chain="lux", network_id=3, chain_id=96370,
            http_port=9650, staking_port=9651, namespace="lux-devnet",
        ),
    },
    "hanzo": {
        "mainnet": NetworkConfig(
            chain="hanzo", network_id=1, chain_id=1337,
            http_port=8545, namespace="hanzo-mainnet",
        ),
        "testnet": NetworkConfig(
            chain="hanzo", network_id=2, chain_id=13370,
            http_port=8545, namespace="hanzo-testnet",
        ),
    },
    "zoo": {
        "mainnet": NetworkConfig(
            chain="zoo", network_id=1, chain_id=2001,
            http_port=8545, namespace="zoo-mainnet",
        ),
        "testnet": NetworkConfig(
            chain="zoo", network_id=2, chain_id=20010,
            http_port=8545, namespace="zoo-testnet",
        ),
    },
    "pars": {
        "mainnet": NetworkConfig(
            chain="pars", network_id=1, chain_id=3001,
            http_port=9650, staking_port=9651, namespace="pars-mainnet",
        ),
        "testnet": NetworkConfig(
            chain="pars", network_id=2, chain_id=30010,
            http_port=9650, staking_port=9651, namespace="pars-testnet",
        ),
    },
    "avalanche": {
        "mainnet": NetworkConfig(
            chain="avalanche", network_id=1, chain_id=43114,
            http_port=9650, staking_port=9651, namespace="avax-mainnet",
        ),
        "fuji": NetworkConfig(
            chain="avalanche", network_id=5, chain_id=43113,
            http_port=9650, staking_port=9651, namespace="avax-fuji",
        ),
    },
    "ethereum": {
        "mainnet": NetworkConfig(
            chain="ethereum", network_id=1, chain_id=1,
            http_port=8545, namespace="eth-mainnet",
        ),
        "sepolia": NetworkConfig(
            chain="ethereum", network_id=11155111, chain_id=11155111,
            http_port=8545, namespace="eth-sepolia",
        ),
        "holesky": NetworkConfig(
            chain="ethereum", network_id=17000, chain_id=17000,
            http_port=8545, namespace="eth-holesky",
        ),
    },
    "bitcoin": {
        "mainnet": NetworkConfig(
            chain="bitcoin", network_id=0, http_port=8332, namespace="btc-mainnet",
        ),
        "testnet": NetworkConfig(
            chain="bitcoin", network_id=0, http_port=18332, namespace="btc-testnet",
        ),
    },
    "solana": {
        "mainnet": NetworkConfig(
            chain="solana", network_id=0, http_port=8899, namespace="sol-mainnet",
        ),
        "devnet": NetworkConfig(
            chain="solana", network_id=0, http_port=8899, namespace="sol-devnet",
        ),
    },
    "filecoin": {
        "mainnet": NetworkConfig(
            chain="filecoin", network_id=314, chain_id=314,
            http_port=1234, namespace="fil-mainnet",
        ),
        "calibration": NetworkConfig(
            chain="filecoin", network_id=314159, chain_id=314159,
            http_port=1234, namespace="fil-calibration",
        ),
    },
}


def get_network_config(chain: str, network: str) -> NetworkConfig:
    """Look up network config for a chain + network pair."""
    chain_nets = CHAIN_NETWORKS.get(chain)
    if not chain_nets:
        raise ValueError(f"Unknown chain: {chain!r}. Available: {list(CHAIN_NETWORKS.keys())}")
    cfg = chain_nets.get(network)
    if not cfg:
        raise ValueError(
            f"Unknown network {network!r} for chain {chain!r}. "
            f"Available: {list(chain_nets.keys())}"
        )
    return cfg


# ---------------------------------------------------------------------------
# Sub-models — shared across all chains
# ---------------------------------------------------------------------------

class ImageConfig(BaseModel):
    """Container image reference."""

    repository: str = "ghcr.io/hanzoai/bootnode"
    tag: str = "latest"
    pull_policy: str = "IfNotPresent"


class ResourceSpec(BaseModel):
    """K8s resource request/limit pair."""

    memory: str = "1Gi"
    cpu: str = "500m"


class ResourceConfig(BaseModel):
    """K8s resource requests and limits."""

    requests: ResourceSpec = Field(default_factory=lambda: ResourceSpec(memory="1Gi", cpu="500m"))
    limits: ResourceSpec = Field(default_factory=lambda: ResourceSpec(memory="4Gi", cpu="2"))


class StorageConfig(BaseModel):
    """Persistent storage settings."""

    size: str = "100Gi"
    storage_class: str = "do-block-storage"


class ServiceConfig(BaseModel):
    """K8s service exposure settings."""

    enabled: bool = True
    type: str = "LoadBalancer"
    annotations: dict[str, str] = Field(default_factory=dict)


class BootstrapConfig(BaseModel):
    """Bootstrap node configuration."""

    use_hostnames: bool = True
    external_ips: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API request/response models
# ---------------------------------------------------------------------------

class FleetCreate(BaseModel):
    """Request body: create a new node fleet.

    Used by: POST /fleets or POST /{chain}/fleets
    The `chain` field selects the operator driver. Everything in
    `chain_config` is chain-specific and opaque to the generic layer.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z][a-z0-9-]*$",
        description="Fleet name. Must be a valid K8s name.",
    )
    cluster_id: str = Field(
        ...,
        description="Target K8s cluster ID (from /infra/clusters).",
    )
    chain: str = Field(
        default="lux",
        description="Chain type: lux, avalanche, ethereum, bitcoin.",
    )
    network: str = Field(
        default="devnet",
        description="Network name: mainnet, testnet, devnet, etc.",
    )
    replicas: int = Field(default=5, ge=1, le=100)

    # Generic overrides
    image: Optional[ImageConfig] = None
    resources: Optional[ResourceConfig] = None
    storage: Optional[StorageConfig] = None
    service: Optional[ServiceConfig] = None
    bootstrap: Optional[BootstrapConfig] = None

    # Chain-specific config (opaque to generic layer, interpreted by driver)
    chain_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("chain")
    @classmethod
    def validate_chain(cls, v: str) -> str:
        if v not in CHAIN_NETWORKS:
            raise ValueError(f"Unknown chain: {v!r}. Available: {list(CHAIN_NETWORKS.keys())}")
        return v


class FleetUpdate(BaseModel):
    """Request body: update an existing fleet.

    Only non-None fields are applied as overrides.
    """

    replicas: Optional[int] = Field(default=None, ge=1, le=100)
    image: Optional[ImageConfig] = None
    resources: Optional[ResourceConfig] = None

    # Partial chain_config update (merged with existing)
    chain_config: Optional[dict[str, Any]] = None


class NodeInfo(BaseModel):
    """Status of a single node pod within a fleet."""

    pod_name: str
    pod_index: int
    node_id: Optional[str] = None
    status: NodeStatus = NodeStatus.PENDING
    external_ip: Optional[str] = None
    healthy: bool = False
    bootstrapped: bool = False
    peers: Optional[int] = None
    # Chain-specific metrics (driver populates these)
    extra: dict[str, Any] = Field(default_factory=dict)


class FleetResponse(BaseModel):
    """Response body: full fleet state."""

    id: str = Field(description="Fleet ID.")
    name: str
    cluster_id: str
    chain: str
    network: str
    status: FleetStatus = FleetStatus.PENDING
    replicas: int
    ready_replicas: int = 0
    image: Optional[ImageConfig] = None
    namespace: str = ""
    rpc_endpoint: Optional[str] = None
    p2p_endpoint: Optional[str] = None
    nodes: list[NodeInfo] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: Optional[str] = None
    error: Optional[str] = None


class FleetSummary(BaseModel):
    """Lightweight fleet summary for list endpoints."""

    id: str
    name: str
    chain: str
    network: str
    status: FleetStatus
    replicas: int
    ready_replicas: int = 0
    cluster_id: str
    created_at: str


class FleetStats(BaseModel):
    """Aggregate fleet statistics."""

    total_fleets: int = 0
    total_nodes: int = 0
    healthy_nodes: int = 0
    fleets_by_chain: dict[str, int] = Field(default_factory=dict)
    fleets_by_network: dict[str, int] = Field(default_factory=dict)
    fleets_by_status: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# CRD constants — must match operator/src/crd.rs
# ---------------------------------------------------------------------------

CRD_GROUP = "bootnode.dev"
CRD_VERSION = "v1alpha1"
CRD_PLURAL = "clusters"


# ---------------------------------------------------------------------------
# CRD translation
# ---------------------------------------------------------------------------

def fleet_create_to_crd(req: FleetCreate) -> dict:
    """Convert a FleetCreate API request into a Cluster CR body.

    This is the canonical translation layer. FleetManager calls this;
    no other component should build CR bodies directly.
    """
    net_cfg = get_network_config(req.chain, req.network)

    spec: dict = {
        "chain": req.chain,
        "network": req.network,
        "replicas": req.replicas,
        "chainConfig": req.chain_config,
    }

    if req.image:
        spec["image"] = {
            "repository": req.image.repository,
            "tag": req.image.tag,
            "pullPolicy": req.image.pull_policy,
        }

    if req.resources:
        spec["resources"] = {
            "cpuRequest": req.resources.requests.cpu,
            "cpuLimit": req.resources.limits.cpu,
            "memoryRequest": req.resources.requests.memory,
            "memoryLimit": req.resources.limits.memory,
        }

    if req.storage:
        spec["storage"] = {
            "size": req.storage.size,
            "storageClass": req.storage.storage_class,
        }

    if req.service:
        spec["service"] = {
            "serviceType": req.service.type,
            "perNodeLb": req.service.enabled,
            "annotations": req.service.annotations,
        }

    # Set ports from network config
    ports = [{"name": "http", "port": net_cfg.http_port}]
    if net_cfg.staking_port:
        ports.append({"name": "staking", "port": net_cfg.staking_port})
    spec["ports"] = ports

    if req.bootstrap:
        spec["bootstrap"] = {
            "useHostnames": req.bootstrap.use_hostnames,
            "externalIps": req.bootstrap.external_ips,
        }

    cr_name = f"{req.chain}d-{req.network}"

    return {
        "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
        "kind": "Cluster",
        "metadata": {
            "name": cr_name,
            "namespace": net_cfg.namespace,
            "labels": {
                "bootnode.dev/chain": req.chain,
                "bootnode.dev/network": req.network,
            },
        },
        "spec": spec,
    }


def fleet_update_to_crd_patch(req: FleetUpdate) -> dict:
    """Convert a FleetUpdate into a partial CR spec for JSON merge patch."""
    spec: dict = {}

    if req.replicas is not None:
        spec["replicas"] = req.replicas

    if req.image:
        spec["image"] = {
            "repository": req.image.repository,
            "tag": req.image.tag,
            "pullPolicy": req.image.pull_policy,
        }

    if req.resources:
        spec["resources"] = {
            "cpuRequest": req.resources.requests.cpu,
            "cpuLimit": req.resources.limits.cpu,
            "memoryRequest": req.resources.requests.memory,
            "memoryLimit": req.resources.limits.memory,
        }

    if req.chain_config:
        spec["chainConfig"] = req.chain_config

    return {"spec": spec} if spec else {}


def crd_status_to_fleet_response(
    cr: dict,
    cluster_id: str,
) -> FleetResponse:
    """Convert a Cluster CR (with status) into a FleetResponse."""
    spec = cr.get("spec", {})
    status = cr.get("status", {})
    metadata = cr.get("metadata", {})

    phase = status.get("phase", "Pending")
    status_map = {
        "Pending": FleetStatus.PENDING,
        "Creating": FleetStatus.DEPLOYING,
        "Bootstrapping": FleetStatus.DEPLOYING,
        "Running": FleetStatus.RUNNING,
        "Degraded": FleetStatus.DEGRADED,
    }
    fleet_status = status_map.get(phase, FleetStatus.ERROR)

    nodes = []
    for i, ns in enumerate(status.get("nodes", [])):
        nodes.append(NodeInfo(
            pod_name=ns.get("podName", f"node-{i}"),
            pod_index=i,
            node_id=ns.get("nodeId"),
            status=NodeStatus.HEALTHY if ns.get("healthy") else NodeStatus.UNHEALTHY,
            external_ip=ns.get("externalIp"),
            healthy=ns.get("healthy", False),
            bootstrapped=ns.get("bootstrapped", False),
            peers=ns.get("connectedPeers"),
            extra=ns.get("extra", {}),
        ))

    img_spec = spec.get("image", {})
    image = ImageConfig(
        repository=img_spec.get("repository", ImageConfig().repository),
        tag=img_spec.get("tag", ImageConfig().tag),
        pull_policy=img_spec.get("pullPolicy", ImageConfig().pull_policy),
    ) if img_spec else None

    return FleetResponse(
        id=f"{cluster_id}:{metadata.get('name', '')}",
        name=metadata.get("name", ""),
        cluster_id=cluster_id,
        chain=spec.get("chain", ""),
        network=spec.get("network", ""),
        status=fleet_status,
        replicas=status.get("totalNodes", spec.get("replicas", 0)),
        ready_replicas=status.get("readyNodes", 0),
        image=image,
        namespace=metadata.get("namespace", ""),
        nodes=nodes,
        created_at=metadata.get("creationTimestamp", ""),
        updated_at=status.get("lastReconciled"),
    )
