//! Lux / Avalanche chain driver.
//!
//! Generates startup scripts, health checks, and node identity extraction
//! for luxd-based chains (Lux mainnet/testnet/devnet and Avalanche).

use super::ChainDriver;
use crate::crd::{HealthSpec, Cluster, NodeStatus, PortMapping};
use crate::error::{OperatorError, Result};
use async_trait::async_trait;
use kube::ResourceExt;
use serde::Deserialize;
use std::collections::BTreeMap;
use std::time::Duration;

/// Lux-specific chain_config fields (deserialized from opaque JSON).
#[derive(Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct LuxConfig {
    #[serde(default)]
    network_id: u32,
    #[serde(default = "default_http_port")]
    http_port: i32,
    #[serde(default = "default_staking_port")]
    staking_port: i32,
    #[serde(default = "default_db_type")]
    db_type: String,
    #[serde(default)]
    sybil_protection_enabled: Option<bool>,
    #[serde(default)]
    require_validator_to_connect: Option<bool>,
    #[serde(default)]
    allow_private_ips: Option<bool>,
    #[serde(default)]
    network_compression_type: Option<String>,
    #[serde(default)]
    consensus: Option<ConsensusConfig>,
    #[serde(default)]
    chain_tracking: Option<ChainTrackingConfig>,
    #[serde(default)]
    evm_config: Option<serde_json::Value>,
    #[serde(default)]
    chains: Vec<ChainRef>,
    #[serde(default)]
    chain_aliases: Option<BTreeMap<String, Vec<String>>>,
    #[serde(default)]
    rlp_import: Option<RlpImportConfig>,
    #[serde(default)]
    api: Option<ApiConfig>,
    #[serde(default)]
    upgrade_config: Option<serde_json::Value>,
    #[serde(default)]
    import_chain_data: Option<String>,
}

fn default_http_port() -> i32 { 9650 }
fn default_staking_port() -> i32 { 9651 }
fn default_db_type() -> String { "leveldb".into() }

#[derive(Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct ConsensusConfig {
    #[serde(default = "default_sample")]
    sample_size: u32,
    #[serde(default = "default_quorum")]
    quorum_size: u32,
}
fn default_sample() -> u32 { 5 }
fn default_quorum() -> u32 { 4 }

#[derive(Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct ChainTrackingConfig {
    #[serde(default)]
    track_all_chains: bool,
    #[serde(default)]
    tracked_chains: Vec<String>,
    #[serde(default)]
    aliases: Vec<String>,
}

#[derive(Deserialize, Default, Clone)]
#[serde(rename_all = "camelCase")]
struct ChainRef {
    blockchain_id: String,
    alias: String,
    tracking_id: Option<String>,
}

#[derive(Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct RlpImportConfig {
    #[serde(default)]
    enabled: bool,
    #[serde(default)]
    base_url: String,
    #[serde(default)]
    filename: String,
    #[serde(default)]
    multi_part: bool,
    #[serde(default)]
    parts: Vec<String>,
    #[serde(default = "default_min_height")]
    min_height: u64,
    #[serde(default = "default_timeout")]
    timeout: u64,
    #[serde(default)]
    c_chain_id: Option<String>,
}
fn default_min_height() -> u64 { 1 }
fn default_timeout() -> u64 { 7200 }

#[derive(Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct ApiConfig {
    #[serde(default = "default_true")]
    admin_enabled: bool,
    #[serde(default = "default_true")]
    index_enabled: bool,
    #[serde(default = "default_true")]
    metrics_enabled: bool,
    #[serde(default = "default_http_allowed")]
    http_allowed_hosts: String,
}
fn default_true() -> bool { true }
fn default_http_allowed() -> String { "*".into() }

pub struct LuxDriver;

impl LuxDriver {
    fn parse_config(cluster: &Cluster) -> LuxConfig {
        serde_json::from_value(cluster.spec.chain_config.clone()).unwrap_or_default()
    }

    /// Resolve ports: user overrides > chain_config > defaults.
    fn ports(cluster: &Cluster) -> (i32, i32) {
        let cfg = Self::parse_config(cluster);
        let ports = &cluster.spec.ports;
        let http = ports.iter().find(|p| p.name == "http").map(|p| p.port).unwrap_or(cfg.http_port);
        let staking = ports.iter().find(|p| p.name == "staking").map(|p| p.port).unwrap_or(cfg.staking_port);
        (http, staking)
    }
}

