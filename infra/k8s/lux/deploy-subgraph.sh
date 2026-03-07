#!/usr/bin/env bash
# Deploy or redeploy a subgraph to the Lux graph-node.
#
# Usage:
#   ./deploy-subgraph.sh                          # Deploy all subgraphs
#   ./deploy-subgraph.sh amm-v3                   # Deploy AMM V3 only
#   ./deploy-subgraph.sh amm-v3 --wipe            # Wipe and redeploy AMM V3
#
# Prerequisites:
#   - graph-node running (k8s or local compose)
#   - Port-forwards active or local compose ports
#   - npx graph-cli available
#
# Environment variables:
#   GRAPH_NODE_URL   - Graph admin endpoint (default: http://localhost:18020)
#   GRAPH_IPFS_URL   - IPFS endpoint (default: http://localhost:15001)
#   EXCHANGE_DIR     - Exchange repo root (default: ~/work/lux/exchange)
set -euo pipefail

GRAPH_NODE_URL="${GRAPH_NODE_URL:-http://localhost:18020}"
GRAPH_IPFS_URL="${GRAPH_IPFS_URL:-http://localhost:15001}"
EXCHANGE_DIR="${EXCHANGE_DIR:-$HOME/work/lux/exchange}"

SUBGRAPH="${1:-all}"
WIPE="${2:-}"

deploy_subgraph() {
  local name="$1"
  local dir="$2"
  local version="$3"

  echo "=== Deploying $name (v$version) ==="

  if [ "$WIPE" = "--wipe" ]; then
    echo "Removing existing deployment..."
    curl -sf -X POST "$GRAPH_NODE_URL" \
      -H 'Content-Type: application/json' \
      -d "{\"jsonrpc\":\"2.0\",\"method\":\"subgraph_remove\",\"params\":{\"name\":\"luxfi/$name\"},\"id\":1}" \
      2>/dev/null || true
  fi

  # Create subgraph name (idempotent)
  curl -sf -X POST "$GRAPH_NODE_URL" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"subgraph_create\",\"params\":{\"name\":\"luxfi/$name\"},\"id\":1}" \
    2>/dev/null || true

  # Build and deploy
  cd "$dir"
  npx graph codegen 2>&1 | tail -2
  npx graph build 2>&1 | tail -2
  npx graph deploy "luxfi/$name" \
    --node "$GRAPH_NODE_URL" \
    --ipfs "$GRAPH_IPFS_URL" \
    --version-label "v$version" 2>&1 | tail -5

  echo "Deployed luxfi/$name v$version"
  echo ""
}

check_sync() {
  local name="$1"
  local query_url="${GRAPH_NODE_URL/18020/18000}"
  # Replace admin port with query port
  query_url="${query_url/8020/8000}"

  echo "Checking sync status for luxfi/$name..."
  curl -sf "$query_url/subgraphs/name/luxfi/$name" \
    -H 'Content-Type: application/json' \
    -d '{"query":"{ _meta { block { number } hasIndexingErrors } }"}' 2>/dev/null \
    | python3 -m json.tool 2>/dev/null || echo "(not yet syncing)"
}

case "$SUBGRAPH" in
  amm-v3)
    deploy_subgraph "amm-v3" "$EXCHANGE_DIR/subgraphs/dex-v3" "1.8.0"
    check_sync "amm-v3"
    ;;
  amm-v2)
    if [ -d "$EXCHANGE_DIR/subgraphs/dex-factory" ]; then
      deploy_subgraph "amm-v2" "$EXCHANGE_DIR/subgraphs/dex-factory" "1.0.0"
      check_sync "amm-v2"
    else
      echo "AMM V2 subgraph not found at $EXCHANGE_DIR/subgraphs/dex-factory"
    fi
    ;;
  status)
    check_sync "amm-v3"
    check_sync "amm-v2"
    ;;
  all)
    deploy_subgraph "amm-v3" "$EXCHANGE_DIR/subgraphs/dex-v3" "1.8.0"
    if [ -d "$EXCHANGE_DIR/subgraphs/dex-factory" ]; then
      deploy_subgraph "amm-v2" "$EXCHANGE_DIR/subgraphs/dex-factory" "1.0.0"
    fi
    echo "=== Sync Status ==="
    check_sync "amm-v3"
    ;;
  *)
    echo "Usage: $0 {amm-v3|amm-v2|all|status} [--wipe]"
    exit 1
    ;;
esac
