#!/bin/bash
# Bootnode Cloud Deployment Script
# Usage: ./deploy.sh <provider> <environment>
# Example: ./deploy.sh aws production

set -euo pipefail

PROVIDER="${1:-docker}"
ENVIRONMENT="${2:-development}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "=== Bootnode Deployment ==="
echo "Provider: $PROVIDER"
echo "Environment: $ENVIRONMENT"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
  case $PROVIDER in
    aws)
      command -v aws >/dev/null 2>&1 || { log_error "AWS CLI required"; exit 1; }
      command -v eksctl >/dev/null 2>&1 || { log_error "eksctl required"; exit 1; }
      ;;
    gcp)
      command -v gcloud >/dev/null 2>&1 || { log_error "gcloud CLI required"; exit 1; }
      ;;
    azure)
      command -v az >/dev/null 2>&1 || { log_error "Azure CLI required"; exit 1; }
      ;;
    digitalocean)
      command -v doctl >/dev/null 2>&1 || { log_error "doctl required"; exit 1; }
      ;;
    docker)
      command -v docker >/dev/null 2>&1 || { log_error "Docker required"; exit 1; }
      ;;
  esac
  command -v kubectl >/dev/null 2>&1 || { log_error "kubectl required"; exit 1; }
}

# Build Docker images
build_images() {
  log_info "Building Docker images..."

  cd "$ROOT_DIR"

  # Build API
  docker build -t ghcr.io/hanzoai/bootnode:api-latest -f api/Dockerfile api/

  # Build Web
  docker build -t ghcr.io/hanzoai/bootnode:web-latest -f web/Dockerfile web/

  # Build Indexer (if exists)
  if [ -d "indexer" ]; then
    docker build -t ghcr.io/hanzoai/bootnode:indexer-latest -f indexer/Dockerfile indexer/
  fi

  log_info "Images built successfully"
}

# Deploy to Docker Compose (local/development)
deploy_docker() {
  log_info "Deploying with Docker Compose..."
  cd "$ROOT_DIR/infra"

  if [ "$ENVIRONMENT" = "production" ]; then
    docker compose --profile monitoring up -d
  else
    docker compose up -d
  fi

  log_info "Waiting for services to be healthy..."
  sleep 10

  docker compose ps
  log_info "Deployment complete!"
  echo ""
  echo "Services available at:"
  echo "  - API: http://localhost:8000"
  echo "  - Web: http://localhost:3001"
  echo "  - Docs: http://localhost:8000/docs"
}

# Deploy to AWS EKS
deploy_aws() {
  log_info "Deploying to AWS EKS..."

  # Create cluster if it doesn't exist
  if ! eksctl get cluster --name bootnode-cluster 2>/dev/null; then
    log_info "Creating EKS cluster..."
    eksctl create cluster -f "$SCRIPT_DIR/aws/eks-cluster.yaml"
  fi

  # Update kubeconfig
  aws eks update-kubeconfig --name bootnode-cluster

  # Push images to ECR
  log_info "Pushing images to ECR..."
  AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  AWS_REGION=${AWS_REGION:-us-east-1}
  ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

  aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

  for image in api web indexer; do
    aws ecr describe-repositories --repository-names hanzoai/bootnode 2>/dev/null || \
      aws ecr create-repository --repository-name hanzoai/bootnode
    docker tag ghcr.io/hanzoai/bootnode:$image-latest $ECR_REGISTRY/hanzoai/bootnode:$image-latest
    docker push $ECR_REGISTRY/hanzoai/bootnode:$image-latest
  done

  # Deploy to Kubernetes
  deploy_kubernetes
}

# Deploy to GCP GKE
deploy_gcp() {
  log_info "Deploying to GCP GKE..."

  PROJECT_ID=$(gcloud config get-value project)
  REGION=${GCP_REGION:-us-central1}

  # Create cluster if it doesn't exist
  if ! gcloud container clusters describe bootnode-cluster --region $REGION 2>/dev/null; then
    log_info "Creating GKE cluster..."
    gcloud container clusters create bootnode-cluster \
      --region $REGION \
      --num-nodes 3 \
      --machine-type e2-standard-4 \
      --enable-autoscaling --min-nodes 2 --max-nodes 10 \
      --workload-pool=$PROJECT_ID.svc.id.goog
  fi

  # Get credentials
  gcloud container clusters get-credentials bootnode-cluster --region $REGION

  # Push images to GCR
  log_info "Pushing images to GCR..."
  for image in api web indexer; do
    docker tag ghcr.io/hanzoai/bootnode:$image-latest gcr.io/$PROJECT_ID/hanzoai-bootnode:$image-latest
    docker push gcr.io/$PROJECT_ID/hanzoai-bootnode:$image-latest
  done

  # Deploy to Kubernetes
  deploy_kubernetes
}

