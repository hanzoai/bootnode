//! Generic reconciliation controller for Cluster and ChainDeployment CRDs.
//!
//! All chain-specific logic is delegated to [`ChainDriver`] implementations.
//! This module handles the state machine, K8s API interactions, health checks,
//! and recovery — identically for every blockchain.

use crate::crd::{
    ChainDeployment, ChainDeploymentStatus, Cluster, ClusterStatus,
    DegradedCondition, DegradedReason, NetworkMetrics, NodeStatus,
};
use crate::drivers::DriverRegistry;
use crate::error::{OperatorError, Result};
use crate::resources;
use futures::StreamExt;
use k8s_openapi::api::apps::v1::StatefulSet;
use k8s_openapi::api::core::v1::{ConfigMap, Pod, Service};
use k8s_openapi::api::policy::v1::PodDisruptionBudget;
use k8s_openapi::api::rbac::v1::{Role, RoleBinding};
use kube::{
    api::{Api, DeleteParams, ListParams, Patch, PatchParams},
    runtime::{
        controller::{Action, Controller},
        watcher::Config as WatcherConfig,
    },
    Client, ResourceExt,
};
use std::collections::BTreeMap;
use std::sync::Arc;
use std::time::Duration;
use tracing::{error, info, warn};

/// Shared context for controllers.
pub struct Context {
    pub client: Client,
    pub drivers: DriverRegistry,
}

// ─── Controller Runners ───

pub async fn run_cluster_controller(client: Client, namespace: String) -> Result<()> {
    let ctx = Arc::new(Context {
        client: client.clone(),
        drivers: DriverRegistry::new(),
    });

    let clusters: Api<Cluster> = if namespace.is_empty() {
        Api::all(client.clone())
    } else {
        Api::namespaced(client.clone(), &namespace)
    };

    info!("Starting Cluster controller");

    Controller::new(clusters, WatcherConfig::default())
        .run(reconcile_cluster, cluster_error_policy, ctx)
        .for_each(|res| async move {
            match res {
                Ok(o) => info!("Reconciled cluster: {:?}", o),
                Err(e) => error!("Cluster reconcile error: {:?}", e),
            }
        })
        .await;

    Ok(())
}

pub async fn run_chain_controller(client: Client, namespace: String) -> Result<()> {
    let ctx = Arc::new(Context {
        client: client.clone(),
        drivers: DriverRegistry::new(),
    });

    let chains: Api<ChainDeployment> = if namespace.is_empty() {
        Api::all(client.clone())
    } else {
        Api::namespaced(client.clone(), &namespace)
    };

    info!("Starting ChainDeployment controller");

    Controller::new(chains, WatcherConfig::default())
        .run(reconcile_chain, chain_error_policy, ctx)
        .for_each(|res| async move {
            match res {
                Ok(o) => info!("Reconciled chain: {:?}", o),
                Err(e) => error!("Chain reconcile error: {:?}", e),
            }
        })
        .await;

    Ok(())
}

// ─── Cluster Reconciliation ───