#[async_trait]
impl ChainDriver for LuxDriver {
    fn name(&self) -> &str { "lux" }
    fn container_name(&self) -> &str { "luxd" }

    fn default_ports(&self) -> Vec<PortMapping> {
        vec![
            PortMapping { name: "http".into(), port: 9650, protocol: None },
            PortMapping { name: "staking".into(), port: 9651, protocol: None },
            PortMapping { name: "metrics".into(), port: 9090, protocol: None },
        ]
    }

    fn default_health(&self) -> HealthSpec {
        HealthSpec {
            path: "/ext/health".into(),
            method: "GET".into(),
            port_name: "http".into(),
            ..Default::default()
        }
    }

    fn startup_script(&self, cluster: &Cluster) -> Result<String> {
        let cfg = Self::parse_config(cluster);
        let spec = &cluster.spec;
        let name = cluster.name_any();
        let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
        let (http_port, staking_port) = Self::ports(cluster);
        let replicas = spec.replicas;

        let mut s = String::with_capacity(8192);

        s.push_str("#!/bin/sh\nset -e\n\n");
        s.push_str("POD_INDEX=${HOSTNAME##*-}\n");
        s.push_str(&format!(
            "echo \"=== luxd startup for $HOSTNAME ({}, network-id={}) ===\"\n\n",
            name, cfg.network_id
        ));

        // Bootstrap node list (K8s DNS)
        if spec.bootstrap.use_hostnames {
            s.push_str("# Build bootstrap node list excluding self\n");
            s.push_str(&format!("DNS_PREFIX=\"{}\"\n", name));
            s.push_str(&format!(
                "DNS_SUFFIX=\"{}-headless.{}.svc.cluster.local\"\n",
                name, namespace
            ));
            s.push_str("BOOTSTRAP_NODES=\"\"\n");
            for i in 0..replicas {
                s.push_str(&format!("if [ \"$POD_INDEX\" != \"{}\" ]; then\n", i));
                s.push_str(&format!(
                    "  CUR_HOST=\"${{DNS_PREFIX}}-{}.${{DNS_SUFFIX}}:{}\"\n",
                    i, staking_port
                ));
                s.push_str("  if [ -n \"$BOOTSTRAP_NODES\" ]; then\n");
                s.push_str("    BOOTSTRAP_NODES=\"${BOOTSTRAP_NODES},${CUR_HOST}\"\n");
                s.push_str("  else\n");
                s.push_str("    BOOTSTRAP_NODES=\"${CUR_HOST}\"\n");
                s.push_str("  fi\n");
                s.push_str("fi\n");
            }
        } else if !spec.bootstrap.external_ips.is_empty() {
            s.push_str("# Build bootstrap node list from static IPs\n");
            s.push_str("BOOTSTRAP_NODES=\"\"\n");
            for (i, ip) in spec.bootstrap.external_ips.iter().enumerate() {
                s.push_str(&format!("if [ \"$POD_INDEX\" != \"{}\" ] && [ -n \"{}\" ]; then\n", i, ip));
                s.push_str(&format!("  CUR_HOST=\"{}:{}\"\n", ip, staking_port));
                s.push_str("  if [ -n \"$BOOTSTRAP_NODES\" ]; then\n");
                s.push_str("    BOOTSTRAP_NODES=\"${BOOTSTRAP_NODES},${CUR_HOST}\"\n");
                s.push_str("  else\n");
                s.push_str("    BOOTSTRAP_NODES=\"${CUR_HOST}\"\n");
                s.push_str("  fi\n");
                s.push_str("fi\n");
            }
        }

        // Public IP discovery
        s.push_str("\n# Discover public IP\nPUBLIC_IP=\"\"\n");
        if !spec.bootstrap.external_ips.is_empty() {
            s.push_str("case \"$POD_INDEX\" in\n");
            for (i, ip) in spec.bootstrap.external_ips.iter().enumerate() {
                s.push_str(&format!("  {}) PUBLIC_IP=\"{}\" ;;\n", i, ip));
            }
            s.push_str("esac\n");
        }

        // LB discovery via K8s API
        s.push_str("\n# Discover from per-pod LoadBalancer service\n");
        s.push_str("if [ -z \"$PUBLIC_IP\" ]; then\n");
        s.push_str("  SA_TOKEN_FILE=\"/var/run/secrets/kubernetes.io/serviceaccount/token\"\n");
        s.push_str("  CA_CERT=\"/var/run/secrets/kubernetes.io/serviceaccount/ca.crt\"\n");
        s.push_str("  K8S_API=\"https://kubernetes.default.svc\"\n");
        s.push_str(&format!("  SVC_NAME=\"{}-${{POD_INDEX}}\"\n", name));
        s.push_str(&format!("  NAMESPACE=\"{}\"\n\n", namespace));
        s.push_str("  if [ -f \"$SA_TOKEN_FILE\" ]; then\n");
        s.push_str("    TOKEN=$(cat \"$SA_TOKEN_FILE\")\n");
        s.push_str("    ATTEMPT=0; MAX_ATTEMPTS=12\n");
        s.push_str("    while [ \"$ATTEMPT\" -lt \"$MAX_ATTEMPTS\" ]; do\n");
        s.push_str("      SVC_JSON=$(curl -sf -m 5 -H \"Authorization: Bearer ${TOKEN}\" --cacert \"$CA_CERT\" \"${K8S_API}/api/v1/namespaces/${NAMESPACE}/services/${SVC_NAME}\" 2>/dev/null || true)\n");
        s.push_str("      if [ -n \"$SVC_JSON\" ]; then\n");
        s.push_str("        LB_IP=$(echo \"$SVC_JSON\" | tr -d ' \\n' | sed -n 's/.*\"loadBalancer\":{\"ingress\":\\[{\"ip\":\"\\([^\"]*\\)\".*/\\1/p')\n");
        s.push_str("        if [ -n \"$LB_IP\" ]; then PUBLIC_IP=\"$LB_IP\"; break; fi\n");
        s.push_str("      fi\n");
        s.push_str("      ATTEMPT=$((ATTEMPT + 1)); sleep 5\n");
        s.push_str("    done\n");
        s.push_str("  fi\n");
        s.push_str("fi\n");
        s.push_str("if [ -z \"$PUBLIC_IP\" ]; then PUBLIC_IP=$(hostname -i); fi\n\n");

        // EVM chain configs
        let all_chain_ids: Vec<&str> = cfg.chains.iter().map(|c| c.blockchain_id.as_str()).collect();
        if cfg.evm_config.is_some() || !all_chain_ids.is_empty() {
            let evm_cfg = cfg.evm_config.as_ref().map_or_else(
                || r#"{"admin-api-enabled":true,"eth-apis":["eth","eth-filter","net","web3","internal-eth","internal-blockchain","internal-transaction","internal-tx-pool","internal-account","internal-personal","debug","internal-debug","admin"],"rpc-gas-cap":50000000,"rpc-tx-fee-cap":100,"pruning-enabled":false,"allow-unfinalized-queries":true,"allow-unprotected-txs":true,"log-level":"info","state-sync-enabled":false,"allow-missing-tries":true}"#.to_string(),
                |v| serde_json::to_string(v).unwrap_or_default(),
            );
            s.push_str("# EVM chain configs\n");
            s.push_str(&format!("CHAIN_CFG='{}'\n", evm_cfg));
            let mut chains = vec!["C".to_string()];
            chains.extend(all_chain_ids.iter().map(|s| s.to_string()));
            s.push_str(&format!("for chain in {}; do\n", chains.join(" ")));
            s.push_str("  mkdir -p /data/configs/chains/$chain\n");
            s.push_str("  echo \"$CHAIN_CFG\" > /data/configs/chains/$chain/config.json\n");
            s.push_str("done\n\n");
        }

        // Build luxd arguments
        s.push_str("# Build luxd arguments\n");
        s.push_str(&format!("ARGS=\"--network-id={}\"\n", cfg.network_id));
        s.push_str("ARGS=\"$ARGS --http-host=0.0.0.0\"\n");
        s.push_str(&format!("ARGS=\"$ARGS --http-port={}\"\n", http_port));

        let api = cfg.api.unwrap_or_default();
        s.push_str(&format!("ARGS=\"$ARGS --http-allowed-hosts={}\"\n", api.http_allowed_hosts));
        s.push_str(&format!("ARGS=\"$ARGS --staking-port={}\"\n", staking_port));
        s.push_str("ARGS=\"$ARGS --data-dir=/data\"\n");

        if spec.genesis.is_some() || spec.genesis_config_map.is_some() {
            s.push_str("ARGS=\"$ARGS --genesis-file=/genesis/genesis.json\"\n");
        }

        s.push_str(&format!("ARGS=\"$ARGS --db-type={}\"\n", cfg.db_type));

        if cfg.evm_config.is_some() || !cfg.chains.is_empty() {
            s.push_str("ARGS=\"$ARGS --chain-config-dir=/data/configs/chains\"\n");
        }

        s.push_str(&format!("ARGS=\"$ARGS --index-enabled={}\"\n", api.index_enabled));
        s.push_str(&format!("ARGS=\"$ARGS --api-admin-enabled={}\"\n", api.admin_enabled));
        s.push_str(&format!("ARGS=\"$ARGS --api-metrics-enabled={}\"\n", api.metrics_enabled));
        s.push_str("ARGS=\"$ARGS --api-keystore-enabled=true\"\n");
        s.push_str("ARGS=\"$ARGS --log-level=info\"\n");
        s.push_str("ARGS=\"$ARGS --plugin-dir=/data/plugins\"\n");
        s.push_str("ARGS=\"$ARGS --staking-tls-cert-file=/data/staking/staker.crt\"\n");
        s.push_str("ARGS=\"$ARGS --staking-tls-key-file=/data/staking/staker.key\"\n\n");

        s.push_str("if [ -f \"/data/staking/signer.key\" ]; then\n");
        s.push_str("  ARGS=\"$ARGS --staking-signer-key-file=/data/staking/signer.key\"\n");
        s.push_str("fi\n\n");

        let compression = cfg.network_compression_type.as_deref().unwrap_or("gzip");
        s.push_str(&format!("ARGS=\"$ARGS --network-compression-type={}\"\n", compression));

        let consensus = cfg.consensus.unwrap_or_default();
        s.push_str(&format!("ARGS=\"$ARGS --consensus-sample-size={}\"\n", consensus.sample_size));
        s.push_str(&format!("ARGS=\"$ARGS --consensus-quorum-size={}\"\n", consensus.quorum_size));

        let sybil = cfg.sybil_protection_enabled.unwrap_or(cfg.network_id <= 2);
        s.push_str(&format!("ARGS=\"$ARGS --sybil-protection-enabled={}\"\n", sybil));
        let req_val = cfg.require_validator_to_connect.unwrap_or(false);
        s.push_str(&format!("ARGS=\"$ARGS --network-require-validator-to-connect={}\"\n", req_val));
        let priv_ips = cfg.allow_private_ips.unwrap_or(true);
        s.push_str(&format!("ARGS=\"$ARGS --network-allow-private-ips={}\"\n\n", priv_ips));

        // Chain aliases
        if let Some(aliases) = &cfg.chain_aliases {
            let json = serde_json::to_string(aliases).unwrap_or_default();
            s.push_str(&format!("ALIASES_JSON='{}'\n", json.replace('\'', "'\"'\"'")));
            s.push_str("ALIASES_B64=$(echo \"$ALIASES_JSON\" | base64 | tr -d '\\n')\n");
            s.push_str("ARGS=\"$ARGS --chain-aliases-file-content=$ALIASES_B64\"\n\n");
        }

        if let Some(import_path) = &cfg.import_chain_data {
            s.push_str(&format!("ARGS=\"$ARGS --import-chain-data={}\"\n", import_path));
        }

        // Public IP and bootstrap
        s.push_str("if [ -n \"$PUBLIC_IP\" ]; then ARGS=\"$ARGS --public-ip=$PUBLIC_IP\"; fi\n");
        s.push_str("if [ -n \"$BOOTSTRAP_NODES\" ]; then ARGS=\"$ARGS --bootstrap-nodes=$BOOTSTRAP_NODES\"; fi\n\n");

        // Chain tracking
        if let Some(tracking) = &cfg.chain_tracking {
            if tracking.track_all_chains {
                s.push_str("ARGS=\"$ARGS --track-all-chains\"\n\n");
            } else if !tracking.tracked_chains.is_empty() {
                s.push_str(&format!("ARGS=\"$ARGS --track-chains={}\"\n\n", tracking.tracked_chains.join(",")));
            } else if !cfg.chains.is_empty() {
                let ids: Vec<String> = cfg.chains.iter()
                    .map(|cr| cr.tracking_id.clone().unwrap_or_else(|| cr.blockchain_id.clone()))
                    .collect();
                s.push_str(&format!("ARGS=\"$ARGS --track-chains={}\"\n\n", ids.join(",")));
            }
        }

        // Upgrade config
        if let Some(upgrade) = &cfg.upgrade_config {
            let json_str = serde_json::to_string(upgrade).unwrap_or_default();
            s.push_str(&format!("UPGRADE_JSON='{}'\n", json_str.replace('\'', "'\"'\"'")));
            s.push_str("UPGRADE_B64=$(echo \"$UPGRADE_JSON\" | base64 | tr -d '\\n')\n");
            s.push_str("ARGS=\"$ARGS --upgrade-file-content=$UPGRADE_B64\"\n\n");
        }

        // RLP import: clear C-chain data
        if let Some(rlp) = &cfg.rlp_import {
            if rlp.enabled {
                if let Some(c_chain_id) = &rlp.c_chain_id {
                    s.push_str(&format!(
                        "C_CHAIN_DIR=\"/data/chainData/network-{}/{}\"\n", cfg.network_id, c_chain_id
                    ));
                    s.push_str(&format!("IMPORT_MARKER=\"/data/.bootstrap-{}-import.done\"\n", name));
                    s.push_str("if [ -d \"$C_CHAIN_DIR\" ]; then\n");
                    s.push_str("  rm -rf \"$C_CHAIN_DIR\"; rm -f \"$IMPORT_MARKER\"\n");
                    s.push_str("fi\n\n");
                }
            }
        }

        // Start luxd in background
        s.push_str("/luxd/build/luxd $ARGS &\nLUXD_PID=$!\n\nset +e\n\n");

        // Wait for health
        s.push_str("echo \"[BOOTSTRAP] Waiting for node health...\"\ni=0\n");
        s.push_str(&format!(
            "while [ \"$i\" -lt 180 ]; do\n  if curl -sf -m 2 http://127.0.0.1:{}/ext/health >/dev/null 2>&1; then\n    echo \"[BOOTSTRAP] Node healthy after ${{i}}s\"; break\n  fi\n  i=$((i + 1)); sleep 1\ndone\n\n",
            http_port
        ));

        // Chain aliases (runtime)
        if let Some(tracking) = &cfg.chain_tracking {
            for alias in &tracking.aliases {
                s.push_str(&format!(
                    "curl -s -m 5 -X POST -H 'Content-Type: application/json' --data '{{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"admin.aliasChain\",\"params\":{{\"chain\":\"C\",\"alias\":\"{}\"}}}}' http://127.0.0.1:{}/ext/admin >/dev/null 2>&1 || true\n",
                    alias, http_port
                ));
            }
        }
        for chain_ref in &cfg.chains {
            s.push_str(&format!(
                "curl -s -m 5 -X POST -H 'Content-Type: application/json' --data '{{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"admin.aliasChain\",\"params\":{{\"chain\":\"{}\",\"alias\":\"{}\"}}}}' http://127.0.0.1:{}/ext/admin >/dev/null 2>&1 || true\n",
                chain_ref.blockchain_id, chain_ref.alias, http_port
            ));
        }

        // RLP import
        if let Some(rlp) = &cfg.rlp_import {
            if rlp.enabled {
                let marker_name = format!("bootstrap-{}-import", name);
                let seed_marker = &spec.seed_restore.marker_path;
                s.push_str("\n# C-Chain RLP import\n");
                s.push_str(&format!("MARKER=\"/data/.{}.done\"\n", marker_name));
                s.push_str(&format!("SEED_MARKER=\"{}\"\n", seed_marker));
                s.push_str("BOOTSTRAP_DIR=\"/data/bootstrap\"\n\n");

                s.push_str("if [ -f \"$SEED_MARKER\" ]; then\n");
                s.push_str("  echo \"[BOOTSTRAP] Seeded from snapshot, skipping RLP\"\n  touch \"$MARKER\"\n");
                s.push_str("elif [ ! -f \"$MARKER\" ]; then\n");
                s.push_str(&format!(
                    "  height_hex=$(curl -s -m 10 -X POST -H 'Content-Type: application/json' --data '{{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_blockNumber\",\"params\":[]}}' http://127.0.0.1:{}/ext/bc/C/rpc | sed -n 's/.*\"result\":\"\\(0x[0-9A-Fa-f]*\\)\".*/\\1/p' | head -n1)\n",
                    http_port
                ));
                s.push_str("  [ -z \"$height_hex\" ] && height_hex=\"0x0\"\n");
                s.push_str("  height_dec=$(printf '%d' \"$height_hex\" 2>/dev/null || echo 0)\n\n");
                s.push_str(&format!("  if [ \"$height_dec\" -lt \"{}\" ]; then\n", rlp.min_height));
                s.push_str("    mkdir -p \"$BOOTSTRAP_DIR\"\n");
                s.push_str(&format!("    RLP_FILE=\"${{BOOTSTRAP_DIR}}/{}\"\n\n", rlp.filename));

                if rlp.multi_part && !rlp.parts.is_empty() {
                    s.push_str("    if [ ! -s \"$RLP_FILE\" ]; then\n");
                    let base_name = rlp.filename.replace(".rlp", "");
                    for part in &rlp.parts {
                        s.push_str(&format!("      [ ! -s \"${{BOOTSTRAP_DIR}}/{}.part.{}\" ] && curl -fL --retry 5 -o \"${{BOOTSTRAP_DIR}}/{}.part.{}\" \"{}/{}.part.{}\" || true\n",
                            rlp.filename, part, rlp.filename, part, rlp.base_url, base_name, part));
                    }
                    s.push_str(&format!("      cat \"${{BOOTSTRAP_DIR}}\"/{}.part.* > \"$RLP_FILE\" 2>/dev/null || true\n", rlp.filename));
                    s.push_str("    fi\n");
                } else {
                    s.push_str(&format!("    [ ! -s \"$RLP_FILE\" ] && curl -fL --retry 5 -o \"$RLP_FILE\" \"{}/{}\" || true\n", rlp.base_url, rlp.filename));
                }

                s.push_str("\n    if [ -s \"$RLP_FILE\" ]; then\n");
                s.push_str(&format!(
                    "      import_result=$(curl -s -m {} -X POST -H 'Content-Type: application/json' --data \"$(printf '{{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"admin_importChain\",\"params\":[\"%s\"]}}' \"$RLP_FILE\")\" http://127.0.0.1:{}/ext/bc/C/rpc || true)\n",
                    rlp.timeout, http_port
                ));
                s.push_str("      echo \"$import_result\" | grep -q '\"success\":true' && touch \"$MARKER\" || true\n");
                s.push_str("    fi\n");
                s.push_str("  else\n    touch \"$MARKER\"\n  fi\n");
                s.push_str("else\n  echo \"[BOOTSTRAP] Import marker exists\"\nfi\n\n");
            }
        }

        s.push_str("wait \"$LUXD_PID\"\n");
        Ok(s)
    }

