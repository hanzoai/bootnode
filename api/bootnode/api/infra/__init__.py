"""
Infrastructure management API endpoints
Handles K8s clusters, persistent volumes, and storage operations
Supports DigitalOcean (DOKS), AWS (EKS), GCP (GKE), Azure (AKS)

Also handles Bootnode service deployment via pluggable deployers.
"""

import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from bootnode.core.deploy import ServiceStatus, ServiceType, get_deployer

router = APIRouter()


# === Configuration ===

class InfraConfig:
    """Infrastructure configuration from environment"""
    DO_TOKEN: str = os.getenv("DO_TOKEN", "")
    AWS_ACCESS_KEY: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    GCP_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    AZURE_CREDENTIALS: str = os.getenv("AZURE_CREDENTIALS", "")
    KUBECONFIG: str = os.getenv("KUBECONFIG", "")


# === Enums ===

class ClusterStatus(str, Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    UPDATING = "updating"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class VolumeStatus(str, Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    CREATING = "creating"
    DELETING = "deleting"
    CLONING = "cloning"
    ERROR = "error"


class ClusterProvider(str, Enum):
    DO = "digitalocean"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    LOCAL = "local"


# === Models ===

class ClusterCreate(BaseModel):
    name: str
    provider: ClusterProvider = ClusterProvider.DO
    region: str = "nyc1"
    node_count: int = 3
    node_size: str = "s-2vcpu-4gb"
    kubernetes_version: str = "1.31"
    auto_upgrade: bool = True
    tags: List[str] = []


class ClusterResponse(BaseModel):
    id: str
    name: str
    provider: str
    region: str
    status: str
    kubernetes_version: str
    node_count: int
    node_size: str
    endpoint: Optional[str]
    created_at: str
    updated_at: Optional[str]
    node_pools: List[Dict[str, Any]]
    tags: List[str]


class VolumeCreate(BaseModel):
    name: str
    size_gb: int = 100
    region: str = "nyc1"
    filesystem_type: str = "ext4"
    tags: List[str] = []


class VolumeResponse(BaseModel):
    id: str
    name: str
    size_gb: int
    region: str
    status: str
    filesystem_type: str
    attached_to: Optional[str]
    mount_path: Optional[str]
    created_at: str
    snapshots: List[Dict[str, Any]]
    tags: List[str]


class SnapshotCreate(BaseModel):
    name: str
    volume_id: str


class SnapshotResponse(BaseModel):
    id: str
    name: str
    volume_id: str
    size_gb: int
    status: str
    created_at: str
    region: str


class CloneRequest(BaseModel):
    source_id: str
    name: str
    region: Optional[str] = None


class CloneResponse(BaseModel):
    id: str
    name: str
    source_id: str
    source_type: str
    size_gb: int
    status: str
    progress: int
    estimated_completion: Optional[str]
    created_at: str


# === Provider Clients ===

def get_do_client():
    """Get DigitalOcean client"""
    try:
        from pydo import Client
        if not InfraConfig.DO_TOKEN:
            return None
        return Client(token=InfraConfig.DO_TOKEN)
    except ImportError:
        return None


def get_k8s_client(kubeconfig: Optional[str] = None):
    """Get Kubernetes client"""
    try:
        from kubernetes import client, config
        if kubeconfig:
            config.load_kube_config(config_file=kubeconfig)
        elif InfraConfig.KUBECONFIG:
            config.load_kube_config(config_file=InfraConfig.KUBECONFIG)
        else:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()
        return client
    except Exception:
        return None


# === DigitalOcean Operations ===

async def do_list_clusters(client) -> List[Dict]:
    """List DOKS clusters"""
    try:
        resp = client.kubernetes.list_clusters()
        clusters = []
        for c in resp.get("kubernetes_clusters", []):
            clusters.append({
                "id": c["id"],
                "name": c["name"],
                "provider": "digitalocean",
                "region": c["region"],
                "status": c["status"]["state"],
                "kubernetes_version": c["version"],
                "node_count": sum(p["count"] for p in c.get("node_pools", [])),
                "node_size": c["node_pools"][0]["size"] if c.get("node_pools") else "",
                "endpoint": c.get("endpoint"),
                "created_at": c["created_at"],
                "updated_at": c.get("updated_at"),
                "node_pools": [
                    {"name": p["name"], "count": p["count"], "size": p["size"]}
                    for p in c.get("node_pools", [])
                ],
                "tags": c.get("tags", []),
            })
        return clusters
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DO API error: {e}")


async def do_create_cluster(client, cluster: ClusterCreate) -> Dict:
    """Create DOKS cluster"""
    try:
        body = {
            "name": cluster.name,
            "region": cluster.region,
            "version": cluster.kubernetes_version,
            "auto_upgrade": cluster.auto_upgrade,
            "node_pools": [{
                "name": "default",
                "size": cluster.node_size,
                "count": cluster.node_count,
                "auto_scale": True,
                "min_nodes": 1,
                "max_nodes": cluster.node_count * 3,
            }],
            "tags": cluster.tags,
        }
        resp = client.kubernetes.create_cluster(body=body)
        c = resp["kubernetes_cluster"]
        return {
            "id": c["id"],
            "name": c["name"],
            "provider": "digitalocean",
            "region": c["region"],
            "status": c["status"]["state"],
            "kubernetes_version": c["version"],
            "node_count": cluster.node_count,
            "node_size": cluster.node_size,
            "endpoint": None,
            "created_at": c["created_at"],
            "updated_at": None,
            "node_pools": [{"name": "default", "count": cluster.node_count, "size": cluster.node_size}],
            "tags": cluster.tags,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DO API error: {e}")


async def do_get_kubeconfig(client, cluster_id: str) -> str:
    """Get DOKS cluster kubeconfig via DO API.

    Uses raw HTTP because pydo can't deserialize YAML responses.
    Falls back to doctl CLI if available.
    """
    import asyncio
    import httpx

    token = InfraConfig.DO_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="DO_TOKEN not configured")

    # Try raw HTTP first (pydo can't handle YAML content-type)
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.get(
                f"https://api.digitalocean.com/v2/kubernetes/clusters/{cluster_id}/kubeconfig",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                return resp.text
            raise HTTPException(status_code=resp.status_code, detail=f"DO API: {resp.text[:200]}")
    except httpx.HTTPError as e:
        # Fallback to doctl CLI
        try:
            proc = await asyncio.create_subprocess_exec(
                "doctl", "kubernetes", "cluster", "kubeconfig", "show", cluster_id,
                "--access-token", token,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode == 0:
                return stdout.decode()
            raise HTTPException(status_code=502, detail=f"doctl error: {stderr.decode()[:200]}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail=f"DO API error: {e}")


async def do_list_volumes(client) -> List[Dict]:
    """List DO block storage volumes"""
    try:
        resp = client.volumes.list()
        volumes = []
        for v in resp.get("volumes", []):
            volumes.append({
                "id": v["id"],
                "name": v["name"],
                "size_gb": v["size_gigabytes"],
                "region": v["region"]["slug"],
                "status": "in_use" if v.get("droplet_ids") else "available",
                "filesystem_type": v.get("filesystem_type", "ext4"),
                "attached_to": v["droplet_ids"][0] if v.get("droplet_ids") else None,
                "mount_path": None,
                "created_at": v["created_at"],
                "snapshots": [],
                "tags": v.get("tags", []),
            })
        return volumes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DO API error: {e}")


async def do_create_volume(client, volume: VolumeCreate) -> Dict:
    """Create DO block storage volume"""
    try:
        body = {
            "name": volume.name,
            "size_gigabytes": volume.size_gb,
            "region": volume.region,
            "filesystem_type": volume.filesystem_type,
            "tags": volume.tags,
        }
        resp = client.volumes.create(body=body)
        v = resp["volume"]
        return {
            "id": v["id"],
            "name": v["name"],
            "size_gb": v["size_gigabytes"],
            "region": v["region"]["slug"],
            "status": "creating",
            "filesystem_type": v.get("filesystem_type", "ext4"),
            "attached_to": None,
            "mount_path": None,
            "created_at": v["created_at"],
            "snapshots": [],
            "tags": v.get("tags", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DO API error: {e}")


async def do_create_snapshot(client, volume_id: str, name: str) -> Dict:
    """Create DO volume snapshot"""
    try:
        body = {"name": name}
        resp = client.volumes.create_snapshot(volume_id=volume_id, body=body)
        s = resp["snapshot"]
        return {
            "id": s["id"],
            "name": s["name"],
            "volume_id": volume_id,
            "size_gb": s["min_disk_size"],
            "status": "creating",
            "created_at": s["created_at"],
            "region": s["regions"][0] if s.get("regions") else "",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DO API error: {e}")


async def do_clone_volume(client, source_id: str, name: str, region: Optional[str] = None) -> Dict:
    """Clone volume from snapshot"""
    try:
        # First get the source volume to get size
        source = client.volumes.get(volume_id=source_id)
        v = source["volume"]

        # Create from snapshot if source_id is a snapshot, otherwise create new volume
        body = {
            "name": name,
            "size_gigabytes": v["size_gigabytes"],
            "region": region or v["region"]["slug"],
            "snapshot_id": source_id,  # Clone from snapshot
        }
        resp = client.volumes.create(body=body)
        new_v = resp["volume"]

        return {
            "id": f"clone-{new_v['id'][:8]}",
            "name": name,
            "source_id": source_id,
            "source_type": "volume",
            "size_gb": new_v["size_gigabytes"],
            "status": "cloning",
            "progress": 0,
            "estimated_completion": None,
            "created_at": new_v["created_at"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DO API error: {e}")


# === Kubernetes Native Operations ===

async def k8s_list_pvcs(k8s_client, namespace: str = "default") -> List[Dict]:
    """List Kubernetes PersistentVolumeClaims"""
    try:
        v1 = k8s_client.CoreV1Api()
        pvcs = v1.list_namespaced_persistent_volume_claim(namespace=namespace)
        volumes = []
        for pvc in pvcs.items:
            volumes.append({
                "id": pvc.metadata.uid,
                "name": pvc.metadata.name,
                "size_gb": int(pvc.spec.resources.requests.get("storage", "0Gi").replace("Gi", "")),
                "region": "k8s",
                "status": pvc.status.phase.lower(),
                "filesystem_type": "ext4",
                "attached_to": pvc.spec.volume_name,
                "mount_path": None,
                "created_at": pvc.metadata.creation_timestamp.isoformat() if pvc.metadata.creation_timestamp else "",
                "snapshots": [],
                "tags": list(pvc.metadata.labels.keys()) if pvc.metadata.labels else [],
            })
        return volumes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"K8s API error: {e}")


async def k8s_create_pvc(k8s_client, name: str, size_gb: int, storage_class: str = "do-block-storage", namespace: str = "default") -> Dict:
    """Create Kubernetes PersistentVolumeClaim"""
    try:
        v1 = k8s_client.CoreV1Api()
        pvc = k8s_client.V1PersistentVolumeClaim(
            metadata=k8s_client.V1ObjectMeta(name=name),
            spec=k8s_client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                storage_class_name=storage_class,
                resources=k8s_client.V1ResourceRequirements(
                    requests={"storage": f"{size_gb}Gi"}
                ),
            ),
        )
        created = v1.create_namespaced_persistent_volume_claim(namespace=namespace, body=pvc)
        return {
            "id": created.metadata.uid,
            "name": created.metadata.name,
            "size_gb": size_gb,
            "region": "k8s",
            "status": "creating",
            "filesystem_type": "ext4",
            "attached_to": None,
            "mount_path": None,
            "created_at": created.metadata.creation_timestamp.isoformat() if created.metadata.creation_timestamp else "",
            "snapshots": [],
            "tags": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"K8s API error: {e}")


# === Mock fallback data ===

MOCK_CLUSTERS = [
    {
        "id": "k8s-prod-001",
        "name": "Production Cluster",
        "provider": "digitalocean",
        "region": "nyc1",
        "status": "running",
        "kubernetes_version": "1.31.1",
        "node_count": 5,
        "node_size": "s-4vcpu-8gb",
        "endpoint": "https://k8s-prod-001.k8s.ondigitalocean.com",
        "created_at": "2024-01-10T08:00:00Z",
        "updated_at": "2024-01-20T12:00:00Z",
        "node_pools": [
            {"name": "default", "count": 3, "size": "s-4vcpu-8gb"},
            {"name": "compute", "count": 2, "size": "c-8vcpu-16gb"},
        ],
        "tags": ["production", "ethereum", "bitcoin"],
    },
]

MOCK_VOLUMES = [
    {
        "id": "vol-eth-chain-001",
        "name": "Ethereum Mainnet Data",
        "size_gb": 2000,
        "region": "nyc1",
        "status": "in_use",
        "filesystem_type": "ext4",
        "attached_to": "k8s-prod-001",
        "mount_path": "/data/ethereum",
        "created_at": "2024-01-10T09:00:00Z",
        "snapshots": [
            {"id": "snap-eth-001", "name": "Daily 2024-01-20", "size_gb": 2000, "created_at": "2024-01-20T00:00:00Z"},
        ],
        "tags": ["ethereum", "mainnet", "production"],
    },
]


# === API Endpoints ===

@router.get("/clusters", response_model=List[ClusterResponse])
async def list_clusters():
    """List all Kubernetes clusters.

    Returns DO clusters if DO_TOKEN is set, otherwise returns the local
    in-cluster entry when running inside K8s.
    """
    client = get_do_client()
    if client:
        return await do_list_clusters(client)

    # Detect in-cluster and return self
    if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token"):
        return [{
            "id": "incluster",
            "name": "Local Cluster",
            "provider": "kubernetes",
            "region": os.getenv("DO_REGION", "sfo3"),
            "status": "running",
            "kubernetes_version": "",
            "node_count": 0,
            "node_size": "",
            "endpoint": "https://kubernetes.default.svc",
            "created_at": "",
            "updated_at": None,
            "node_pools": [],
            "tags": ["incluster"],
        }]

    return MOCK_CLUSTERS


@router.get("/clusters/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(cluster_id: str):
    """Get details for a specific cluster"""
    client = get_do_client()
    if client:
        clusters = await do_list_clusters(client)
        for c in clusters:
            if c["id"] == cluster_id:
                return c
        raise HTTPException(status_code=404, detail="Cluster not found")

    for cluster in MOCK_CLUSTERS:
        if cluster["id"] == cluster_id:
            return cluster
    raise HTTPException(status_code=404, detail="Cluster not found")


@router.post("/clusters", response_model=ClusterResponse)
async def create_cluster(cluster: ClusterCreate):
    """Create a new Kubernetes cluster"""
    client = get_do_client()
    if client:
        return await do_create_cluster(client, cluster)

    # Mock response
    return {
        "id": f"k8s-{uuid.uuid4().hex[:8]}",
        "name": cluster.name,
        "provider": cluster.provider.value,
        "region": cluster.region,
        "status": "provisioning",
        "kubernetes_version": cluster.kubernetes_version,
        "node_count": cluster.node_count,
        "node_size": cluster.node_size,
        "endpoint": None,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": None,
        "node_pools": [{"name": "default", "count": cluster.node_count, "size": cluster.node_size}],
        "tags": cluster.tags,
    }


@router.delete("/clusters/{cluster_id}")
async def delete_cluster(cluster_id: str):
    """Delete a Kubernetes cluster"""
    client = get_do_client()
    if client:
        try:
            client.kubernetes.delete_cluster(cluster_id=cluster_id)
            return {"status": "deleting", "cluster_id": cluster_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DO API error: {e}")
    return {"status": "deleting", "cluster_id": cluster_id}


@router.post("/clusters/{cluster_id}/scale")
async def scale_cluster(cluster_id: str, node_count: int):
    """Scale cluster node count"""
    client = get_do_client()
    if client:
        try:
            # Get current cluster to find default pool
            resp = client.kubernetes.get_cluster(cluster_id=cluster_id)
            pool_id = resp["kubernetes_cluster"]["node_pools"][0]["id"]

            # Update pool size
            body = {"count": node_count}
            client.kubernetes.update_node_pool(cluster_id=cluster_id, node_pool_id=pool_id, body=body)

            return {"status": "scaling", "cluster_id": cluster_id, "target_nodes": node_count}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DO API error: {e}")

    return {"status": "scaling", "cluster_id": cluster_id, "target_nodes": node_count}


@router.get("/clusters/{cluster_id}/kubeconfig")
async def get_kubeconfig(cluster_id: str):
    """Get kubeconfig for cluster access"""
    client = get_do_client()
    if client:
        kubeconfig = await do_get_kubeconfig(client, cluster_id)
        return {"cluster_id": cluster_id, "kubeconfig": kubeconfig}

    # Mock kubeconfig
    return {
        "cluster_id": cluster_id,
        "kubeconfig": f"""apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://{cluster_id}.k8s.ondigitalocean.com
    certificate-authority-data: LS0t...
  name: {cluster_id}
contexts:
- context:
    cluster: {cluster_id}
    user: admin
  name: {cluster_id}
current-context: {cluster_id}
users:
- name: admin
  user:
    token: <token>
""",
    }


# === Volume Endpoints ===

@router.get("/volumes", response_model=List[VolumeResponse])
async def list_volumes():
    """List all persistent volumes"""
    client = get_do_client()
    if client:
        return await do_list_volumes(client)

    k8s = get_k8s_client()
    if k8s:
        return await k8s_list_pvcs(k8s)

    return MOCK_VOLUMES


@router.get("/volumes/{volume_id}", response_model=VolumeResponse)
async def get_volume(volume_id: str):
    """Get details for a specific volume"""
    volumes = await list_volumes()
    for v in volumes:
        if v["id"] == volume_id:
            return v
    raise HTTPException(status_code=404, detail="Volume not found")


@router.post("/volumes", response_model=VolumeResponse)
async def create_volume(volume: VolumeCreate):
    """Create a new persistent volume"""
    client = get_do_client()
    if client:
        return await do_create_volume(client, volume)

    k8s = get_k8s_client()
    if k8s:
        return await k8s_create_pvc(k8s, volume.name, volume.size_gb)

    return {
        "id": f"vol-{uuid.uuid4().hex[:8]}",
        "name": volume.name,
        "size_gb": volume.size_gb,
        "region": volume.region,
        "status": "creating",
        "filesystem_type": volume.filesystem_type,
        "attached_to": None,
        "mount_path": None,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "snapshots": [],
        "tags": volume.tags,
    }


@router.delete("/volumes/{volume_id}")
async def delete_volume(volume_id: str):
    """Delete a persistent volume"""
    client = get_do_client()
    if client:
        try:
            client.volumes.delete(volume_id=volume_id)
            return {"status": "deleting", "volume_id": volume_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DO API error: {e}")
    return {"status": "deleting", "volume_id": volume_id}


@router.post("/volumes/{volume_id}/attach")
async def attach_volume(volume_id: str, cluster_id: str, mount_path: str = "/data"):
    """Attach volume to a cluster"""
    return {"status": "attaching", "volume_id": volume_id, "cluster_id": cluster_id, "mount_path": mount_path}


@router.post("/volumes/{volume_id}/detach")
async def detach_volume(volume_id: str):
    """Detach volume from cluster"""
    return {"status": "detaching", "volume_id": volume_id}


@router.post("/volumes/{volume_id}/resize")
async def resize_volume(volume_id: str, new_size_gb: int):
    """Resize a persistent volume (can only increase)"""
    client = get_do_client()
    if client:
        try:
            body = {"size_gigabytes": new_size_gb}
            client.volumes.resize(volume_id=volume_id, body=body)
            return {"status": "resizing", "volume_id": volume_id, "new_size_gb": new_size_gb}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DO API error: {e}")
    return {"status": "resizing", "volume_id": volume_id, "new_size_gb": new_size_gb}


# === Snapshot Endpoints ===

@router.get("/snapshots", response_model=List[SnapshotResponse])
async def list_snapshots(volume_id: Optional[str] = None):
    """List all snapshots"""
    client = get_do_client()
    if client:
        try:
            resp = client.snapshots.list(resource_type="volume")
            snapshots = []
            for s in resp.get("snapshots", []):
                if volume_id and s.get("resource_id") != volume_id:
                    continue
                snapshots.append({
                    "id": s["id"],
                    "name": s["name"],
                    "volume_id": s.get("resource_id", ""),
                    "size_gb": s["min_disk_size"],
                    "status": "available",
                    "created_at": s["created_at"],
                    "region": s["regions"][0] if s.get("regions") else "",
                })
            return snapshots
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DO API error: {e}")

    # Mock fallback
    return [
        {"id": "snap-eth-001", "name": "Daily backup", "volume_id": "vol-eth-chain-001", "size_gb": 2000, "status": "available", "created_at": "2024-01-20T00:00:00Z", "region": "nyc1"}
    ]


@router.post("/snapshots", response_model=SnapshotResponse)
async def create_snapshot(snapshot: SnapshotCreate):
    """Create a snapshot of a volume"""
    client = get_do_client()
    if client:
        return await do_create_snapshot(client, snapshot.volume_id, snapshot.name)

    return {
        "id": f"snap-{uuid.uuid4().hex[:8]}",
        "name": snapshot.name,
        "volume_id": snapshot.volume_id,
        "size_gb": 100,
        "status": "creating",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "region": "nyc1",
    }


@router.delete("/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: str):
    """Delete a snapshot"""
    client = get_do_client()
    if client:
        try:
            client.snapshots.delete(snapshot_id=snapshot_id)
            return {"status": "deleting", "snapshot_id": snapshot_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DO API error: {e}")
    return {"status": "deleting", "snapshot_id": snapshot_id}


# === Clone Endpoints ===

@router.post("/clone", response_model=CloneResponse)
async def clone_storage(clone: CloneRequest):
    """Rapidly clone a volume or snapshot using copy-on-write"""
    client = get_do_client()
    if client:
        return await do_clone_volume(client, clone.source_id, clone.name, clone.region)

    return {
        "id": f"clone-{uuid.uuid4().hex[:8]}",
        "name": clone.name,
        "source_id": clone.source_id,
        "source_type": "volume",
        "size_gb": 100,
        "status": "cloning",
        "progress": 0,
        "estimated_completion": datetime.utcnow().isoformat() + "Z",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/clone", response_model=List[CloneResponse])
async def list_clones():
    """List all active clone operations"""
    return [
        {
            "id": "clone-example",
            "name": "Example Clone",
            "source_id": "vol-eth-chain-001",
            "source_type": "volume",
            "size_gb": 2000,
            "status": "completed",
            "progress": 100,
            "estimated_completion": None,
            "created_at": "2024-01-20T10:00:00Z",
        }
    ]


@router.get("/clone/{clone_id}", response_model=CloneResponse)
async def get_clone_status(clone_id: str):
    """Get status of a clone operation"""
    return {
        "id": clone_id,
        "name": "Clone Operation",
        "source_id": "vol-eth-chain-001",
        "source_type": "volume",
        "size_gb": 2000,
        "status": "completed",
        "progress": 100,
        "estimated_completion": None,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


@router.delete("/clone/{clone_id}")
async def cancel_clone(clone_id: str):
    """Cancel a clone operation"""
    return {"status": "cancelled", "clone_id": clone_id}


# === Service Deployment Endpoints ===


class ServiceScaleRequest(BaseModel):
    """Request to scale a service."""

    replicas: int = Field(ge=0, le=100, description="Target number of replicas")


class ServiceDeployRequest(BaseModel):
    """Request to deploy a service."""

    image: str = Field(description="Container image to deploy")
    replicas: int = Field(default=1, ge=1, le=100, description="Number of replicas")
    env: dict[str, str] | None = Field(default=None, description="Environment variables")


class ServiceListResponse(BaseModel):
    """List of service statuses."""

    services: list[ServiceStatus]


@router.get("/services", response_model=ServiceListResponse)
async def list_services():
    """List all Bootnode services and their status.

    Returns the current status of all managed services including
    running state, replica counts, and resource usage.
    """
    deployer = get_deployer()
    services = []

    for service_type in ServiceType:
        try:
            status = await deployer.status(service_type)
            services.append(status)
        except Exception:
            services.append(ServiceStatus(
                name=service_type.value,
                running=False,
                replicas=0,
                ready_replicas=0,
            ))

    return ServiceListResponse(services=services)


@router.get("/services/{service}/status", response_model=ServiceStatus)
async def get_service_status(service: str):
    """Get detailed status for a specific service.

    Args:
        service: Service name (api, web, indexer, webhook-worker, bundler)

    Returns:
        ServiceStatus with running state, replicas, and resource usage.
    """
    try:
        service_type = ServiceType(service)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service: {service}. Valid services: {[s.value for s in ServiceType]}",
        )

    deployer = get_deployer()
    return await deployer.status(service_type)


@router.post("/services/{service}/deploy", response_model=ServiceStatus)
async def deploy_service(service: str, request: ServiceDeployRequest):
    """Deploy or update a service.

    Args:
        service: Service name to deploy
        request: Deployment configuration including image and replicas

    Returns:
        ServiceStatus after deployment.
    """
    try:
        service_type = ServiceType(service)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service: {service}. Valid services: {[s.value for s in ServiceType]}",
        )

    deployer = get_deployer()
    success = await deployer.deploy(
        service_type,
        request.image,
        request.replicas,
        request.env,
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deploy service: {service}",
        )

    return await deployer.status(service_type)


@router.post("/services/{service}/scale", response_model=ServiceStatus)
async def scale_service(service: str, request: ServiceScaleRequest):
    """Scale a service to the specified number of replicas.

    Args:
        service: Service name to scale
        request: Scale configuration with target replicas

    Returns:
        ServiceStatus after scaling.
    """
    try:
        service_type = ServiceType(service)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service: {service}. Valid services: {[s.value for s in ServiceType]}",
        )

    deployer = get_deployer()
    success = await deployer.scale(service_type, request.replicas)

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scale service: {service}",
        )

    return await deployer.status(service_type)


@router.post("/services/{service}/restart", response_model=ServiceStatus)
async def restart_service(service: str):
    """Restart a service.

    Args:
        service: Service name to restart

    Returns:
        ServiceStatus after restart.
    """
    try:
        service_type = ServiceType(service)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service: {service}. Valid services: {[s.value for s in ServiceType]}",
        )

    deployer = get_deployer()
    success = await deployer.restart(service_type)

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart service: {service}",
        )

    return await deployer.status(service_type)


@router.delete("/services/{service}")
async def destroy_service(service: str):
    """Stop and remove a service.

    Args:
        service: Service name to destroy

    Returns:
        Confirmation of destruction.
    """
    try:
        service_type = ServiceType(service)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service: {service}. Valid services: {[s.value for s in ServiceType]}",
        )

    deployer = get_deployer()
    success = await deployer.destroy(service_type)

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to destroy service: {service}",
        )

    return {"status": "destroyed", "service": service}


@router.get("/services/{service}/logs")
async def get_service_logs(
    service: str,
    tail: int = Query(default=100, ge=1, le=10000, description="Number of lines to return"),
    follow: bool = Query(default=False, description="Stream logs continuously"),
):
    """Get logs from a service.

    Args:
        service: Service name to get logs from
        tail: Number of recent log lines to return
        follow: If true, stream logs continuously (SSE)

    Returns:
        Log lines as JSON array or SSE stream if follow=true.
    """
    try:
        service_type = ServiceType(service)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service: {service}. Valid services: {[s.value for s in ServiceType]}",
        )

    deployer = get_deployer()

    if follow:
        async def stream_logs():
            async for line in deployer.logs(service_type, tail=tail, follow=True):
                yield f"data: {line}\n\n"

        return StreamingResponse(
            stream_logs(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    else:
        logs = []
        async for line in deployer.logs(service_type, tail=tail, follow=False):
            logs.append(line)
        return {"service": service, "lines": logs}


@router.get("/services/{service}/health")
async def check_service_health(service: str):
    """Check if a service is healthy.

    Args:
        service: Service name to check

    Returns:
        Health status.
    """
    try:
        service_type = ServiceType(service)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service: {service}. Valid services: {[s.value for s in ServiceType]}",
        )

    deployer = get_deployer()
    is_healthy = await deployer.health(service_type)

    return {"service": service, "healthy": is_healthy}


# === Stats ===

@router.get("/stats")
async def get_infra_stats():
    """Get overall infrastructure statistics"""
    clusters = await list_clusters()
    volumes = await list_volumes()

    total_storage = sum(v.get("size_gb", 0) for v in volumes)
    used_storage = sum(v.get("size_gb", 0) for v in volumes if v.get("status") == "in_use")

    return {
        "clusters": {
            "total": len(clusters),
            "running": sum(1 for c in clusters if c.get("status") == "running"),
            "total_nodes": sum(c.get("node_count", 0) for c in clusters),
        },
        "volumes": {
            "total": len(volumes),
            "in_use": sum(1 for v in volumes if v.get("status") == "in_use"),
            "total_storage_gb": total_storage,
            "used_storage_gb": used_storage,
        },
        "snapshots": {
            "total": sum(len(v.get("snapshots", [])) for v in volumes),
        },
        "regions": list(set(c.get("region", "") for c in clusters) | set(v.get("region", "") for v in volumes)),
    }
