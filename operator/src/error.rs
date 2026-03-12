//! Error types for the operator.

use thiserror::Error;

#[derive(Error, Debug)]
pub enum OperatorError {
    #[error("Kubernetes API error: {0}")]
    KubeApi(#[from] kube::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Configuration error: {0}")]
    Config(String),

    #[error("Resource not found: {0}")]
    #[allow(dead_code)]
    NotFound(String),

    #[error("Reconciliation error: {0}")]
    Reconcile(String),

    #[error("Unknown chain driver: {0}")]
    UnknownChain(String),
}

pub type Result<T> = std::result::Result<T, OperatorError>;
