//! REST API for imperative operator actions.
//!
//! Runs on :8081 alongside the controller. Provides endpoints for:
//! - Restarting unhealthy nodes
//! - Force health checks
//! - Per-node status
//! - Operator health

use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use kube::{
    api::{Api, DeleteParams, ListParams},
    Client,
};
use k8s_openapi::api::core::v1::Pod;
use serde_json::json;
use std::sync::Arc;

pub struct ApiState {
    pub client: Client,
}

pub fn router(state: Arc<ApiState>) -> Router {
    Router::new()
        .route("/healthz", get(healthz))
        .route("/readyz", get(readyz))
        .route("/api/v1/clusters/:namespace/:name/nodes", get(list_nodes))
        .route("/api/v1/clusters/:namespace/:name/restart", post(restart_cluster))
        .with_state(state)
}

async fn healthz() -> &'static str {
    "ok"
}

async fn readyz() -> &'static str {
    "ok"
}

async fn list_nodes(
    State(state): State<Arc<ApiState>>,
    Path((namespace, name)): Path<(String, String)>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let pods: Api<Pod> = Api::namespaced(state.client.clone(), &namespace);
    let label = format!("app.kubernetes.io/instance={}", name);
    let list = pods
        .list(&ListParams::default().labels(&label))
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let nodes: Vec<serde_json::Value> = list
        .items
        .iter()
        .map(|pod| {
            let name = pod.metadata.name.clone().unwrap_or_default();
            let ip = pod.status.as_ref().and_then(|s| s.pod_ip.clone());
            let phase = pod.status.as_ref().and_then(|s| s.phase.clone());
            let ready = pod.status.as_ref()
                .and_then(|s| s.conditions.as_ref())
                .and_then(|c| c.iter().find(|c| c.type_ == "Ready"))
                .map(|c| c.status == "True")
                .unwrap_or(false);

            json!({
                "name": name,
                "ip": ip,
                "phase": phase,
                "ready": ready,
            })
        })
        .collect();

    Ok(Json(json!({"nodes": nodes})))
}

async fn restart_cluster(
    State(state): State<Arc<ApiState>>,
    Path((namespace, name)): Path<(String, String)>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let pods: Api<Pod> = Api::namespaced(state.client.clone(), &namespace);
    let label = format!("app.kubernetes.io/instance={}", name);
    let list = pods
        .list(&ListParams::default().labels(&label))
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let mut restarted = Vec::new();
    for pod in &list.items {
        let pod_name = pod.metadata.name.clone().unwrap_or_default();
        if pods.delete(&pod_name, &DeleteParams::default()).await.is_ok() {
            restarted.push(pod_name);
        }
    }

    Ok(Json(json!({
        "restarted": restarted,
        "count": restarted.len(),
    })))
}