# Deploy to Azure AKS
deploy_azure() {
  log_info "Deploying to Azure AKS..."

  RESOURCE_GROUP=${AZURE_RESOURCE_GROUP:-bootnode-rg}
  LOCATION=${AZURE_LOCATION:-eastus}

  # Create resource group
  az group create --name $RESOURCE_GROUP --location $LOCATION 2>/dev/null || true

  # Deploy cluster
  az deployment group create \
    --resource-group $RESOURCE_GROUP \
    --template-file "$SCRIPT_DIR/azure/aks-cluster.bicep"

  # Get credentials
  az aks get-credentials --resource-group $RESOURCE_GROUP --name bootnode-cluster

  # Push images to ACR
  log_info "Pushing images to ACR..."
  ACR_NAME="${RESOURCE_GROUP}acr"
  az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Standard 2>/dev/null || true
  az acr login --name $ACR_NAME

  for image in api web indexer; do
    docker tag ghcr.io/hanzoai/bootnode:$image-latest $ACR_NAME.azurecr.io/hanzoai/bootnode:$image-latest
    docker push $ACR_NAME.azurecr.io/hanzoai/bootnode:$image-latest
  done

  # Deploy to Kubernetes
  deploy_kubernetes
}

# Deploy to DigitalOcean DOKS
deploy_digitalocean() {
  log_info "Deploying to DigitalOcean Kubernetes..."

  # Create cluster if it doesn't exist
  if ! doctl kubernetes cluster get bootnode-cluster 2>/dev/null; then
    log_info "Creating DOKS cluster..."
    doctl kubernetes cluster create bootnode-cluster \
      --region nyc1 \
      --version 1.29.1-do.0 \
      --node-pool "name=api-pool;size=s-4vcpu-8gb;count=3;auto-scale=true;min-nodes=2;max-nodes=10"
  fi

  # Get credentials
  doctl kubernetes cluster kubeconfig save bootnode-cluster

  # Push images to DO Container Registry
  log_info "Pushing images to DO Container Registry..."
  doctl registry login
  REGISTRY=$(doctl registry get --format RegistryName --no-header)

  for image in api web indexer; do
    docker tag ghcr.io/hanzoai/bootnode:$image-latest registry.digitalocean.com/$REGISTRY/hanzoai-bootnode:$image-latest
    docker push registry.digitalocean.com/$REGISTRY/hanzoai-bootnode:$image-latest
  done

  # Deploy to Kubernetes
  deploy_kubernetes
}

# Deploy Kubernetes resources
deploy_kubernetes() {
  log_info "Deploying Kubernetes resources..."

  K8S_DIR="$ROOT_DIR/infra/k8s"

  # Create namespace
  kubectl apply -f "$K8S_DIR/namespace.yaml"

  # Create secrets (you should use external secrets manager in production)
  kubectl apply -f "$K8S_DIR/secrets.yaml"

  # Deploy services
  kubectl apply -f "$K8S_DIR/api-deployment.yaml"
  kubectl apply -f "$K8S_DIR/indexer-deployment.yaml"
  kubectl apply -f "$K8S_DIR/ingress.yaml"

  # Wait for deployments
  log_info "Waiting for deployments to be ready..."
  kubectl rollout status deployment/bootnode-api -n bootnode --timeout=300s
  kubectl rollout status deployment/bootnode-indexer -n bootnode --timeout=300s

  log_info "Deployment complete!"
  kubectl get pods -n bootnode
  kubectl get svc -n bootnode
}

# Main execution
check_prerequisites

# Build images for cloud deployments
if [ "$PROVIDER" != "docker" ]; then
  build_images
fi

# Deploy based on provider
case $PROVIDER in
  docker)
    deploy_docker
    ;;
  aws)
    deploy_aws
    ;;
  gcp)
    deploy_gcp
    ;;
  azure)
    deploy_azure
    ;;
  digitalocean)
    deploy_digitalocean
    ;;
  *)
    log_error "Unknown provider: $PROVIDER"
    echo "Supported providers: docker, aws, gcp, azure, digitalocean"
    exit 1
    ;;
esac
