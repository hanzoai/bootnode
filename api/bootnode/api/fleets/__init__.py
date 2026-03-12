"""Fleet API -- chain-agnostic REST endpoints for managing blockchain node fleets.

Unified surface: /v1/fleets
  - Manages any chain (lux, hanzo, zoo, pars, avalanche, ethereum, bitcoin, solana, filecoin)
  - Multi-tenant: fleets scoped to IAM org via project
  - Cross-cluster management via DO API kubeconfig
  - Full CRUD + scale/restart/logs/health/stats
"""

import logging
import os
import re
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bootnode.api.deps import ApiKeyDep, ProjectDep, DbDep
from bootnode.core.chains.fleet_manager import FleetManager
from bootnode.core.chains.fleet_models import (
    CHAIN_NETWORKS,
    FleetCreate,
    FleetResponse,
    FleetStats,
    FleetSummary,
    FleetUpdate,
)
from bootnode.db.models import OrgCluster, Project
from bootnode.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

_manager = FleetManager()

_K8S_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$")
_INCLUSTER_ID = "incluster"


# ---- Helpers ----

def _validate_k8s_name(name: str, field: str = "name") -> None:
    if not _K8S_NAME_RE.match(name):
        raise HTTPException(400, f"Invalid {field}: must match RFC 1123 DNS label")


def _validate_chain(chain: str) -> None:
    if chain not in CHAIN_NETWORKS:
        raise HTTPException(400, f"Unknown chain: {chain}. Supported: {list(CHAIN_NETWORKS.keys())}")


def _validate_network(chain: str, network: str) -> None:
    _validate_chain(chain)
    nets = CHAIN_NETWORKS[chain]
    if network not in nets:
        raise HTTPException(400, f"Unknown network {network} for chain {chain}. Available: {list(nets.keys())}")


def _is_incluster() -> bool:
    return os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")


async def _get_kubeconfig(cluster_id: str) -> Optional[str]:
    if cluster_id == _INCLUSTER_ID:
        return None
    try:
        from bootnode.api.infra import do_get_kubeconfig, get_do_client
        client = get_do_client()
        if not client:
            if _is_incluster():
                return None
            raise HTTPException(500, "DigitalOcean client not configured")
        return await do_get_kubeconfig(client, cluster_id)
    except ImportError:
        if _is_incluster():
            return None
        raise HTTPException(500, "Infrastructure module not available")
    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to fetch kubeconfig for cluster %s", cluster_id)
        if _is_incluster():
            return None
        raise HTTPException(502, "Failed to fetch kubeconfig for cluster")


async def _get_org_clusters(project: Project, db: AsyncSession) -> list[OrgCluster]:
    """Get clusters accessible to this project's org."""
    result = await db.execute(
        select(OrgCluster).where(
            OrgCluster.project_id == project.id,
            OrgCluster.is_active,
        )
    )
    return list(result.scalars().all())


async def _check_cluster_access(
    project: Project, cluster_id: str, db: AsyncSession,
) -> None:
    """Verify the project has access to the given cluster.

    Admin projects (role in settings) bypass this check.
    Projects with no OrgCluster entries also bypass (open access for bootstrapping).
    """
    if project.settings and project.settings.get("admin"):
        return

    clusters = await _get_org_clusters(project, db)
    if not clusters:
        return  # No cluster restrictions configured

    allowed_ids = {c.cluster_id for c in clusters}
    if cluster_id not in allowed_ids:
        raise HTTPException(
            403, f"Project does not have access to cluster {cluster_id}",
        )


def _check_chain_access(project: Project, chain: str) -> None:
    """Verify the project is allowed to use this chain."""
    if project.allowed_chains and chain not in project.allowed_chains:
        raise HTTPException(
            403, f"Project does not have access to chain {chain}. Allowed: {project.allowed_chains}",
        )


# ---- Fleet CRUD ----