async fn reconcile_cluster(cluster: Arc<Cluster>, ctx: Arc<Context>) -> Result<Action> {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());

    info!("Reconciling Cluster {}/{}", namespace, name);

    let driver = ctx.drivers.get(&cluster.spec.chain).ok_or_else(|| {
        OperatorError::UnknownChain(format!(
            "No driver for chain '{}'. Available: {:?}",
            cluster.spec.chain,
            ctx.drivers.chains()
        ))
    })?;

    // Validate chain_config
    info!(chain = driver.name(), "reconciling cluster");
    driver.validate_config(&cluster.spec.chain_config)?;

    let clusters_api: Api<Cluster> = Api::namespaced(ctx.client.clone(), &namespace);
    let current_status = cluster.status.clone().unwrap_or_default();
    let phase = current_status.phase.as_str();

    let new_status = match phase {
        "" | "Pending" => {
            if cluster.spec.adopt_existing {
                adopt_existing(&cluster, &ctx, &*driver).await?
            } else {
                create_cluster(&cluster, &ctx, &*driver).await?
            }
        }
        "Creating" => check_creation_progress(&cluster, &ctx).await?,
        "Bootstrapping" => check_bootstrap_progress(&cluster, &ctx, &*driver).await?,
        "Running" => {
            if !check_scale_safety(&cluster, &ctx).await? {
                warn!("Cluster {} scale-down blocked", name);
                let mut s = current_status.clone();
                s.degraded_reasons.push(DegradedCondition {
                    reason: DegradedReason::NodeUnhealthy,
                    message: "Scale-down blocked: set allowScaleDown=true".into(),
                    affected_nodes: vec![],
                });
                s
            } else {
                // Sync replicas if changed
                let sts_api: Api<StatefulSet> = Api::namespaced(ctx.client.clone(), &namespace);
                if let Ok(sts) = sts_api.get(&name).await {
                    let current = sts.spec.as_ref().and_then(|s| s.replicas).unwrap_or(0) as u32;
                    if current != cluster.spec.replicas {
                        info!("Cluster {} scaling: {} -> {}", name, current, cluster.spec.replicas);
                        let patch = Patch::Merge(serde_json::json!({"spec":{"replicas":cluster.spec.replicas}}));
                        sts_api.patch(&name, &PatchParams::default(), &patch).await.map_err(OperatorError::KubeApi)?;
                        if cluster.spec.replicas > current && cluster.spec.service.per_node_lb {
                            create_per_pod_services(&cluster, &ctx, &*driver).await?;
                        }
                    }
                }
                check_health(&cluster, &ctx, &*driver).await?
            }
        }
        "Degraded" => attempt_recovery(&cluster, &ctx, &*driver).await?,
        _ => current_status.clone(),
    };

    // Update status if changed
    if new_status.phase != current_status.phase
        || new_status.ready_nodes != current_status.ready_nodes
        || new_status.chain_statuses != current_status.chain_statuses
        || new_status.external_ips != current_status.external_ips
    {
        let patch = Patch::Merge(serde_json::json!({"status": new_status}));
        clusters_api
            .patch_status(&name, &PatchParams::default(), &patch)
            .await
            .map_err(OperatorError::KubeApi)?;
    }

    let interval = cluster.spec.health.check_interval_seconds;
    let requeue = match new_status.phase.as_str() {
        "Running" => Duration::from_secs(interval),
        "Creating" | "Bootstrapping" => Duration::from_secs(10),
        "Degraded" => Duration::from_secs(interval / 2),
        _ => Duration::from_secs(15),
    };

    Ok(Action::requeue(requeue))
}

// ─── Create Cluster ───

async fn create_cluster(
    cluster: &Cluster,
    ctx: &Context,
    driver: &dyn crate::drivers::ChainDriver,
) -> Result<ClusterStatus> {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());

    info!("Creating cluster {} with {} nodes", name, cluster.spec.replicas);

    // ConfigMap
    let cm = resources::build_config_map(cluster);
    apply(&Api::<ConfigMap>::namespaced(ctx.client.clone(), &namespace), &format!("{}-config", name), &cm).await?;

    // Startup script (driver-generated unless user provides their own)
    if cluster.spec.startup_script.is_none() {
        let script = driver.startup_script(cluster)?;
        let startup_cm = resources::build_startup_configmap(cluster, script);
        apply(&Api::<ConfigMap>::namespaced(ctx.client.clone(), &namespace), &format!("{}-startup", name), &startup_cm).await?;
    }

    // Services
    let headless = resources::build_headless_service(cluster, driver);
    apply(&Api::<Service>::namespaced(ctx.client.clone(), &namespace), &format!("{}-headless", name), &headless).await?;

    let rpc_svc = resources::build_rpc_service(cluster, driver);
    apply(&Api::<Service>::namespaced(ctx.client.clone(), &namespace), &name, &rpc_svc).await?;

    if cluster.spec.service.per_node_lb {
        create_per_pod_services(cluster, ctx, driver).await?;
    }

    // RBAC
    let role = resources::build_role(cluster);
    apply(&Api::<Role>::namespaced(ctx.client.clone(), &namespace), &format!("{}-service-reader", name), &role).await?;
    let binding = resources::build_role_binding(cluster);
    apply(&Api::<RoleBinding>::namespaced(ctx.client.clone(), &namespace), &format!("{}-service-reader", name), &binding).await?;

    // PDB
    let pdb = resources::build_pdb(cluster);
    apply(&Api::<PodDisruptionBudget>::namespaced(ctx.client.clone(), &namespace), &format!("{}-pdb", name), &pdb).await?;

    // StatefulSet
    let sts = resources::build_statefulset(cluster, driver)?;
    apply(&Api::<StatefulSet>::namespaced(ctx.client.clone(), &namespace), &name, &sts).await?;

    Ok(ClusterStatus {
        phase: "Creating".into(),
        ready_nodes: 0,
        total_nodes: cluster.spec.replicas,
        ..Default::default()
    })
}

