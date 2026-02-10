"""Lux Fleet API -- REST endpoints for managing Lux validator fleets.

Provides CRUD operations for Lux blockchain validator fleets deployed
via Helm charts to DOKS clusters.
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from bootnode.api.deps import ApiKeyDep
from bootnode.core.chains.lux import LuxFleetManager
from bootnode.core.chains.lux_models import (
    LuxFleetCreate,
    LuxFleetResponse,
    LuxFleetStats,
    LuxFleetStatus,
    LuxFleetSummary,
    LuxFleetUpdate,
    LuxNetwork,
    NETWORK_CONFIGS,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory fleet registry (source of truth is Helm releases on clusters)
_fleets: dict[str, dict] = {}

# Singleton manager
_manager = LuxFleetManager()

# K8s name validation: RFC 1123 DNS label
_K8S_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$")


def _validate_k8s_name(name: str, field: str = "name") -> None:
    """Validate a string is a valid K8s name (RFC 1123 DNS label)."""
    if not _K8S_NAME_RE.match(name):
        raise HTTPException(400, f"Invalid {field}: must match RFC 1123 DNS label")


async def _get_kubeconfig(cluster_id: str) -> str:
    """Fetch kubeconfig for a DOKS cluster via the infra API."""
    try:
        from bootnode.api.infra import do_get_kubeconfig, get_do_client
        client = get_do_client()
        if not client:
            raise HTTPException(500, "DigitalOcean client not configured")
        return await do_get_kubeconfig(client, cluster_id)
    except ImportError:
        raise HTTPException(500, "Infrastructure module not available")
    except HTTPException:
        raise
    except Exception:
        logger.error("Failed to fetch kubeconfig for cluster %s", cluster_id)
        raise HTTPException(502, "Failed to fetch kubeconfig for cluster")


# ---- Fleet CRUD ----

@router.post("/fleets", response_model=LuxFleetResponse)
async def create_fleet(
    params: LuxFleetCreate,
    background_tasks: BackgroundTasks,
    _api_key: ApiKeyDep,
) -> LuxFleetResponse:
    """Create a new Lux validator fleet on a DOKS cluster."""
    fleet_id = f"{params.name}-{params.network.value}"
    if fleet_id in _fleets:
        raise HTTPException(409, f"Fleet {fleet_id} already exists")

    kubeconfig = await _get_kubeconfig(params.cluster_id)
    result = await _manager.create(kubeconfig, params)

    _fleets[fleet_id] = {
        "name": params.name,
        "cluster_id": params.cluster_id,
        "network": params.network.value,
    }

    return result


@router.get("/fleets", response_model=list[LuxFleetSummary])
async def list_fleets(_api_key: ApiKeyDep, cluster_id: Optional[str] = None) -> list[LuxFleetSummary]:
    """List all Lux fleets, optionally filtered by cluster."""
    if cluster_id:
        kubeconfig = await _get_kubeconfig(cluster_id)
        return await _manager.list_fleets(kubeconfig, cluster_id)

    # List across all known clusters
    all_fleets = []
    cluster_ids = {f["cluster_id"] for f in _fleets.values()}
    for cid in cluster_ids:
        try:
            kubeconfig = await _get_kubeconfig(cid)
            fleets = await _manager.list_fleets(kubeconfig, cid)
            all_fleets.extend(fleets)
        except Exception as e:
            logger.warning("Failed to list fleets on cluster %s: %s", cid, e)
    return all_fleets


@router.get("/fleets/{cluster_id}/{network}", response_model=LuxFleetResponse)
async def get_fleet(cluster_id: str, network: LuxNetwork, _api_key: ApiKeyDep) -> LuxFleetResponse:
    """Get full status of a fleet including pods and endpoints."""
    kubeconfig = await _get_kubeconfig(cluster_id)

    # Find fleet name from registry
    name = f"luxd-{network.value}"
    for fid, fdata in _fleets.items():
        if fdata["cluster_id"] == cluster_id and fdata["network"] == network.value:
            name = fdata["name"]
            break

    return await _manager.get_status(kubeconfig, name, network, cluster_id)


@router.patch("/fleets/{cluster_id}/{network}", response_model=LuxFleetResponse)
async def update_fleet(
    cluster_id: str,
    network: LuxNetwork,
    params: LuxFleetUpdate,
    _api_key: ApiKeyDep,
) -> LuxFleetResponse:
    """Update a fleet (helm upgrade). Only provided fields are changed."""
    kubeconfig = await _get_kubeconfig(cluster_id)

    name = f"luxd-{network.value}"
    for fid, fdata in _fleets.items():
        if fdata["cluster_id"] == cluster_id and fdata["network"] == network.value:
            name = fdata["name"]
            break

    return await _manager.update(kubeconfig, name, network, cluster_id, params)


@router.delete("/fleets/{cluster_id}/{network}")
async def destroy_fleet(cluster_id: str, network: LuxNetwork, _api_key: ApiKeyDep) -> dict:
    """Destroy a fleet (helm uninstall). PVCs are preserved."""
    kubeconfig = await _get_kubeconfig(cluster_id)
    success = await _manager.destroy(kubeconfig, network)

    # Remove from registry
    to_remove = [
        fid for fid, fdata in _fleets.items()
        if fdata["cluster_id"] == cluster_id and fdata["network"] == network.value
    ]
    for fid in to_remove:
        del _fleets[fid]

    return {"success": success, "message": f"Fleet {network.value} destroyed on {cluster_id}"}


# ---- Fleet operations ----

@router.post("/fleets/{cluster_id}/{network}/scale", response_model=LuxFleetResponse)
async def scale_fleet(
    cluster_id: str,
    network: LuxNetwork,
    replicas: int,
    _api_key: ApiKeyDep,
) -> LuxFleetResponse:
    """Scale fleet to the specified replica count."""
    if replicas < 1 or replicas > 20:
        raise HTTPException(400, "Replicas must be between 1 and 20")

    kubeconfig = await _get_kubeconfig(cluster_id)
    name = f"luxd-{network.value}"
    return await _manager.scale(kubeconfig, name, network, cluster_id, replicas)


@router.post("/fleets/{cluster_id}/{network}/restart")
async def restart_fleet(
    cluster_id: str,
    network: LuxNetwork,
    background_tasks: BackgroundTasks,
    _api_key: ApiKeyDep,
) -> dict:
    """Rolling restart all pods (one at a time, OnDelete strategy)."""
    kubeconfig = await _get_kubeconfig(cluster_id)

    async def _do_restart():
        try:
            restarted = await _manager.rolling_restart(kubeconfig, network)
            logger.info("Rolling restart complete: %s", restarted)
        except Exception as e:
            logger.error("Rolling restart failed: %s", e)

    background_tasks.add_task(_do_restart)
    return {"message": f"Rolling restart initiated for {network.value}", "status": "started"}


@router.get("/fleets/{cluster_id}/{network}/pods/{pod_name}/logs")
async def get_pod_logs(
    cluster_id: str,
    network: LuxNetwork,
    pod_name: str,
    _api_key: ApiKeyDep,
    tail: int = 100,
) -> dict:
    """Get logs from a specific pod."""
    _validate_k8s_name(pod_name, "pod_name")
    if tail < 1 or tail > 10000:
        raise HTTPException(400, "tail must be between 1 and 10000")
    kubeconfig = await _get_kubeconfig(cluster_id)
    logs = await _manager.get_pod_logs(kubeconfig, network, pod_name, tail=tail)
    return {"pod": pod_name, "lines": logs.splitlines()}


@router.get("/fleets/{cluster_id}/{network}/pods/{pod_name}/health")
async def get_pod_health(
    cluster_id: str,
    network: LuxNetwork,
    pod_name: str,
    _api_key: ApiKeyDep,
) -> dict:
    """Probe a luxd node's health via RPC."""
    _validate_k8s_name(pod_name, "pod_name")
    kubeconfig = await _get_kubeconfig(cluster_id)
    return await _manager.probe_node_health(kubeconfig, network, pod_name)


# ---- Stats ----

@router.get("/stats", response_model=LuxFleetStats)
async def get_stats(_api_key: ApiKeyDep) -> LuxFleetStats:
    """Get aggregate fleet statistics."""
    total_fleets = len(_fleets)
    fleets_by_network: dict[str, int] = {}
    for fdata in _fleets.values():
        net = fdata["network"]
        fleets_by_network[net] = fleets_by_network.get(net, 0) + 1

    return LuxFleetStats(
        total_fleets=total_fleets,
        fleets_by_network=fleets_by_network,
    )


# ---- Network info ----

@router.get("/networks")
async def list_networks() -> dict:
    """List available Lux networks and their configurations."""
    return {
        "networks": {
            net.value: {
                "network_id": cfg.network_id,
                "chain_id": cfg.chain_id,
                "http_port": cfg.http_port,
                "staking_port": cfg.staking_port,
                "namespace": cfg.namespace,
            }
            for net, cfg in NETWORK_CONFIGS.items()
        }
    }