    fn startup_gate_script(&self, cluster: &Cluster) -> Result<String> {
        let cfg = Self::parse_config(cluster);
        let spec = &cluster.spec;
        let name = cluster.name_any();
        let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
        let (_, staking_port) = Self::ports(cluster);
        let gate = &spec.startup_gate;
        let min_peers = gate.min_peers.min(spec.replicas.saturating_sub(1));

        let mut s = String::with_capacity(2048);
        s.push_str("#!/bin/sh\nset -e\n\n");
        s.push_str("POD_INDEX=${HOSTNAME##*-}\n");
        s.push_str(&format!("echo \"[GATE] Startup gate for $HOSTNAME ({}, network-id={})\"\n", name, cfg.network_id));
        s.push_str(&format!("DNS_PREFIX=\"{}\"\n", name));
        s.push_str(&format!("DNS_SUFFIX=\"{}-headless.{}.svc.cluster.local\"\n", name, namespace));
        s.push_str(&format!("GATE_MIN_PEERS={}\nGATE_TIMEOUT={}\nGATE_INTERVAL={}\n", min_peers, gate.timeout_seconds, gate.check_interval_seconds));
        s.push_str("GATE_START=$(date +%s)\n\n");

        s.push_str("while true; do\n  REACHABLE=0\n");
        if spec.bootstrap.use_hostnames {
            for i in 0..spec.replicas {
                s.push_str(&format!("  if [ \"$POD_INDEX\" != \"{}\" ]; then\n", i));
                s.push_str(&format!(
                    "    nc -z -w 2 \"${{DNS_PREFIX}}-{}.${{DNS_SUFFIX}}\" {} 2>/dev/null && REACHABLE=$((REACHABLE + 1))\n",
                    i, staking_port
                ));
                s.push_str("  fi\n");
            }
        }

        s.push_str("\n  [ \"$REACHABLE\" -ge \"$GATE_MIN_PEERS\" ] && echo \"[GATE] $REACHABLE peers, proceeding\" && break\n\n");
        s.push_str("  ELAPSED=$(( $(date +%s) - GATE_START ))\n");
        s.push_str("  if [ \"$ELAPSED\" -ge \"$GATE_TIMEOUT\" ]; then\n");
        if gate.on_timeout == "StartAnyway" {
            s.push_str("    echo \"[GATE] Timeout, proceeding anyway\"; break\n");
        } else {
            s.push_str("    echo \"[GATE] Timeout, exiting\"; exit 1\n");
        }
        s.push_str("  fi\n");
        s.push_str("  sleep \"$GATE_INTERVAL\"\ndone\n");
        s.push_str("echo \"[GATE] Gate passed.\"\n");
        Ok(s)
    }