async fn create_per_pod_services(
    cluster: &Cluster,
    ctx: &Context,
    driver: &dyn crate::drivers::ChainDriver,
) -> Result<()> {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let svc_api: Api<Service> = Api::namespaced(ctx.client.clone(), &namespace);

    for i in 0..cluster.spec.replicas {
        let svc = resources::build_per_pod_service(cluster, driver, i);
        apply(&svc_api, &format!("{}-{}", name, i), &svc).await?;
    }
    Ok(())
}

// ─── Adopt Existing ───

async fn adopt_existing(
    cluster: &Cluster,
    ctx: &Context,
    _driver: &dyn crate::drivers::ChainDriver,
) -> Result<ClusterStatus> {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());

    let sts_api: Api<StatefulSet> = Api::namespaced(ctx.client.clone(), &namespace);
    match sts_api.get(&name).await {
        Ok(sts) => {
            let ready = sts.status.unwrap_or_default().ready_replicas.unwrap_or(0) as u32;
            let phase = if ready >= cluster.spec.replicas {
                "Running"
            } else if ready > 0 {
                "Bootstrapping"
            } else {
                "Creating"
            };
            Ok(ClusterStatus {
                phase: phase.into(),
                ready_nodes: ready,
                total_nodes: cluster.spec.replicas,
                ..Default::default()
            })
        }
        Err(kube::Error::Api(e)) if e.code == 404 => {
            warn!("adopt_existing: StatefulSet {} not found, falling back to create", name);
            create_cluster(cluster, ctx, _driver).await
        }
        Err(e) => Err(OperatorError::KubeApi(e)),
    }
}

// ─── Progress Checks ───

async fn check_creation_progress(cluster: &Cluster, ctx: &Context) -> Result<ClusterStatus> {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let status = cluster.status.clone().unwrap_or_default();

    let sts_api: Api<StatefulSet> = Api::namespaced(ctx.client.clone(), &namespace);
    let sts = match sts_api.get(&name).await {
        Ok(s) => s,
        Err(kube::Error::Api(e)) if e.code == 404 => return Ok(status),
        Err(e) => return Err(OperatorError::KubeApi(e)),
    };

    let ready = sts.status.unwrap_or_default().ready_replicas.unwrap_or(0) as u32;
    let phase = if ready >= cluster.spec.replicas { "Bootstrapping" } else { "Creating" };

    Ok(ClusterStatus {
        phase: phase.into(),
        ready_nodes: ready,
        total_nodes: cluster.spec.replicas,
        ..status
    })
}

