//! Generic blockchain CRDs.
//!
//! One CRD (`Cluster`) handles all chains: Lux, Avalanche, Ethereum, Bitcoin, etc.
//! Chain-specific behavior lives in drivers (see `drivers/`). The CRD carries
//! chain-specific config as an opaque JSON value interpreted by the driver.
//!
//! Naming: A `Cluster` (bootnode.dev/v1alpha1) is a cluster of blockchain nodes
//! on a single K8s cluster. A "Fleet" is the API-level concept spanning multiple
//! Clusters across providers/regions.

use k8s_openapi::apimachinery::pkg::apis::meta::v1::Condition;
use kube::CustomResource;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

// ---------------------------------------------------------------------------
// Cluster — primary CRD (a cluster of blockchain nodes on one K8s cluster)
// ---------------------------------------------------------------------------

/// A cluster of blockchain nodes managed as a StatefulSet.
///
/// Works for any chain. The `chain` field selects the driver that interprets
/// `chain_config` and generates the startup script, health checks, etc.
#[derive(CustomResource, Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[kube(
    group = "bootnode.dev",
    version = "v1alpha1",
    kind = "Cluster",
    namespaced,
    status = "ClusterStatus",
    shortname = "bc",
    printcolumn = r#"{"name":"Chain","type":"string","jsonPath":".spec.chain"}"#,
    printcolumn = r#"{"name":"Network","type":"string","jsonPath":".spec.network"}"#,
    printcolumn = r#"{"name":"Phase","type":"string","jsonPath":".status.phase"}"#,
    printcolumn = r#"{"name":"Ready","type":"string","jsonPath":".status.readyNodes"}"#,
    printcolumn = r#"{"name":"Total","type":"string","jsonPath":".status.totalNodes"}"#,
    printcolumn = r#"{"name":"Age","type":"date","jsonPath":".metadata.creationTimestamp"}"#
)]
#[serde(rename_all = "camelCase")]
pub struct ClusterSpec {
    // ---- Chain identification ----

    /// Chain type: "lux", "avalanche", "ethereum", "bitcoin", etc.
    /// Selects the driver that interprets chain_config.
    pub chain: String,

    /// Network name: "mainnet", "testnet", "devnet", or custom.
    pub network: String,

    // ---- Topology ----

    /// Number of nodes (validators/peers).
    pub replicas: u32,

    // ---- Image ----

    /// Container image.
    #[serde(default)]
    pub image: ImageSpec,

    // ---- Resources ----

    #[serde(default)]
    pub resources: ResourceSpec,

    #[serde(default)]
    pub storage: StorageSpec,

    // ---- Networking ----

    /// Port mappings. Drivers provide defaults; user can override.
    #[serde(default)]
    pub ports: Vec<PortMapping>,

    /// Service exposure settings.
    #[serde(default)]
    pub service: ServiceSpec,

    // ---- Bootstrap ----

    #[serde(default)]
    pub bootstrap: BootstrapSpec,

    // ---- Health ----

    #[serde(default)]
    pub health: HealthSpec,

    // ---- Lifecycle ----

    #[serde(default)]
    pub upgrade_strategy: UpgradeStrategy,

    #[serde(default)]
    pub startup_gate: StartupGateSpec,

    /// Explicit opt-in to scale down (remove nodes).
    #[serde(default)]
    pub allow_scale_down: bool,

    // ---- Chain-specific ----

    /// Opaque config interpreted by the chain driver.
    /// For Lux: consensus, chain_tracking, rlp_import, evm_config, etc.
    /// For Ethereum: execution_client, consensus_client, jwt_secret, etc.
    #[serde(default)]
    pub chain_config: serde_json::Value,

    /// Genesis data (inline JSON).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub genesis: Option<serde_json::Value>,

    /// Pre-existing genesis ConfigMap name.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub genesis_config_map: Option<String>,

    /// Arbitrary node config overrides (merged into generated config).
    #[serde(default)]
    pub config: BTreeMap<String, serde_json::Value>,

    // ---- Init / plugins ----

    #[serde(skip_serializing_if = "Option::is_none")]
    pub init: Option<InitSpec>,

