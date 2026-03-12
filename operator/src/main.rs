//! Bootnode Operator — generic blockchain node operator for Kubernetes.
//!
//! Manages Cluster and ChainDeployment custom resources for any chain.
//! Chain-specific behavior is pluggable via drivers (see `drivers/`).

mod api;
mod controller;
mod crd;
mod drivers;
mod error;
mod resources;

use clap::Parser;
use kube::Client;
use std::net::SocketAddr;
use std::sync::Arc;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

#[derive(Parser, Debug)]
#[command(name = "bootnode-operator")]
#[command(about = "Generic blockchain node operator for Kubernetes")]
struct Args {
    /// Log level
    #[arg(long, default_value = "info")]
    log_level: String,

    /// Namespace to watch (empty for all namespaces)
    #[arg(long, default_value = "")]
    namespace: String,

    /// Metrics port
    #[arg(long, default_value = "8080")]
    metrics_port: u16,

    /// REST API / health port
    #[arg(long, default_value = "8081")]
    api_port: u16,
}

async fn metrics() -> &'static str {
    // TODO: prometheus metrics
    ""
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();

    let level = match args.log_level.to_lowercase().as_str() {
        "trace" => Level::TRACE,
        "debug" => Level::DEBUG,
        "info" => Level::INFO,
        "warn" => Level::WARN,
        "error" => Level::ERROR,
        _ => Level::INFO,
    };

    let subscriber = FmtSubscriber::builder()
        .with_max_level(level)
        .with_target(true)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    info!("Starting Bootnode Operator");
    info!("Namespace: {}", if args.namespace.is_empty() { "all" } else { &args.namespace });

    let client = Client::try_default().await?;
    info!("Connected to Kubernetes cluster");

    // REST API server (includes /healthz, /readyz)
    let api_state = Arc::new(api::ApiState { client: client.clone() });
    let api_app = api::router(api_state);
    let api_addr = SocketAddr::from(([0, 0, 0, 0], args.api_port));
    info!("API server listening on {}", api_addr);

    // Metrics server
    let metrics_app = axum::Router::new().route("/metrics", axum::routing::get(metrics));
    let metrics_addr = SocketAddr::from(([0, 0, 0, 0], args.metrics_port));
    info!("Metrics server listening on {}", metrics_addr);

    // Run all concurrently
    let cluster_client = client.clone();
    let chain_client = client.clone();
    let cluster_ns = args.namespace.clone();
    let chain_ns = args.namespace.clone();

    tokio::select! {
        res = controller::run_cluster_controller(cluster_client, cluster_ns) => {
            if let Err(e) = res { tracing::error!("Cluster controller exited: {:?}", e); }
        }
        res = controller::run_chain_controller(chain_client, chain_ns) => {
            if let Err(e) = res { tracing::error!("Chain controller exited: {:?}", e); }
        }
        res = axum::serve(
            tokio::net::TcpListener::bind(api_addr).await.unwrap(),
            api_app.into_make_service(),
        ) => {
            if let Err(e) = res { tracing::error!("API server exited: {:?}", e); }
        }
        res = axum::serve(
            tokio::net::TcpListener::bind(metrics_addr).await.unwrap(),
            metrics_app.into_make_service(),
        ) => {
            if let Err(e) = res { tracing::error!("Metrics server exited: {:?}", e); }
        }
    }

    Ok(())
}