async fn check_bootstrap_progress(
    cluster: &Cluster,
    ctx: &Context,
    driver: &dyn crate::drivers::ChainDriver,
) -> Result<ClusterStatus> {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let status = cluster.status.clone().unwrap_or_default();

    let pods = list_cluster_pods(&name, &namespace, &ctx.client, cluster.spec.adopt_existing).await?;
    let mut bootstrapped = 0u32;

    for pod in &pods {
        let pod_name = pod.metadata.name.clone().unwrap_or_default();
        let pod_ip = pod.status.as_ref().and_then(|s| s.pod_ip.clone()).unwrap_or_default();
        if pod_ip.is_empty() { continue; }

        match driver.check_node_health(cluster, &pod_name, &pod_ip).await {
            Ok(ns) if ns.bootstrapped => { bootstrapped += 1; }
            _ => {}
        }
    }

    let phase = if bootstrapped >= cluster.spec.replicas { "Running" } else { "Bootstrapping" };
    Ok(ClusterStatus {
        phase: phase.into(),
        ready_nodes: bootstrapped,
        total_nodes: cluster.spec.replicas,
        ..status
    })
}

// ─── Health Checks ───

async fn check_health(
    cluster: &Cluster,
    ctx: &Context,
    driver: &dyn crate::drivers::ChainDriver,
) -> Result<ClusterStatus> {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let status = cluster.status.clone().unwrap_or_default();

    let pods = list_cluster_pods(&name, &namespace, &ctx.client, cluster.spec.adopt_existing).await?;
    let mut healthy_count = 0u32;
    let mut node_statuses = BTreeMap::new();
    let mut degraded_reasons: Vec<DegradedCondition> = Vec::new();
    let mut heights: Vec<u64> = Vec::new();

    for pod in &pods {
        let pod_name = pod.metadata.name.clone().unwrap_or_default();
        let pod_ip = pod.status.as_ref().and_then(|s| s.pod_ip.clone()).unwrap_or_default();
        let start_time = pod.status.as_ref()
            .and_then(|s| s.start_time.as_ref())
            .map(|t| t.0.to_rfc3339());

        if pod_ip.is_empty() {
            node_statuses.insert(pod_name.clone(), NodeStatus { healthy: false, ..Default::default() });
            degraded_reasons.push(DegradedCondition {
                reason: DegradedReason::PodNotReady,
                message: format!("Pod {} has no IP", pod_name),
                affected_nodes: vec![pod_name],
            });
            continue;
        }

        let mut ns = driver.check_node_health(cluster, &pod_name, &pod_ip).await.unwrap_or_default();
        ns.start_time = start_time.clone();

        if ns.healthy { healthy_count += 1; }
        if let Some(h) = ns.block_height { heights.push(h); }

        if !ns.healthy {
            degraded_reasons.push(DegradedCondition {
                reason: DegradedReason::NodeUnhealthy,
                message: format!("Pod {} failed health check", pod_name),
                affected_nodes: vec![pod_name.clone()],
            });
        }

        node_statuses.insert(pod_name, ns);
    }

    // Height skew
    let (min_h, max_h) = if !heights.is_empty() {
        (*heights.iter().min().unwrap_or(&0), *heights.iter().max().unwrap_or(&0))
    } else { (0, 0) };
    let skew = max_h.saturating_sub(min_h);

    if skew > cluster.spec.health.max_height_skew && heights.len() > 1 {
        let lagging: Vec<String> = node_statuses.iter()
            .filter(|(_, ns)| ns.block_height.map(|h| max_h.saturating_sub(h) > cluster.spec.health.max_height_skew).unwrap_or(false))
            .map(|(name, _)| name.clone())
            .collect();
        degraded_reasons.push(DegradedCondition {
            reason: DegradedReason::HeightSkew,
            message: format!("Height skew: {} (min={}, max={})", skew, min_h, max_h),
            affected_nodes: lagging,
        });
    }

    // External IPs from LB services
    let svc_api: Api<Service> = Api::namespaced(ctx.client.clone(), &namespace);
    let external_ips = discover_external_ips(&svc_api, &name, cluster.spec.replicas).await;
    for (svc_key, ip) in &external_ips {
        if let Some(idx_str) = svc_key.rsplit('-').next() {
            if let Ok(idx) = idx_str.parse::<u32>() {
                let pod = node_statuses.keys()
                    .find(|pn| pn.rsplit('-').next().and_then(|s| s.parse::<u32>().ok()) == Some(idx))
                    .cloned();
                if let Some(pn) = pod {
                    if let Some(ns) = node_statuses.get_mut(&pn) {
                        ns.external_ip = Some(ip.clone());
                    }
                }
            }
        }
    }

    let total_peers: u32 = node_statuses.values().map(|ns| ns.connected_peers).sum();
    let threshold = (cluster.spec.replicas * 2) / 3;
    let phase = if healthy_count >= cluster.spec.replicas && degraded_reasons.is_empty() {
        "Running"
    } else if healthy_count >= threshold {
        "Degraded"
    } else {
        "Degraded"
    };

    Ok(ClusterStatus {
        phase: phase.into(),
        ready_nodes: healthy_count,
        total_nodes: cluster.spec.replicas,
        external_ips,
        node_statuses,
        degraded_reasons,
        network_metrics: Some(NetworkMetrics {
            min_height: min_h,
            max_height: max_h,
            height_skew: skew,
            bootstrapped_chains: 0,
            total_peers,
        }),
        ..status
    })
}