    /// Custom startup script ConfigMap (bypasses driver generation).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub startup_script: Option<String>,

    // ---- Security ----

    #[serde(default)]
    pub security: SecuritySpec,

    /// Adopt existing resources instead of creating new ones.
    #[serde(default)]
    pub adopt_existing: bool,

    // ---- Staking / identity ----

    #[serde(skip_serializing_if = "Option::is_none")]
    pub staking: Option<StakingSpec>,

    // ---- Seed restore ----

    #[serde(default)]
    pub seed_restore: SeedRestoreSpec,
}

// ---------------------------------------------------------------------------
// Sub-specs (shared across all chains)
// ---------------------------------------------------------------------------

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct ImageSpec {
    #[serde(default = "default_image_repo")]
    pub repository: String,
    #[serde(default = "default_image_tag")]
    pub tag: String,
    #[serde(default = "default_pull_policy")]
    pub pull_policy: String,
    #[serde(default)]
    pub pull_secrets: Vec<String>,
}

fn default_image_repo() -> String { "ghcr.io/hanzoai/bootnode".to_string() }
fn default_image_tag() -> String { "latest".to_string() }
fn default_pull_policy() -> String { "IfNotPresent".to_string() }

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct ResourceSpec {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cpu_request: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cpu_limit: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub memory_request: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub memory_limit: Option<String>,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct StorageSpec {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub storage_class: Option<String>,
    #[serde(default = "default_storage_size")]
    pub size: String,
}

fn default_storage_size() -> String { "200Gi".to_string() }

/// Named port mapping (used by all chains).
#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct PortMapping {
    pub name: String,
    pub port: i32,
    #[serde(default)]
    pub protocol: Option<String>,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct ServiceSpec {
    #[serde(default = "default_service_type")]
    pub service_type: String,
    #[serde(default)]
    pub annotations: BTreeMap<String, String>,
    /// Create per-node LoadBalancer services for stable P2P IPs.
    #[serde(default = "default_true")]
    pub per_node_lb: bool,
}

fn default_service_type() -> String { "LoadBalancer".to_string() }

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct BootstrapSpec {
    /// Use internal K8s DNS for bootstrap.
    #[serde(default = "default_true")]
    pub use_hostnames: bool,
    /// Static external IPs (overrides LB discovery).
    #[serde(default)]
    pub external_ips: Vec<String>,
}

impl Default for BootstrapSpec {
    fn default() -> Self {
        Self {
            use_hostnames: true,
            external_ips: vec![],
        }
    }
}

#[derive(Deserialize, Serialize, Clone, Debug, PartialEq, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct HealthSpec {
    /// HTTP path for health check (e.g. "/ext/health" for Lux, "/healthz" for Ethereum).
    #[serde(default = "default_health_path")]
    pub path: String,
    /// HTTP method (GET or POST).
    #[serde(default = "default_health_method")]
    pub method: String,
    /// Port name to use for health checks (matches a PortMapping name).
    #[serde(default = "default_health_port_name")]
    pub port_name: String,
    /// Grace period after pod start before enforcing requirements.
    #[serde(default = "default_health_grace")]
    pub grace_period_seconds: u64,
    /// Check interval.
    #[serde(default = "default_health_interval")]
    pub check_interval_seconds: u64,
    /// Max height skew between nodes before marking Degraded.
    #[serde(default = "default_max_height_skew")]
    pub max_height_skew: u64,
}

impl Default for HealthSpec {
    fn default() -> Self {
        Self {
            path: default_health_path(),
            method: default_health_method(),
            port_name: default_health_port_name(),
            grace_period_seconds: default_health_grace(),
            check_interval_seconds: default_health_interval(),
            max_height_skew: default_max_height_skew(),
        }
    }
}