    fn init_script(&self, cluster: &Cluster) -> Result<Option<String>> {
        let spec = &cluster.spec;
        if spec.init.is_none() && spec.staking.is_none() {
            return Ok(None);
        }

        let mut script = String::from("set -e\nIDX=${HOSTNAME##*-}\necho \"=== Init for ${HOSTNAME} ===\"\n");

        // Clear data for re-genesis
        if spec.init.as_ref().map_or(false, |i| i.clear_data) {
            script.push_str("rm -rf /data/chainData /data/db /data/genesis.bytes /data/.bootstrap-*-import.done /data/.seeded\n");
        }

        // Seed restore
        let seed = &spec.seed_restore;
        if seed.enabled {
            let marker = &seed.marker_path;
            let check = if seed.restore_policy == "Always" { "true".into() } else { format!("! -f \"{}\"", marker) };
            script.push_str(&format!("if [ {} ]; then\n", check));
            match seed.source_type.as_str() {
                "ObjectStore" => {
                    if let Some(url) = &seed.object_store_url {
                        script.push_str(&format!("  curl -fL --retry 5 -o /tmp/snapshot.tar.zst \"{}\" && \\\n", url));
                        script.push_str("  (zstd -d /tmp/snapshot.tar.zst -o /tmp/snapshot.tar 2>/dev/null || cp /tmp/snapshot.tar.zst /tmp/snapshot.tar) && \\\n");
                        script.push_str(&format!("  tar xf /tmp/snapshot.tar -C /data && rm -f /tmp/snapshot.tar* && touch \"{}\" || true\n", marker));
                    }
                }
                "PVCClone" | "VolumeSnapshot" => {
                    script.push_str("  if [ -d \"/data/db\" ] || [ -d \"/data/chainData\" ]; then\n");
                    script.push_str(&format!("    touch \"{}\"\n  fi\n", marker));
                }
                _ => {}
            }
            script.push_str("fi\n\n");
        }

        // Plugin setup
        let c_chain_vm_id = "mgj786NP7uDwBCcq6YwThhaN8FLyybkCa4zBWTQbNgmK6k9A6";
        let chain_vm_id = "ag3GReYPNuSR17rUP8acMdZipQBikdXNRKDyFszAysmy3vDXE";

        if let Some(init) = &spec.init {
            if !init.plugins.is_empty() {
                script.push_str("mkdir -p /data/plugins\n");
                for plugin in &init.plugins {
                    script.push_str(&format!("cp {} /data/plugins/{}\n", plugin.source, plugin.dest));
                }
            } else {
                script.push_str("mkdir -p /data/plugins\n");
                script.push_str(&format!("cp /luxd/build/plugins/{} /data/plugins/\n", c_chain_vm_id));
                script.push_str(&format!("cp /luxd/build/plugins/{} /data/plugins/{}\n", c_chain_vm_id, chain_vm_id));
            }
        }

        // Staking key setup
        if spec.staking.is_some() {
            script.push_str("mkdir -p /data/staking\n");
            script.push_str("cp /staking-keys/staker-${IDX}.crt /data/staking/staker.crt\n");
            script.push_str("cp /staking-keys/staker-${IDX}.key /data/staking/staker.key\n");
            script.push_str("[ -f \"/staking-keys/signer-${IDX}.key\" ] && cp /staking-keys/signer-${IDX}.key /data/staking/signer.key\n");
            let uid = spec.security.run_as_user;
            let gid = spec.security.run_as_group;
            script.push_str(&format!("chown -R {}:{} /data/staking && chmod 600 /data/staking/*\n", uid, gid));
        }

        script.push_str("echo \"=== Init complete ===\"\n");
        Ok(Some(script))
    }