@router.post("", response_model=FleetResponse)
async def create_fleet(
    params: FleetCreate,
    background_tasks: BackgroundTasks,
    project: ProjectDep,
    db: DbDep,
) -> FleetResponse:
    """Create a new node fleet on a cluster."""
    _validate_network(params.chain, params.network)
    _check_chain_access(project, params.chain)
    await _check_cluster_access(project, params.cluster_id, db)

    kubeconfig = await _get_kubeconfig(params.cluster_id)
    return await _manager.create(kubeconfig, params)


@router.get("", response_model=list[FleetSummary])
async def list_fleets(
    project: ProjectDep,
    db: DbDep,
    cluster_id: Optional[str] = None,
    chain: Optional[str] = None,
) -> list[FleetSummary]:
    """List all node fleets, optionally filtered by cluster and/or chain."""
    if chain:
        _validate_chain(chain)

    # If cluster_id provided, use it directly (with access check)
    if cluster_id:
        await _check_cluster_access(project, cluster_id, db)
        kubeconfig = await _get_kubeconfig(cluster_id)
        return await _manager.list_fleets(kubeconfig, cluster_id, chain=chain)

    # Otherwise, list across all org clusters
    org_clusters = await _get_org_clusters(project, db)

    if org_clusters:
        all_fleets = []
        for oc in org_clusters:
            try:
                kubeconfig = await _get_kubeconfig(oc.cluster_id)
                fleets = await _manager.list_fleets(kubeconfig, oc.cluster_id, chain=chain)
                all_fleets.extend(fleets)
            except Exception as e:
                logger.warning("Failed to list fleets on cluster %s: %s", oc.cluster_id, e)
        return all_fleets

    # No clusters configured - check in-cluster
    if _is_incluster():
        return await _manager.list_fleets(None, _INCLUSTER_ID, chain=chain)

    return []


@router.get("/stats", response_model=FleetStats)
async def get_stats(
    project: ProjectDep,
    db: DbDep,
    cluster_id: Optional[str] = None,
    chain: Optional[str] = None,
) -> FleetStats:
    """Get aggregate fleet statistics across all chains."""
    if chain:
        _validate_chain(chain)

    # Determine which clusters to query
    cluster_ids_to_check: list[str] = []
    if cluster_id:
        await _check_cluster_access(project, cluster_id, db)
        cluster_ids_to_check = [cluster_id]
    else:
        org_clusters = await _get_org_clusters(project, db)
        cluster_ids_to_check = [oc.cluster_id for oc in org_clusters]
        if not cluster_ids_to_check and _is_incluster():
            cluster_ids_to_check = [_INCLUSTER_ID]

    if not cluster_ids_to_check:
        return FleetStats()

    all_fleets: list[FleetSummary] = []
    for cid in cluster_ids_to_check:
        try:
            kubeconfig = await _get_kubeconfig(cid)
            fleets = await _manager.list_fleets(kubeconfig, cid, chain=chain)
            all_fleets.extend(fleets)
        except Exception as e:
            logger.warning("Failed to get stats from cluster %s: %s", cid, e)

    total_nodes = sum(f.replicas for f in all_fleets)
    healthy_nodes = sum(f.ready_replicas for f in all_fleets)
    fleets_by_network: dict[str, int] = {}
    fleets_by_chain: dict[str, int] = {}
    fleets_by_status: dict[str, int] = {}

    for f in all_fleets:
        fleets_by_network[f.network] = fleets_by_network.get(f.network, 0) + 1
        fleets_by_chain[f.chain] = fleets_by_chain.get(f.chain, 0) + 1
        fleets_by_status[f.status.value] = fleets_by_status.get(f.status.value, 0) + 1

    return FleetStats(
        total_fleets=len(all_fleets),
        total_nodes=total_nodes,
        healthy_nodes=healthy_nodes,
        fleets_by_chain=fleets_by_chain,
        fleets_by_network=fleets_by_network,
        fleets_by_status=fleets_by_status,
    )


