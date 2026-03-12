//! Chain driver abstraction.
//!
//! Every blockchain implements [`ChainDriver`]. The generic controller
//! calls driver methods at the right points — startup script generation,
//! health checks, node identity extraction, etc.
//!
//! Register new drivers in [`DriverRegistry::new`].

pub mod bitcoin;
pub mod ethereum;
pub mod lux;

use crate::crd::{HealthSpec, Cluster, NodeStatus, PortMapping};
use crate::error::Result;
use async_trait::async_trait;
use std::collections::BTreeMap;
use std::sync::Arc;

/// Chain-specific behavior. One implementation per blockchain family.
#[async_trait]
pub trait ChainDriver: Send + Sync {
    /// Identifier: "lux", "avalanche", "ethereum", "bitcoin".
    fn name(&self) -> &str;

    /// Container name for the main process (e.g. "luxd", "geth").
    fn container_name(&self) -> &str;

    /// Default ports when user doesn't specify any.
    fn default_ports(&self) -> Vec<PortMapping>;

    /// Default health spec when user doesn't override.
    fn default_health(&self) -> HealthSpec;

    /// Generate the main startup script (runs as PID 1 in container).
    fn startup_script(&self, cluster: &Cluster) -> Result<String>;

    /// Generate the startup gate init-container script.
    fn startup_gate_script(&self, cluster: &Cluster) -> Result<String>;

    /// Generate the init-container script (plugin setup, staking keys, etc.).
    fn init_script(&self, cluster: &Cluster) -> Result<Option<String>>;

    /// Extra environment variables for the main container.
    fn env_vars(&self, cluster: &Cluster) -> Vec<(String, String)>;

    /// Check a single node's health. Returns updated NodeStatus.
    async fn check_node_health(
        &self,
        cluster: &Cluster,
        pod_name: &str,
        pod_ip: &str,
    ) -> Result<NodeStatus>;

    /// Validate chain_config before reconciliation starts.
    fn validate_config(&self, chain_config: &serde_json::Value) -> Result<()>;
}

/// Registry of available chain drivers.
pub struct DriverRegistry {
    drivers: BTreeMap<String, Arc<dyn ChainDriver>>,
}

impl DriverRegistry {
    pub fn new() -> Self {
        let mut drivers: BTreeMap<String, Arc<dyn ChainDriver>> = BTreeMap::new();
        drivers.insert("lux".into(), Arc::new(lux::LuxDriver));
        drivers.insert("avalanche".into(), Arc::new(lux::LuxDriver)); // same family
        drivers.insert("ethereum".into(), Arc::new(ethereum::EthereumDriver));
        drivers.insert("bitcoin".into(), Arc::new(bitcoin::BitcoinDriver));
        Self { drivers }
    }

    pub fn get(&self, chain: &str) -> Option<Arc<dyn ChainDriver>> {
        self.drivers.get(chain).cloned()
    }

    pub fn chains(&self) -> Vec<&str> {
        self.drivers.keys().map(|s| s.as_str()).collect()
    }
}