fn default_health_path() -> String { "/ext/health".to_string() }
fn default_health_method() -> String { "GET".to_string() }
fn default_health_port_name() -> String { "http".to_string() }
fn default_health_grace() -> u64 { 300 }
fn default_health_interval() -> u64 { 60 }
fn default_max_height_skew() -> u64 { 10 }

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct UpgradeStrategy {
    /// "OnDelete" (safest) or "RollingUpdate".
    #[serde(default = "default_upgrade_type")]
    pub strategy_type: String,
    #[serde(default = "default_one")]
    pub max_unavailable: u32,
    #[serde(default = "default_true")]
    pub health_check_between_restarts: bool,
    #[serde(default = "default_stabilization")]
    pub stabilization_seconds: u64,
}

impl Default for UpgradeStrategy {
    fn default() -> Self {
        Self {
            strategy_type: default_upgrade_type(),
            max_unavailable: 1,
            health_check_between_restarts: true,
            stabilization_seconds: default_stabilization(),
        }
    }
}

fn default_upgrade_type() -> String { "OnDelete".to_string() }
fn default_one() -> u32 { 1 }
fn default_stabilization() -> u64 { 60 }

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct StartupGateSpec {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_min_peers")]
    pub min_peers: u32,
    #[serde(default = "default_gate_timeout")]
    pub timeout_seconds: u64,
    #[serde(default = "default_gate_interval")]
    pub check_interval_seconds: u64,
    /// "Fail" (exit 1, pod restarts) or "StartAnyway".
    #[serde(default = "default_on_timeout")]
    pub on_timeout: String,
}

impl Default for StartupGateSpec {
    fn default() -> Self {
        Self {
            enabled: true,
            min_peers: 2,
            timeout_seconds: 300,
            check_interval_seconds: 5,
            on_timeout: "Fail".to_string(),
        }
    }
}

fn default_min_peers() -> u32 { 2 }
fn default_gate_timeout() -> u64 { 300 }
fn default_gate_interval() -> u64 { 5 }
fn default_on_timeout() -> String { "Fail".to_string() }

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct StakingSpec {
    /// Secret name containing node identity keys.
    pub secret_name: String,
    /// KMS configuration for syncing keys.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub kms: Option<KmsSpec>,
}

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct KmsSpec {
    pub host_api: String,
    pub project_slug: String,
    pub env_slug: String,
    #[serde(default = "default_kms_path")]
    pub secrets_path: String,
    pub auth: KmsAuthSpec,
    #[serde(default = "default_kms_resync")]
    pub resync_interval: u64,
}

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct KmsAuthSpec {
    pub credentials_secret: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub credentials_namespace: Option<String>,
}

fn default_kms_path() -> String { "/staking".to_string() }
fn default_kms_resync() -> u64 { 300 }

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct InitSpec {
    pub image: String,
    #[serde(default = "default_pull_policy")]
    pub pull_policy: String,
    #[serde(default)]
    pub plugins: Vec<PluginSpec>,
    #[serde(default)]
    pub clear_data: bool,
}

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct PluginSpec {
    pub source: String,
    pub dest: String,
}

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct SecuritySpec {
    #[serde(default = "default_uid")]
    pub run_as_user: i64,
    #[serde(default = "default_uid")]
    pub run_as_group: i64,
    #[serde(default = "default_uid")]
    pub fs_group: i64,
}

impl Default for SecuritySpec {
    fn default() -> Self {
        Self {
            run_as_user: 1000,
            run_as_group: 1000,
            fs_group: 1000,
        }
    }
}

fn default_uid() -> i64 { 1000 }

#[derive(Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct SeedRestoreSpec {
    #[serde(default)]
    pub enabled: bool,
    /// "None", "ObjectStore", "PVCClone", "VolumeSnapshot".
    #[serde(default = "default_seed_source")]
    pub source_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub object_store_url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub volume_snapshot_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub donor_pvc_name: Option<String>,
    #[serde(default = "default_restore_policy")]
    pub restore_policy: String,
    #[serde(default = "default_marker_path")]
    pub marker_path: String,
}

impl Default for SeedRestoreSpec {
    fn default() -> Self {
        Self {
            enabled: false,
            source_type: "None".to_string(),
            object_store_url: None,
            volume_snapshot_name: None,
            donor_pvc_name: None,
            restore_policy: "IfNotSeeded".to_string(),
            marker_path: "/data/.seeded".to_string(),
        }
    }
}