@router.get("/chains")
async def list_chains() -> dict:
    """List all supported chains and their available networks."""
    return {
        chain: list(networks.keys())
        for chain, networks in CHAIN_NETWORKS.items()
    }


@router.get("/networks")
async def list_networks(chain: Optional[str] = None) -> dict:
    """List network configurations, optionally filtered by chain."""
    chains_to_show = (
        {chain: CHAIN_NETWORKS[chain]} if chain and chain in CHAIN_NETWORKS
        else CHAIN_NETWORKS
    )
    result = {}
    for ch, networks in chains_to_show.items():
        result[ch] = {
            name: {
                "network_id": cfg.network_id,
                "chain_id": cfg.chain_id,
                "http_port": cfg.http_port,
                "staking_port": cfg.staking_port,
                "namespace": cfg.namespace,
            }
            for name, cfg in networks.items()
        }
    return {"chains": result}


# ---- Org cluster management ----

@router.get("/clusters")
async def list_org_clusters(project: ProjectDep, db: DbDep) -> list[dict]:
    """List clusters accessible to this project."""
    clusters = await _get_org_clusters(project, db)
    return [
        {
            "id": str(c.id),
            "cluster_id": c.cluster_id,
            "cluster_name": c.cluster_name,
            "provider": c.provider,
            "region": c.region,
            "allowed_chains": c.allowed_chains,
            "allowed_namespaces": c.allowed_namespaces,
            "is_active": c.is_active,
        }
        for c in clusters
    ]


@router.post("/clusters")
async def add_org_cluster(
    cluster_id: str,
    cluster_name: str,
    project: ProjectDep,
    db: DbDep,
    provider: str = "digitalocean",
    region: str = "sfo3",
    allowed_chains: Optional[list[str]] = None,
) -> dict:
    """Add a cluster to this project's accessible clusters."""
    oc = OrgCluster(
        project_id=project.id,
        cluster_id=cluster_id,
        cluster_name=cluster_name,
        provider=provider,
        region=region,
        allowed_chains=allowed_chains,
    )
    db.add(oc)
    await db.commit()
    return {"id": str(oc.id), "cluster_id": cluster_id, "status": "added"}


@router.delete("/clusters/{cluster_id}")
async def remove_org_cluster(
    cluster_id: str,
    project: ProjectDep,
    db: DbDep,
) -> dict:
    """Remove a cluster from this project's access."""
    result = await db.execute(
        select(OrgCluster).where(
            OrgCluster.project_id == project.id,
            OrgCluster.cluster_id == cluster_id,
        )
    )
    oc = result.scalar_one_or_none()
    if not oc:
        raise HTTPException(404, "Cluster not found in project")
    await db.delete(oc)
    await db.commit()
    return {"cluster_id": cluster_id, "status": "removed"}


# ---- Fleet detail + operations ----

@router.get("/{chain}/{cluster_id}/{network}", response_model=FleetResponse)
async def get_fleet(
    chain: str,
    cluster_id: str,
    network: str,
    project: ProjectDep,
    db: DbDep,
) -> FleetResponse:
    """Get full status of a fleet including nodes and endpoints."""
    _validate_network(chain, network)
    _check_chain_access(project, chain)
    await _check_cluster_access(project, cluster_id, db)
    kubeconfig = await _get_kubeconfig(cluster_id)
    return await _manager.get_status(kubeconfig, chain, network, cluster_id)


@router.patch("/{chain}/{cluster_id}/{network}", response_model=FleetResponse)
async def update_fleet(
    chain: str,
    cluster_id: str,
    network: str,
    params: FleetUpdate,
    project: ProjectDep,
    db: DbDep,
) -> FleetResponse:
    """Update a fleet. Only provided fields are changed."""
    _validate_network(chain, network)
    _check_chain_access(project, chain)
    await _check_cluster_access(project, cluster_id, db)
    kubeconfig = await _get_kubeconfig(cluster_id)
    return await _manager.update(kubeconfig, chain, network, cluster_id, params)


