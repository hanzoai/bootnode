"""Lux fleet manager -- business logic for validator fleet lifecycle.

Orchestrates Lux validator fleet deployments via HelmDeployer.
Each fleet operation:
  1. Fetches kubeconfig for the target cluster
  2. Creates a HelmDeployer pointed at that cluster
  3. Runs the Helm operation
  4. Probes individual pod health via luxd RPC
"""

import asyncio
import json
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from bootnode.core.chains.lux_models import (
    NETWORK_CONFIGS,
    LuxFleetCreate,
    LuxFleetResponse,
    LuxFleetStatus,
    LuxFleetSummary,
    LuxFleetUpdate,
    LuxNetwork,
    LuxNodeInfo,
    LuxNodeStatus,
    fleet_create_to_helm_values,
    fleet_update_to_helm_values,
)
from bootnode.core.deploy.helm import HelmDeployer, HelmError

logger = logging.getLogger(__name__)

# Chart path defaults to the devops repo checkout
DEFAULT_CHART_PATH = Path("/opt/charts/lux")

# Network-specific values files
NETWORK_VALUES_FILES: dict[str, str] = {
    "mainnet": "values-mainnet.yaml",
    "testnet": "values-testnet.yaml",
}


@dataclass
class LuxFleetManager:
    """Manages Lux validator fleet lifecycle via Helm."""

    chart_path: Path = DEFAULT_CHART_PATH

    def _release_name(self, network: LuxNetwork) -> str:
        return f"luxd-{network.value}"

    def _namespace(self, network: LuxNetwork) -> str:
        return NETWORK_CONFIGS[network].namespace

    def _fleet_id(self, name: str, network: LuxNetwork) -> str:
        return f"{name}-{network.value}"

    async def _get_deployer(self, kubeconfig_data: str) -> HelmDeployer:
        """Create a HelmDeployer from raw kubeconfig YAML.

        The returned deployer's kubeconfig temp file is tracked for cleanup.
        Call deployer.cleanup_temp_files() when done.
        """
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".kubeconfig", delete=False
        )
        tmp.write(kubeconfig_data)
        tmp.flush()
        tmp.close()
        kc_path = Path(tmp.name)
        deployer = HelmDeployer(
            chart_path=self.chart_path,
            kubeconfig_path=kc_path,
        )
        # Track kubeconfig path for cleanup alongside helm values files
        if not hasattr(deployer, "_temp_files"):
            deployer._temp_files = []
        deployer._temp_files.append(kc_path)
        return deployer

    def _get_values_files(self, network: LuxNetwork) -> list[Path]:
        """Get the network-specific values file if one exists."""
        filename = NETWORK_VALUES_FILES.get(network.value)
        if filename:
            full_path = self.chart_path / filename
            if full_path.exists():
                return [full_path]
        return []

    # ---- Fleet lifecycle ----

    async def create(
        self,
        kubeconfig: str,
        params: LuxFleetCreate,
    ) -> LuxFleetResponse:
        """Create a new Lux validator fleet."""
        deployer = await self._get_deployer(kubeconfig)
        try:
            release_name = self._release_name(params.network)
            namespace = self._namespace(params.network)
            values = fleet_create_to_helm_values(params)
            values_files = self._get_values_files(params.network)

            logger.info(
                "Creating Lux fleet: release=%s namespace=%s network=%s replicas=%d",
                release_name, namespace, params.network.value, params.replicas,
            )

            try:
                release = await deployer.install(
                    release_name=release_name,
                    namespace=namespace,
                    values=values,
                    values_files=values_files,
                    wait=False,
                    create_namespace=True,
                )
                status = LuxFleetStatus.DEPLOYING
            except HelmError as e:
                logger.error("Fleet creation failed: %s", e)
                return LuxFleetResponse(
                    id=self._fleet_id(params.name, params.network),
                    name=params.name,
                    cluster_id=params.cluster_id,
                    network=params.network,
                    status=LuxFleetStatus.ERROR,
                    replicas=params.replicas,
                    namespace=namespace,
                    error=str(e),
                )

            return LuxFleetResponse(
                id=self._fleet_id(params.name, params.network),
                name=params.name,
                cluster_id=params.cluster_id,
                network=params.network,
                status=status,
                replicas=params.replicas,
                namespace=namespace,
                helm_revision=release.revision,
                image=params.image if params.image else None,
            )
        finally:
            deployer.cleanup_temp_files()

    async def update(
        self,
        kubeconfig: str,
        name: str,
        network: LuxNetwork,
        cluster_id: str,
        params: LuxFleetUpdate,
    ) -> LuxFleetResponse:
        """Update an existing fleet (helm upgrade)."""
        deployer = await self._get_deployer(kubeconfig)
        try:
            release_name = self._release_name(network)
            namespace = self._namespace(network)
            values = fleet_update_to_helm_values(params)

            logger.info("Updating fleet: release=%s values=%s", release_name, values)

            try:
                release = await deployer.upgrade(
                    release_name=release_name,
                    namespace=namespace,
                    values=values,
                    reuse_values=True,
                )
            except HelmError as e:
                logger.error("Fleet update failed: %s", e)
                return LuxFleetResponse(
                    id=self._fleet_id(name, network),
                    name=name,
                    cluster_id=cluster_id,
                    network=network,
                    status=LuxFleetStatus.ERROR,
                    replicas=params.replicas or 0,
                    namespace=namespace,
                    error=str(e),
                )

            # Get pod status after upgrade
            pods = await deployer.get_pods(namespace, "app=luxd")
            ready_count = sum(1 for p in pods if p.ready)
            total = len(pods)

            return LuxFleetResponse(
                id=self._fleet_id(name, network),
                name=name,
                cluster_id=cluster_id,
                network=network,
                status=LuxFleetStatus.UPDATING,
                replicas=total,
                ready_replicas=ready_count,
                namespace=namespace,
                helm_revision=release.revision,
            )
        finally:
            deployer.cleanup_temp_files()

    async def scale(
        self,
        kubeconfig: str,
        name: str,
        network: LuxNetwork,
        cluster_id: str,
        replicas: int,
    ) -> LuxFleetResponse:
        """Scale a fleet's replica count."""
        return await self.update(
            kubeconfig=kubeconfig,
            name=name,
            network=network,
            cluster_id=cluster_id,
            params=LuxFleetUpdate(replicas=replicas),
        )

    async def destroy(
        self,
        kubeconfig: str,
        network: LuxNetwork,
    ) -> bool:
        """Destroy a fleet (helm uninstall). PVCs persist."""
        deployer = await self._get_deployer(kubeconfig)
        try:
            release_name = self._release_name(network)
            namespace = self._namespace(network)
            return await deployer.uninstall(release_name, namespace)
        finally:
            deployer.cleanup_temp_files()

    async def get_status(
        self,
        kubeconfig: str,
        name: str,
        network: LuxNetwork,
        cluster_id: str,
    ) -> LuxFleetResponse:
        """Get full status of a fleet including pods and endpoints."""
        deployer = await self._get_deployer(kubeconfig)
        try:
            release_name = self._release_name(network)
            namespace = self._namespace(network)
            net_cfg = NETWORK_CONFIGS[network]

            # Get Helm release status
            try:
                release = await deployer.status(release_name, namespace)
            except HelmError:
                return LuxFleetResponse(
                    id=self._fleet_id(name, network),
                    name=name,
                    cluster_id=cluster_id,
                    network=network,
                    status=LuxFleetStatus.ERROR,
                    replicas=0,
                    namespace=namespace,
                    error="Helm release not found",
                )

            # Get pods
            pods = await deployer.get_pods(namespace, "app=luxd")
            ready_count = sum(1 for p in pods if p.ready)
            total = len(pods)

            # Get services for endpoint discovery
            services = await deployer.get_services(namespace)
            rpc_endpoint = None
            staking_endpoint = None
            for svc in services:
                for ext_ip in svc.get("external_ips", []):
                    if ext_ip:
                        for port in svc.get("ports", []):
                            if port.get("port") == net_cfg.http_port:
                                rpc_endpoint = f"http://{ext_ip}:{net_cfg.http_port}"
                            elif port.get("port") == net_cfg.staking_port:
                                staking_endpoint = f"{ext_ip}:{net_cfg.staking_port}"

            # Build node info
            nodes = []
            for i, pod in enumerate(sorted(pods, key=lambda p: p.name)):
                node_status = LuxNodeStatus.HEALTHY if pod.ready else LuxNodeStatus.UNHEALTHY
                if pod.status == "Pending":
                    node_status = LuxNodeStatus.PENDING
                elif pod.status == "Init":
                    node_status = LuxNodeStatus.INIT

                nodes.append(LuxNodeInfo(
                    pod_name=pod.name,
                    pod_index=i,
                    status=node_status,
                    http_port=net_cfg.http_port,
                    staking_port=net_cfg.staking_port,
                ))

            # Determine fleet status
            if total == 0:
                fleet_status = LuxFleetStatus.DEPLOYING
            elif ready_count == total:
                fleet_status = LuxFleetStatus.RUNNING
            elif ready_count > 0:
                fleet_status = LuxFleetStatus.DEGRADED
            else:
                fleet_status = LuxFleetStatus.ERROR

            return LuxFleetResponse(
                id=self._fleet_id(name, network),
                name=name,
                cluster_id=cluster_id,
                network=network,
                status=fleet_status,
                replicas=total,
                ready_replicas=ready_count,
                namespace=namespace,
                helm_revision=release.revision,
                rpc_endpoint=rpc_endpoint,
                staking_endpoint=staking_endpoint,
                nodes=nodes,
            )
        finally:
            deployer.cleanup_temp_files()

    async def list_fleets(
        self,
        kubeconfig: str,
        cluster_id: str,
    ) -> list[LuxFleetSummary]:
        """List all Lux fleets on a cluster."""
        deployer = await self._get_deployer(kubeconfig)
        try:
            releases = await deployer.list_releases(
                all_namespaces=True,
                filter_pattern="^luxd-",
            )

            fleets = []
            for r in releases:
                # Infer network from release name (luxd-mainnet -> mainnet)
                network_str = r.name.removeprefix("luxd-")
                try:
                    network = LuxNetwork(network_str)
                except ValueError:
                    continue

                pods = await deployer.get_pods(r.namespace, "app=luxd")
                ready = sum(1 for p in pods if p.ready)
                total = len(pods)

                if total == 0:
                    status = LuxFleetStatus.DEPLOYING
                elif ready == total:
                    status = LuxFleetStatus.RUNNING
                elif ready > 0:
                    status = LuxFleetStatus.DEGRADED
                else:
                    status = LuxFleetStatus.ERROR

                fleets.append(LuxFleetSummary(
                    id=f"{cluster_id}:{r.name}",
                    name=r.name,
                    network=network,
                    status=status,
                    replicas=total,
                    ready_replicas=ready,
                    cluster_id=cluster_id,
                    created_at=r.updated or "",
                ))

            return fleets
        finally:
            deployer.cleanup_temp_files()

    async def get_pod_logs(
        self,
        kubeconfig: str,
        network: LuxNetwork,
        pod_name: str,
        tail: int = 100,
    ) -> str:
        """Get logs from a specific pod."""
        deployer = await self._get_deployer(kubeconfig)
        try:
            namespace = self._namespace(network)
            return await deployer.get_pod_logs(pod_name, namespace, tail=tail)
        finally:
            deployer.cleanup_temp_files()

    async def rolling_restart(
        self,
        kubeconfig: str,
        network: LuxNetwork,
    ) -> list[str]:
        """Rolling restart: delete pods one at a time (OnDelete strategy)."""
        deployer = await self._get_deployer(kubeconfig)
        try:
            namespace = self._namespace(network)
            pods = await deployer.get_pods(namespace, "app=luxd")
            restarted = []

            for pod in sorted(pods, key=lambda p: p.name):
                logger.info("Rolling restart: deleting %s", pod.name)
                await deployer.delete_pod(pod.name, namespace)
                restarted.append(pod.name)
                # Wait for pod to come back ready (up to 5 min)
                for _ in range(60):
                    await asyncio.sleep(5)
                    new_pods = await deployer.get_pods(namespace, "app=luxd")
                    replaced = next((p for p in new_pods if p.name == pod.name), None)
                    if replaced and replaced.ready:
                        break

            return restarted
        finally:
            deployer.cleanup_temp_files()

    async def probe_node_health(
        self,
        kubeconfig: str,
        network: LuxNetwork,
        pod_name: str,
    ) -> dict:
        """Probe a luxd node's health via kubectl exec + wget."""
        deployer = await self._get_deployer(kubeconfig)
        try:
            namespace = self._namespace(network)
            net_cfg = NETWORK_CONFIGS[network]
            port = net_cfg.http_port

            results: dict = {}

            # Health check
            try:
                health = await deployer.exec_pod(
                    pod_name, namespace,
                    ["wget", "-qO-", f"http://localhost:{port}/ext/health"],
                )
                results["health"] = json.loads(health)
                results["healthy"] = results["health"].get("healthy", False)
            except Exception:
                results["healthy"] = False

            # Block height
            try:
                rpc_resp = await deployer.exec_pod(
                    pod_name, namespace,
                    [
                        "wget", "-qO-",
                        "--header=Content-Type: application/json",
                        f"--post-data={{\"jsonrpc\":\"2.0\",\"method\":\"eth_blockNumber\",\"params\":[],\"id\":1}}",
                        f"http://localhost:{port}/ext/bc/C/rpc",
                    ],
                )
                data = json.loads(rpc_resp)
                results["c_chain_height"] = int(data.get("result", "0x0"), 16)
            except Exception:
                results["c_chain_height"] = None

            return results
        finally:
            deployer.cleanup_temp_files()