    fn env_vars(&self, cluster: &Cluster) -> Vec<(String, String)> {
        let cfg = Self::parse_config(cluster);
        vec![("LUX_NETWORK_ID".into(), cfg.network_id.to_string())]
    }

    async fn check_node_health(
        &self,
        cluster: &Cluster,
        _pod_name: &str,
        pod_ip: &str,
    ) -> Result<NodeStatus> {
        let (http_port, _) = Self::ports(cluster);
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(5))
            .build()
            .map_err(|e| OperatorError::Reconcile(format!("HTTP client: {}", e)))?;

        // Health check
        let url = format!("http://{}:{}/ext/health", pod_ip, http_port);
        let healthy = client.get(&url).send().await.map(|r| r.status().is_success()).unwrap_or(false);

        // Bootstrap check
        let bootstrapped = {
            let resp = client.post(&url)
                .json(&serde_json::json!({"jsonrpc":"2.0","id":1,"method":"health.health","params":{}}))
                .send().await;
            resp.ok().and_then(|r| if r.status().is_success() { Some(r) } else { None })
                .and_then(|r| futures::executor::block_on(r.json::<serde_json::Value>()).ok())
                .and_then(|b| b.get("result")?.get("healthy")?.as_bool())
                .unwrap_or(false)
        };

