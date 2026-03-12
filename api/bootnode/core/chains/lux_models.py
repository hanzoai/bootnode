"""Lux-specific fleet models — backward compatibility re-exports.

All generic fleet models live in fleet_models.py. This module provides
Lux-prefixed aliases and Lux-specific network config for backward compat.
New code should import from fleet_models directly.
"""

# Re-export generic models with Lux-prefixed aliases
from bootnode.core.chains.fleet_models import (  # noqa: F401
    CHAIN_NETWORKS,
    CRD_GROUP,
    CRD_PLURAL,
    CRD_VERSION,
    BootstrapConfig,
    FleetCreate,
    FleetResponse,
    FleetStats,
    FleetStatus,
    FleetSummary,
    FleetUpdate,
    ImageConfig,
    NetworkConfig,
    NodeInfo,
    NodeStatus,
    ResourceConfig,
    ResourceSpec,
    ServiceConfig,
    StorageConfig,
    crd_status_to_fleet_response,
    fleet_create_to_crd,
    fleet_update_to_crd_patch,
    get_network_config,
)
from enum import Enum


# Lux-specific aliases
class LuxNetwork(str, Enum):
    MAINNET = "mainnet"
    TESTNET = "testnet"
    DEVNET = "devnet"


# Convenience: Lux network configs (subset of CHAIN_NETWORKS["lux"])
NETWORK_CONFIGS = CHAIN_NETWORKS["lux"]

# Type aliases for backward compatibility
LuxFleetStatus = FleetStatus
LuxNodeStatus = NodeStatus
LuxFleetCreate = FleetCreate
LuxFleetUpdate = FleetUpdate
LuxFleetResponse = FleetResponse
LuxFleetSummary = FleetSummary
LuxFleetStats = FleetStats
LuxNodeInfo = NodeInfo
LuxNetworkConfig = NetworkConfig

# Deprecated Lux-specific sub-models (kept as pass-through)
RLPImportConfig = None  # Now part of chain_config dict
ConsensusConfig = None  # Now part of chain_config dict
ChainTrackingConfig = None  # Now part of chain_config dict
NodeServicesConfig = ServiceConfig
APIConfig = None  # Now part of chain_config dict
