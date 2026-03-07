#!/usr/bin/env bash
# Deploy bootnode-operator to lux-k8s cluster.
#
# Prerequisites:
#   - kubectl configured for lux-k8s cluster
#   - CRD YAMLs and RBAC applied
#
# Usage:
#   ./deploy.sh                    # Apply all manifests
#   ./deploy.sh crds               # Apply CRDs only
#   ./deploy.sh operator           # Apply operator only
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

apply_crds() {
    echo "=== Applying CRDs ==="
    kubectl apply -f "$SCRIPT_DIR/crds.yaml"
    echo "Waiting for CRDs to be established..."
    kubectl wait --for=condition=Established crd/clusters.bootnode.dev --timeout=30s
    kubectl wait --for=condition=Established crd/chaindeployments.bootnode.dev --timeout=30s
}

apply_rbac() {
    echo "=== Applying RBAC ==="
    kubectl apply -f "$SCRIPT_DIR/rbac.yaml"
}

apply_operator() {
    echo "=== Deploying operator ==="
    kubectl apply -f "$SCRIPT_DIR/operator-deployment.yaml"
    echo "Waiting for operator to be ready..."
    kubectl rollout status deployment/bootnode-operator -n bootnode-system --timeout=120s
}

apply_graph() {
    local ns="${GRAPH_NAMESPACE:-lux-explorer}"
    echo "=== Deploying Graph Node infrastructure to $ns ==="
    kubectl apply -f "$SCRIPT_DIR/graph-node.yaml" -n "$ns"
    echo "Waiting for graph-postgres..."
    kubectl rollout status statefulset/graph-postgres -n "$ns" --timeout=120s
    echo "Waiting for graph-ipfs..."
    kubectl rollout status deployment/graph-ipfs -n "$ns" --timeout=120s
    echo "Waiting for graph-node..."
    kubectl rollout status statefulset/graph-node -n "$ns" --timeout=120s
    echo "Graph Node ready. Deploy subgraphs with: ./deploy-subgraph.sh"
}

case "${1:-all}" in
    crds)
        apply_crds
        ;;
    rbac)
        apply_rbac
        ;;
    operator)
        apply_operator
        ;;
    graph)
        apply_graph
        ;;
    all)
        apply_crds
        apply_rbac
        apply_operator
        echo "=== Done ==="
        kubectl get pods -n bootnode-system
        ;;
    *)
        echo "Usage: $0 {crds|rbac|operator|graph|all}"
        exit 1
        ;;
esac