        // P-chain height
        let p_height = {
            let url = format!("http://{}:{}/ext/bc/P", pod_ip, http_port);
            client.post(&url)
                .json(&serde_json::json!({"jsonrpc":"2.0","id":1,"method":"platform.getHeight","params":{}}))
                .send().await.ok()
                .and_then(|r| if r.status().is_success() { futures::executor::block_on(r.json::<serde_json::Value>()).ok() } else { None })
                .and_then(|b| b.get("result")?.get("height")?.as_str()?.parse::<u64>().ok())
        };

        // C-chain height
        let c_height = {
            let url = format!("http://{}:{}/ext/bc/C/rpc", pod_ip, http_port);
            client.post(&url)
                .json(&serde_json::json!({"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}))
                .send().await.ok()
                .and_then(|r| if r.status().is_success() { futures::executor::block_on(r.json::<serde_json::Value>()).ok() } else { None })
                .and_then(|b| {
                    let hex = b.get("result")?.as_str()?;
                    u64::from_str_radix(hex.trim_start_matches("0x"), 16).ok()
                })
        };

        // Node ID + peers
        let (node_id, connected, inbound, outbound) = {
            let info_url = format!("http://{}:{}/ext/info", pod_ip, http_port);
            let nid = client.post(&info_url)
                .json(&serde_json::json!({"jsonrpc":"2.0","id":1,"method":"info.getNodeID","params":{}}))
                .send().await.ok()
                .and_then(|r| if r.status().is_success() { futures::executor::block_on(r.json::<serde_json::Value>()).ok() } else { None })
                .and_then(|b| b.get("result")?.get("nodeID")?.as_str().map(|s| s.to_string()));

            let peers_resp = client.post(&info_url)
                .json(&serde_json::json!({"jsonrpc":"2.0","id":1,"method":"info.peers","params":{}}))
                .send().await.ok()
                .and_then(|r| if r.status().is_success() { futures::executor::block_on(r.json::<serde_json::Value>()).ok() } else { None });

            let (total, ib, ob) = peers_resp.and_then(|b| {
                let peers = b.get("result")?.get("peers")?.as_array()?;
                let total = peers.len() as u32;
                let mut ib = 0u32;
                let mut ob = 0u32;
                for p in peers {
                    match p.get("type").and_then(|t| t.as_str()).unwrap_or("") {
                        "inbound" => ib += 1,
                        _ => ob += 1,
                    }
                }
                Some((total, ib, ob))
            }).unwrap_or((0, 0, 0));

            (nid, total, ib, ob)
        };

        // Block height = max of P-chain and C-chain
        let block_height = p_height.or(c_height);

        // Extra driver-specific fields
        let mut extra = BTreeMap::new();
        if let Some(h) = p_height {
            extra.insert("pChainHeight".into(), serde_json::json!(h));
        }
        if let Some(h) = c_height {
            extra.insert("cChainHeight".into(), serde_json::json!(h));
        }

        Ok(NodeStatus {
            node_id,
            external_ip: None, // filled by controller from LB services
            block_height,
            connected_peers: connected,
            inbound_peers: inbound,
            outbound_peers: outbound,
            bootstrapped,
            healthy,
            start_time: None, // filled by controller from pod status
            extra,
        })
    }

    fn validate_config(&self, chain_config: &serde_json::Value) -> Result<()> {
        let cfg: LuxConfig = serde_json::from_value(chain_config.clone())
            .map_err(|e| OperatorError::Config(format!("Invalid Lux chain_config: {}", e)))?;
        if cfg.network_id == 0 {
            return Err(OperatorError::Config("networkId must be > 0".into()));
        }
        Ok(())
    }
}