@router.delete("/{chain}/{cluster_id}/{network}")
async def destroy_fleet(
    chain: str,
    cluster_id: str,
    network: str,
    project: ProjectDep,
    db: DbDep,
) -> dict:
    """Destroy a fleet. PVCs are preserved."""
    _validate_network(chain, network)
    _check_chain_access(project, chain)
    await _check_cluster_access(project, cluster_id, db)
    kubeconfig = await _get_kubeconfig(cluster_id)
    success = await _manager.destroy(kubeconfig, chain, network)
    return {"success": success, "message": f"Fleet {chain}-{network} destroyed on {cluster_id}"}


@router.post("/{chain}/{cluster_id}/{network}/scale", response_model=FleetResponse)
async def scale_fleet(
    chain: str,
    cluster_id: str,
    network: str,
    replicas: int,
    project: ProjectDep,
    db: DbDep,
) -> FleetResponse:
    """Scale fleet to the specified replica count."""
    _validate_network(chain, network)
    _check_chain_access(project, chain)
    await _check_cluster_access(project, cluster_id, db)
    if replicas < 1 or replicas > 100:
        raise HTTPException(400, "Replicas must be between 1 and 100")
    kubeconfig = await _get_kubeconfig(cluster_id)
    return await _manager.scale(kubeconfig, chain, network, cluster_id, replicas)


@router.post("/{chain}/{cluster_id}/{network}/restart")
async def restart_fleet(
    chain: str,
    cluster_id: str,
    network: str,
    background_tasks: BackgroundTasks,
    project: ProjectDep,
    db: DbDep,
) -> dict:
    """Rolling restart all pods."""
    _validate_network(chain, network)
    _check_chain_access(project, chain)
    await _check_cluster_access(project, cluster_id, db)
    kubeconfig = await _get_kubeconfig(cluster_id)

    async def _do_restart():
        try:
            restarted = await _manager.restart(kubeconfig, chain, network)
            logger.info("Rolling restart complete: %s", restarted)
        except Exception as e:
            logger.error("Rolling restart failed: %s", e)

    background_tasks.add_task(_do_restart)
    return {"message": f"Rolling restart initiated for {chain}-{network}", "status": "started"}


@router.get("/{chain}/{cluster_id}/{network}/pods/{pod_name}/logs")
async def get_pod_logs(
    chain: str,
    cluster_id: str,
    network: str,
    pod_name: str,
    project: ProjectDep,
    db: DbDep,
    tail: int = 100,
) -> dict:
    """Get logs from a specific pod."""
    _validate_network(chain, network)
    _check_chain_access(project, chain)
    await _check_cluster_access(project, cluster_id, db)
    _validate_k8s_name(pod_name, "pod_name")
    if tail < 1 or tail > 10000:
        raise HTTPException(400, "tail must be between 1 and 10000")
    kubeconfig = await _get_kubeconfig(cluster_id)
    logs = await _manager.get_pod_logs(kubeconfig, chain, network, pod_name, tail=tail)
    return {"pod": pod_name, "lines": logs.splitlines()}


@router.get("/{chain}/{cluster_id}/{network}/pods/{pod_name}/health")
async def get_pod_health(
    chain: str,
    cluster_id: str,
    network: str,
    pod_name: str,
    project: ProjectDep,
    db: DbDep,
) -> dict:
    """Probe a node's health."""
    _validate_network(chain, network)
    _check_chain_access(project, chain)
    await _check_cluster_access(project, cluster_id, db)
    _validate_k8s_name(pod_name, "pod_name")
    kubeconfig = await _get_kubeconfig(cluster_id)
    return await _manager.probe_node(kubeconfig, chain, network, pod_name)
