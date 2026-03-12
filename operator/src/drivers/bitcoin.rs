//! Bitcoin chain driver (stub).

use super::ChainDriver;
use crate::crd::{HealthSpec, Cluster, NodeStatus, PortMapping};
use crate::error::{OperatorError, Result};
use async_trait::async_trait;

pub struct BitcoinDriver;

#[async_trait]
impl ChainDriver for BitcoinDriver {
    fn name(&self) -> &str {
        "bitcoin"
    }

    fn container_name(&self) -> &str {
        "bitcoind"
    }

    fn default_ports(&self) -> Vec<PortMapping> {
        vec![
            PortMapping { name: "rpc".into(), port: 8332, protocol: None },
            PortMapping { name: "p2p".into(), port: 8333, protocol: None },
        ]
    }

    fn default_health(&self) -> HealthSpec {
        HealthSpec {
            path: "/".into(),
            method: "POST".into(),
            port_name: "rpc".into(),
            ..Default::default()
        }
    }

    fn startup_script(&self, _cluster: &Cluster) -> Result<String> {
        Err(OperatorError::Config(
            "Bitcoin driver not yet implemented".into(),
        ))
    }

    fn startup_gate_script(&self, _cluster: &Cluster) -> Result<String> {
        Err(OperatorError::Config(
            "Bitcoin driver not yet implemented".into(),
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
            "Bitcoin driver not yet implemented".into(),
        ))
    }

    fn validate_config(&self, _chain_config: &serde_json::Value) -> Result<()> {
        Ok(())
    }
}