// ─── Recovery ───

async fn attempt_recovery(
    cluster: &Cluster,
    ctx: &Context,
    driver: &dyn crate::drivers::ChainDriver,
) -> Result<ClusterStatus> {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());
    let status = cluster.status.clone().unwrap_or_default();

    let pod_api: Api<Pod> = Api::namespaced(ctx.client.clone(), &namespace);
    let pods = list_cluster_pods(&name, &namespace, &ctx.client, cluster.spec.adopt_existing).await?;

    let mut recovered = 0u32;
    let mut healthy = 0u32;
    let max_recoveries = cluster.spec.upgrade_strategy.max_unavailable;

    for pod in &pods {
        let pod_name = pod.metadata.name.clone().unwrap_or_default();
        let pod_ip = pod.status.as_ref().and_then(|s| s.pod_ip.clone()).unwrap_or_default();

        let is_healthy = if pod_ip.is_empty() {
            false
        } else {
            driver.check_node_health(cluster, &pod_name, &pod_ip).await.map(|ns| ns.healthy).unwrap_or(false)
        };

        if is_healthy {
            healthy += 1;
        } else if recovered < max_recoveries {
            let age = pod.status.as_ref()
                .and_then(|s| s.start_time.as_ref())
                .map(|t| chrono::Utc::now().signed_duration_since(t.0).num_seconds())
                .unwrap_or(0);
            if age > 120 {
                info!("Deleting unhealthy pod {} (age {}s) for recovery", pod_name, age);
                if pod_api.delete(&pod_name, &DeleteParams::default()).await.is_ok() {
                    recovered += 1;
                }
            }
        }
    }

    let phase = if recovered > 0 {
        "Bootstrapping"
    } else if healthy >= cluster.spec.replicas {
        "Running"
    } else {
        "Degraded"
    };

    Ok(ClusterStatus {
        phase: phase.into(),
        ready_nodes: healthy,
        total_nodes: cluster.spec.replicas,
        ..status
    })
}

// ─── Scale Safety ───

async fn check_scale_safety(cluster: &Cluster, ctx: &Context) -> Result<bool> {
    let name = cluster.name_any();
    let namespace = cluster.namespace().unwrap_or_else(|| "default".into());

    let sts_api: Api<StatefulSet> = Api::namespaced(ctx.client.clone(), &namespace);
    let sts = match sts_api.get(&name).await {
        Ok(s) => s,
        Err(_) => return Ok(true),
    };

    let current = sts.spec.as_ref().and_then(|s| s.replicas).unwrap_or(0) as u32;
    if cluster.spec.replicas < current && !cluster.spec.allow_scale_down {
        warn!("Cluster {} scale-down blocked: {} -> {}", name, current, cluster.spec.replicas);
        return Ok(false);
    }
    Ok(true)
}

