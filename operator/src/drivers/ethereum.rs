//! Ethereum chain driver (stub).

use super::ChainDriver;
use crate::crd::{HealthSpec, Cluster, NodeStatus, PortMapping};
use crate::error::{OperatorError, Result};
use async_trait::async_trait;

pub struct EthereumDriver;

#[async_trait]
impl ChainDriver for EthereumDriver {
    fn name(&self) -> &str {
        "ethereum"
    }

    fn container_name(&self) -> &str {
        "geth"
    }

    fn default_ports(&self) -> Vec<PortMapping> {
        vec![
            PortMapping { name: "http".into(), port: 8545, protocol: None },
            PortMapping { name: "ws".into(), port: 8546, protocol: None },
            PortMapping { name: "p2p".into(), port: 30303, protocol: None },
            PortMapping { name: "metrics".into(), port: 6060, protocol: None },
        ]
    }

    fn default_health(&self) -> HealthSpec {
        HealthSpec {
            path: "/".into(),
            method: "POST".into(),
            port_name: "http".into(),
            ..Default::default()
        }
    }

    fn startup_script(&self, _cluster: &Cluster) -> Result<String> {
        Err(OperatorError::Config(
            "Ethereum driver not yet implemented".into(),
        ))
    }

    fn startup_gate_script(&self, _cluster: &Cluster) -> Result<String> {
        Err(OperatorError::Config(
            "Ethereum driver not yet implemented".into(),
        ))
    }

    fn init_script(&self, _cluster: &Cluster) -> Result<Option<String>> {
        Ok(None)
    }

    fn env_vars(&self, _cluster: &Cluster) -> Vec<(String, String)> {
        vec![]
    }

    async fn check_node_health(
        &self,
        _cluster: &Cluster,
        _pod_name: &str,
        _pod_ip: &str,
    ) -> Result<NodeStatus> {
        Err(OperatorError::Config(
            "Ethereum driver not yet implemented".into(),
        ))
    }

    fn validate_config(&self, _chain_config: &serde_json::Value) -> Result<()> {
        Ok(())
    }
}
