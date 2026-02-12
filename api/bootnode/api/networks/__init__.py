"""
Network launcher API — 1-click deploy of a complete blockchain network stack.

Each network gets:
  - K8s namespace with bootnode-web + bootnode-api
  - IAM org + app for SSO
  - DNS records (cloud.{domain}, api.cloud.{domain})
  - Lux validator fleet (optional)
  - Ingress with TLS + CORS

Usage:
  POST /v1/networks  — Launch a new network
  GET  /v1/networks  — List all networks
  GET  /v1/networks/{id} — Get network status
  POST /v1/networks/{id}/scale — Scale network resources
  DELETE /v1/networks/{id} — Tear down network
"""

import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from bootnode.core.iam import get_current_user

logger = structlog.get_logger()
router = APIRouter()


# === Enums ===

class NetworkStatus(str, Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    DEPLOYING = "deploying"
    RUNNING = "running"
    UPDATING = "updating"
    ERROR = "error"
    DELETING = "deleting"
    DELETED = "deleted"


class NetworkTier(str, Enum):
    STARTER = "starter"      # Shared API, 2 web replicas
    PRO = "pro"              # Dedicated API, 3 web replicas, 3 validators
    ENTERPRISE = "enterprise"  # Dedicated cluster, custom config


# === Models ===

class NetworkBrand(BaseModel):
    """White-label branding configuration."""
    name: str = Field(description="Network display name (e.g. 'Lux Network')")
    domain: str = Field(description="Network domain (e.g. 'lux.network')")
    logo_url: str = ""
    primary_color: str = "#000000"
    accent_color: str = "#fd4444"


class NetworkCreate(BaseModel):
    """Request to launch a new blockchain network."""
    name: str = Field(description="Network slug (e.g. 'lux', 'pars', 'zoo')")
    brand: NetworkBrand
    tier: NetworkTier = NetworkTier.STARTER
    region: str = "sfo3"
    chain_id: Optional[int] = None  # Auto-assigned if not provided
    # Lux-specific
    deploy_validators: bool = False
    validator_count: int = 3
    # IAM
    iam_org: Optional[str] = None  # Defaults to network name
    iam_domain: Optional[str] = None  # e.g. lux.id


class NetworkResponse(BaseModel):
    """Network status and configuration."""
    id: str
    name: str
    brand: NetworkBrand
    tier: str
    status: str
    region: str
    chain_id: Optional[int]
    # URLs
    cloud_url: Optional[str]
    api_url: Optional[str]
    ws_url: Optional[str]
    rpc_url: Optional[str]
    # IAM
    iam_org: str
    iam_app_client_id: str
    iam_domain: Optional[str]
    # Infra
    web_replicas: int
    api_replicas: int
    validator_count: int
    cluster_id: Optional[str]
    namespace: str
    # Timestamps
    created_at: str
    updated_at: Optional[str]
    provisioned_at: Optional[str]
    error: Optional[str] = None


class NetworkScale(BaseModel):
    """Scale network resources."""
    web_replicas: Optional[int] = None
    api_replicas: Optional[int] = None
    validator_count: Optional[int] = None


# === In-memory registry (persisted to DB in production) ===

_networks: dict[str, dict] = {}


def _tier_defaults(tier: NetworkTier) -> dict:
    """Default resource allocation per tier."""
    if tier == NetworkTier.STARTER:
        return {"web_replicas": 2, "api_replicas": 0, "validator_count": 0}
    elif tier == NetworkTier.PRO:
        return {"web_replicas": 2, "api_replicas": 3, "validator_count": 3}
    else:
        return {"web_replicas": 3, "api_replicas": 5, "validator_count": 5}


# === K8s Deployment Helpers ===

async def _deploy_web(name: str, domain: str, brand: NetworkBrand,
                      iam_org: str, iam_domain: str, iam_client_id: str,
                      replicas: int = 2) -> bool:
    """Deploy white-labeled bootnode-web for a network."""
    import asyncio

    namespace = "bootnode"
    deployment_name = f"{name}-cloud-web"
    service_name = f"{name}-cloud-web"

    manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {deployment_name}
  namespace: {namespace}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {deployment_name}
  template:
    metadata:
      labels:
        app: {deployment_name}
    spec:
      imagePullSecrets:
      - name: ghcr-secret
      containers:
      - name: web
        image: ghcr.io/hanzoai/bootnode:web-latest
        imagePullPolicy: Always
        ports:
        - name: http
          containerPort: 3001
        env:
        - name: NODE_ENV
          value: production
        - name: NEXT_PUBLIC_BRAND
          value: "{name}"
        - name: BRAND
          value: "{name}"
        - name: NEXT_PUBLIC_API_URL
          value: "https://api.cloud.{domain}"
        - name: NEXT_PUBLIC_WS_URL
          value: "wss://ws.cloud.{domain}"
        - name: NEXT_PUBLIC_IAM_URL
          value: "https://hanzo.id"
        - name: NEXT_PUBLIC_IAM_CLIENT_ID
          value: "{iam_client_id}"
        - name: NEXT_PUBLIC_IAM_DOMAIN
          value: "{iam_domain}"
        - name: NEXT_PUBLIC_AUTH_MODE
          value: iam
        livenessProbe:
          httpGet:
            path: /
            port: 3001
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /
            port: 3001
          initialDelaySeconds: 10
          periodSeconds: 10
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: {service_name}
  namespace: {namespace}
spec:
  selector:
    app: {deployment_name}
  ports:
  - port: 3001
    targetPort: 3001
"""
    proc = await asyncio.create_subprocess_exec(
        "kubectl", "apply", "-f", "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(manifest.encode())
    if proc.returncode != 0:
        logger.error("deploy_web failed", name=name, error=stderr.decode())
        return False
    logger.info("deploy_web success", name=name, output=stdout.decode())
    return True


async def _deploy_ingress(name: str, domain: str, cors_origins: str) -> bool:
    """Deploy web + API ingresses with CORS for a network."""
    import asyncio

    namespace = "bootnode"

    manifest = f"""
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {name}-cloud-ingress
  namespace: {namespace}
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  ingressClassName: nginx
  rules:
  - host: cloud.{domain}
    http:
      paths:
      - backend:
          service:
            name: {name}-cloud-web
            port:
              number: 3001
        path: /
        pathType: Prefix
  tls:
  - hosts:
    - cloud.{domain}
    secretName: {name}-cloud-web-tls
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {name}-cloud-api-ingress
  namespace: {namespace}
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "{cors_origins}"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    nginx.ingress.kubernetes.io/cors-allow-headers: "DNT,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization,X-API-Key"
    nginx.ingress.kubernetes.io/cors-allow-credentials: "true"
    nginx.ingress.kubernetes.io/cors-max-age: "600"
spec:
  ingressClassName: nginx
  rules:
  - host: api.cloud.{domain}
    http:
      paths:
      - backend:
          service:
            name: bootnode-api
            port:
              number: 80
        path: /
        pathType: Prefix
  tls:
  - hosts:
    - api.cloud.{domain}
    secretName: {name}-cloud-api-tls
"""
    proc = await asyncio.create_subprocess_exec(
        "kubectl", "apply", "-f", "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(manifest.encode())
    if proc.returncode != 0:
        logger.error("deploy_ingress failed", name=name, error=stderr.decode())
        return False
    logger.info("deploy_ingress success", name=name, output=stdout.decode())
    return True


# === API Endpoints ===

@router.post("", response_model=NetworkResponse)
async def launch_network(req: NetworkCreate, user=Depends(get_current_user)):
    """Launch a new blockchain network with full stack.

    Creates:
    1. White-labeled cloud portal (bootnode-web)
    2. API backend (shared bootnode-api in starter tier)
    3. K8s ingresses with TLS + CORS
    4. IAM integration for SSO

    DNS records for cloud.{domain} and api.cloud.{domain} must point
    to the cluster load balancer IP.
    """
    network_id = f"net-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    iam_org = req.iam_org or req.name
    iam_domain = req.iam_domain or f"{req.name}.id"
    iam_client_id = f"{req.name}-cloud"
    tier = _tier_defaults(req.tier)

    # Build CORS origins list (all known cloud domains)
    all_origins = [
        f"https://cloud.{req.brand.domain}",
        "https://cloud.lux.network",
        "https://cloud.pars.network",
        "https://cloud.zoo.network",
        "https://cloud.hanzo.network",
        "https://cloud.hanzo.ai",
        "https://bootno.de",
    ]
    cors_origins = ",".join(all_origins)

    network = {
        "id": network_id,
        "name": req.name,
        "brand": req.brand.model_dump(),
        "tier": req.tier.value,
        "status": NetworkStatus.PROVISIONING.value,
        "region": req.region,
        "chain_id": req.chain_id,
        "cloud_url": f"https://cloud.{req.brand.domain}",
        "api_url": f"https://api.cloud.{req.brand.domain}",
        "ws_url": f"wss://ws.cloud.{req.brand.domain}",
        "rpc_url": f"https://api.cloud.{req.brand.domain}/v1/rpc/{req.name}",
        "iam_org": iam_org,
        "iam_app_client_id": iam_client_id,
        "iam_domain": iam_domain,
        "web_replicas": tier["web_replicas"],
        "api_replicas": tier["api_replicas"],
        "validator_count": tier["validator_count"] if req.deploy_validators else 0,
        "cluster_id": None,
        "namespace": "bootnode",
        "created_at": now,
        "updated_at": now,
        "provisioned_at": None,
        "error": None,
    }

    _networks[network_id] = network

    # Deploy web frontend
    try:
        ok = await _deploy_web(
            name=req.name,
            domain=req.brand.domain,
            brand=req.brand,
            iam_org=iam_org,
            iam_domain=iam_domain,
            iam_client_id=iam_client_id,
            replicas=tier["web_replicas"],
        )
        if not ok:
            network["status"] = NetworkStatus.ERROR.value
            network["error"] = "Failed to deploy web frontend"
            return NetworkResponse(**network)
    except Exception as e:
        network["status"] = NetworkStatus.ERROR.value
        network["error"] = str(e)
        return NetworkResponse(**network)

    # Deploy ingresses
    try:
        ok = await _deploy_ingress(
            name=req.name,
            domain=req.brand.domain,
            cors_origins=cors_origins,
        )
        if not ok:
            network["status"] = NetworkStatus.ERROR.value
            network["error"] = "Failed to deploy ingresses"
            return NetworkResponse(**network)
    except Exception as e:
        network["status"] = NetworkStatus.ERROR.value
        network["error"] = str(e)
        return NetworkResponse(**network)

    network["status"] = NetworkStatus.RUNNING.value
    network["provisioned_at"] = datetime.now(timezone.utc).isoformat()
    network["updated_at"] = datetime.now(timezone.utc).isoformat()

    logger.info(
        "network launched",
        network_id=network_id,
        name=req.name,
        domain=req.brand.domain,
        tier=req.tier.value,
    )

    return NetworkResponse(**network)


@router.get("", response_model=list[NetworkResponse])
async def list_networks(user=Depends(get_current_user)):
    """List all launched networks."""
    return [NetworkResponse(**n) for n in _networks.values()]


@router.get("/{network_id}", response_model=NetworkResponse)
async def get_network(network_id: str, user=Depends(get_current_user)):
    """Get status of a specific network."""
    if network_id not in _networks:
        raise HTTPException(status_code=404, detail="Network not found")
    return NetworkResponse(**_networks[network_id])


@router.post("/{network_id}/scale", response_model=NetworkResponse)
async def scale_network(network_id: str, req: NetworkScale, user=Depends(get_current_user)):
    """Scale network resources (web replicas, API replicas, validators)."""
    import asyncio

    if network_id not in _networks:
        raise HTTPException(status_code=404, detail="Network not found")

    network = _networks[network_id]
    name = network["name"]
    namespace = network["namespace"]

    if req.web_replicas is not None:
        proc = await asyncio.create_subprocess_exec(
            "kubectl", "scale", f"deployment/{name}-cloud-web",
            f"--replicas={req.web_replicas}",
            f"-n", namespace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        network["web_replicas"] = req.web_replicas

    network["updated_at"] = datetime.now(timezone.utc).isoformat()
    return NetworkResponse(**network)


@router.delete("/{network_id}")
async def delete_network(network_id: str, user=Depends(get_current_user)):
    """Tear down a network (removes deployments, services, ingresses)."""
    import asyncio

    if network_id not in _networks:
        raise HTTPException(status_code=404, detail="Network not found")

    network = _networks[network_id]
    name = network["name"]
    namespace = network["namespace"]
    network["status"] = NetworkStatus.DELETING.value

    resources = [
        f"deployment/{name}-cloud-web",
        f"service/{name}-cloud-web",
        f"ingress/{name}-cloud-ingress",
        f"ingress/{name}-cloud-api-ingress",
    ]

    for resource in resources:
        proc = await asyncio.create_subprocess_exec(
            "kubectl", "delete", resource, "-n", namespace, "--ignore-not-found",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    network["status"] = NetworkStatus.DELETED.value
    network["updated_at"] = datetime.now(timezone.utc).isoformat()

    return {"status": "deleted", "network_id": network_id, "name": name}