// ─── ChainDeployment Reconciliation ───

async fn reconcile_chain(chain: Arc<ChainDeployment>, ctx: Arc<Context>) -> Result<Action> {
    let name = chain.name_any();
    let namespace = chain.namespace().unwrap_or_else(|| "default".into());

    info!("Reconciling ChainDeployment {}/{}", namespace, name);

    let chains_api: Api<ChainDeployment> = Api::namespaced(ctx.client.clone(), &namespace);
    let current = chain.status.clone().unwrap_or_default();
    let phase = current.phase.as_str();

    let new_status = match phase {
        "" | "Pending" => {
            if chain.spec.blockchain_id.is_some() {
                ChainDeploymentStatus {
                    chain_id: chain.spec.chain_id.clone(),
                    blockchain_id: chain.spec.blockchain_id.clone(),
                    phase: "Active".into(),
                    ..Default::default()
                }
            } else {
                ChainDeploymentStatus {
                    chain_id: chain.spec.chain_id.clone(),
                    phase: "Pending".into(),
                    ..Default::default()
                }
            }
        }
        "Active" => current.clone(),
        _ => current.clone(),
    };

    if new_status.phase != current.phase || new_status.blockchain_id != current.blockchain_id {
        let patch = Patch::Merge(serde_json::json!({"status": new_status}));
        chains_api.patch_status(&name, &PatchParams::default(), &patch).await.map_err(OperatorError::KubeApi)?;
    }

    let requeue = match new_status.phase.as_str() {
        "Active" => Duration::from_secs(120),
        _ => Duration::from_secs(30),
    };
    Ok(Action::requeue(requeue))
}

// ─── Helpers ───

async fn list_cluster_pods(
    name: &str,
    namespace: &str,
    client: &Client,
    adopt: bool,
) -> Result<Vec<Pod>> {
    let pods: Api<Pod> = Api::namespaced(client.clone(), namespace);
    let label = if adopt {
        format!("app={}", name)
    } else {
        format!("app.kubernetes.io/instance={}", name)
    };
    let list = pods.list(&ListParams::default().labels(&label)).await.map_err(OperatorError::KubeApi)?;
    Ok(list.items)
}

async fn discover_external_ips(
    svc_api: &Api<Service>,
    name: &str,
    replicas: u32,
) -> BTreeMap<String, String> {
    let mut ips = BTreeMap::new();
    for i in 0..replicas {
        let svc_name = format!("{}-{}", name, i);
        if let Ok(svc) = svc_api.get(&svc_name).await {
            if let Some(ip) = svc.status
                .and_then(|s| s.load_balancer)
                .and_then(|lb| lb.ingress)
                .and_then(|ing| ing.first().cloned())
                .and_then(|i| i.ip)
            {
                ips.insert(svc_name, ip);
            }
        }
    }
    ips
}

async fn apply<T>(api: &Api<T>, name: &str, resource: &T) -> Result<()>
where
    T: kube::Resource<DynamicType = ()> + Clone + std::fmt::Debug + serde::Serialize + serde::de::DeserializeOwned,
{
    let params = PatchParams::apply("bootnode-operator").force();
    let patch = Patch::Apply(resource);
    api.patch(name, &params, &patch).await.map_err(OperatorError::KubeApi)?;
    Ok(())
}

fn cluster_error_policy(cluster: Arc<Cluster>, error: &OperatorError, _ctx: Arc<Context>) -> Action {
    error!("Error reconciling cluster {}: {:?}", cluster.name_any(), error);
    Action::requeue(Duration::from_secs(30))
}

fn chain_error_policy(chain: Arc<ChainDeployment>, error: &OperatorError, _ctx: Arc<Context>) -> Action {
    error!("Error reconciling chain {}: {:?}", chain.name_any(), error);
    Action::requeue(Duration::from_secs(30))
}