fn default_seed_source() -> String { "None".to_string() }
fn default_restore_policy() -> String { "IfNotSeeded".to_string() }
fn default_marker_path() -> String { "/data/.seeded".to_string() }

fn default_true() -> bool { true }

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct ClusterStatus {
    /// Pending, Creating, Bootstrapping, Running, Degraded.
    #[serde(default)]
    pub phase: String,
    #[serde(default)]
    pub ready_nodes: u32,
    #[serde(default)]
    pub total_nodes: u32,
    #[serde(default)]
    pub bootstrap_endpoints: Vec<String>,
    #[serde(default)]
    pub external_ips: BTreeMap<String, String>,
    #[serde(default)]
    pub node_statuses: BTreeMap<String, NodeStatus>,
    #[serde(default)]
    pub chain_statuses: BTreeMap<String, ChainStatus>,
    #[serde(default)]
    pub degraded_reasons: Vec<DegradedCondition>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub network_metrics: Option<NetworkMetrics>,
    #[serde(default)]
    #[schemars(skip)]
    pub conditions: Vec<Condition>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub observed_generation: Option<i64>,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, PartialEq, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct NodeStatus {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub node_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub external_ip: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub block_height: Option<u64>,
    #[serde(default)]
    pub connected_peers: u32,
    #[serde(default)]
    pub inbound_peers: u32,
    #[serde(default)]
    pub outbound_peers: u32,
    #[serde(default)]
    pub bootstrapped: bool,
    #[serde(default)]
    pub healthy: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub start_time: Option<String>,
    /// Driver-specific extra status fields.
    #[serde(default)]
    pub extra: BTreeMap<String, serde_json::Value>,
}

#[derive(Deserialize, Serialize, Clone, Debug, PartialEq, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct ChainStatus {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub alias: Option<String>,
    #[serde(default)]
    pub healthy: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub block_height: Option<u64>,
}

#[derive(Deserialize, Serialize, Clone, Debug, PartialEq, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct DegradedCondition {
    pub reason: DegradedReason,
    pub message: String,
    #[serde(default)]
    pub affected_nodes: Vec<String>,
}

#[derive(Deserialize, Serialize, Clone, Debug, PartialEq, JsonSchema)]
pub enum DegradedReason {
    BootstrapBlocked,
    HeightSkew,
    InboundPeersTooLow,
    ChainUnhealthy,
    PodNotReady,
    NodeUnhealthy,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, PartialEq, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct NetworkMetrics {
    #[serde(default)]
    pub min_height: u64,
    #[serde(default)]
    pub max_height: u64,
    #[serde(default)]
    pub height_skew: u64,
    #[serde(default)]
    pub bootstrapped_chains: u32,
    #[serde(default)]
    pub total_peers: u32,
}

// ---------------------------------------------------------------------------
// ChainDeployment — secondary CRD for subnet/L2 chains
// ---------------------------------------------------------------------------

#[derive(CustomResource, Deserialize, Serialize, Clone, Debug, JsonSchema)]
#[kube(
    group = "bootnode.dev",
    version = "v1alpha1",
    kind = "ChainDeployment",
    namespaced,
    status = "ChainDeploymentStatus",
    shortname = "cd",
    printcolumn = r#"{"name":"Phase","type":"string","jsonPath":".status.phase"}"#,
    printcolumn = r#"{"name":"ChainID","type":"string","jsonPath":".status.chainId"}"#
)]
#[serde(rename_all = "camelCase")]
pub struct ChainDeploymentSpec {
    /// Parent Cluster name.
    pub cluster_ref: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub chain_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub blockchain_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub alias: Option<String>,
    /// Chain-specific VM/client config.
    #[serde(default)]
    pub config: serde_json::Value,
}

#[derive(Deserialize, Serialize, Clone, Debug, Default, JsonSchema)]
#[serde(rename_all = "camelCase")]
pub struct ChainDeploymentStatus {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub chain_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub blockchain_id: Option<String>,
    #[serde(default)]
    pub phase: String,
    #[serde(default)]
    #[schemars(skip)]
    pub conditions: Vec<Condition>,
}
