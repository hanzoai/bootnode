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

    def _get_k8s_client(self):
        """Get a kubernetes client using in-cluster config."""
        try:
            from kubernetes import client, config
            config.load_incluster_config()
            return client.CoreV1Api(), client.AppsV1Api()
        except Exception:
            logger.warning("Failed to load in-cluster k8s config")
            raise

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

            # Get Helm release status (optional -- fleet may be kubectl-deployed)
            helm_revision = None
            try:
                release = await deployer.status(release_name, namespace)
                helm_revision = release.revision
            except HelmError:
                pass  # Not a Helm-managed fleet, continue with kubectl

            # Get pods
            pods = await deployer.get_pods(namespace, "app=luxd")
            ready_count = sum(1 for p in pods if p.ready)
            total = len(pods)

            if total == 0 and helm_revision is None:
                return LuxFleetResponse(
                    id=self._fleet_id(name, network),
                    name=name,
                    cluster_id=cluster_id,
                    network=network,
                    status=LuxFleetStatus.ERROR,
                    replicas=0,
                    namespace=namespace,
                    error="No fleet found (no Helm release or pods)",
                )

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
                helm_revision=helm_revision,
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
        """List all Lux fleets on a cluster.

        Discovers fleets via Helm releases first, then falls back to
        direct StatefulSet discovery for fleets deployed via kubectl.
        """
        deployer = await self._get_deployer(kubeconfig)
        try:
            fleets = []
            seen_namespaces: set[str] = set()

            # 1. Try Helm releases
            try:
                releases = await deployer.list_releases(
                    all_namespaces=True,
                    filter_pattern="^luxd-",
                )
                for r in releases:
                    network_str = r.name.removeprefix("luxd-")
                    try:
                        network = LuxNetwork(network_str)
                    except ValueError:
                        continue

                    pods = await deployer.get_pods(r.namespace, "app=luxd")
                    ready = sum(1 for p in pods if p.ready)
                    total = len(pods)
                    seen_namespaces.add(r.namespace)

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
            except Exception:
                logger.debug("No Helm releases found, trying StatefulSet discovery")

            # 2. Fall back to StatefulSet discovery for kubectl-deployed fleets
            for network, cfg in NETWORK_CONFIGS.items():
                if cfg.namespace in seen_namespaces:
                    continue
                try:
                    sts_list = await deployer.get_statefulsets(namespace=cfg.namespace)
                    for sts in sts_list:
                        if sts["name"] != "luxd":
                            continue
                        total = sts["replicas"]
                        ready = sts["ready_replicas"]

                        if total == 0:
                            status = LuxFleetStatus.DEPLOYING
                        elif ready == total:
                            status = LuxFleetStatus.RUNNING
                        elif ready > 0:
                            status = LuxFleetStatus.DEGRADED
                        else:
                            status = LuxFleetStatus.ERROR

                        fleets.append(LuxFleetSummary(
                            id=f"{cluster_id}:luxd-{network.value}",
                            name=f"luxd-{network.value}",
                            network=network,
                            status=status,
                            replicas=total,
                            ready_replicas=ready,
                            cluster_id=cluster_id,
                            created_at=sts.get("created_at", ""),
                        ))
                except Exception:
                    continue

            return fleets
        finally:
            deployer.cleanup_temp_files()

    async def list_fleets_incluster(
        self,
        cluster_id: str,
    ) -> list[LuxFleetSummary]:
        """List all Lux fleets using in-cluster k8s access.

        Discovers fleets via StatefulSet discovery in known namespaces.
        """
        core_v1, apps_v1 = self._get_k8s_client()
        fleets = []

        for network, cfg in NETWORK_CONFIGS.items():
            try:
                sts_list = apps_v1.list_namespaced_stateful_set(
                    namespace=cfg.namespace,
                    label_selector="app=luxd",
                )
                for sts in sts_list.items:
                    total = sts.spec.replicas or 0
                    ready = sts.status.ready_replicas or 0

                    if total == 0:
                        fleet_status = LuxFleetStatus.DEPLOYING
                    elif ready == total:
                        fleet_status = LuxFleetStatus.RUNNING
                    elif ready > 0:
                        fleet_status = LuxFleetStatus.DEGRADED
                    else:
                        fleet_status = LuxFleetStatus.ERROR

                    created = ""
                    if sts.metadata.creation_timestamp:
                        created = sts.metadata.creation_timestamp.isoformat()

                    fleets.append(LuxFleetSummary(
                        id=f"{cluster_id}:luxd-{network.value}",
                        name=f"luxd-{network.value}",
                        network=network,
                        status=fleet_status,
                        replicas=total,
                        ready_replicas=ready,
                        cluster_id=cluster_id,
                        created_at=created,
                    ))

                # If no statefulset found, check for pods directly
                if not sts_list.items:
                    pods = core_v1.list_namespaced_pod(
                        namespace=cfg.namespace,
                        label_selector="app=luxd",
                    )
                    if pods.items:
                        total = len(pods.items)
                        ready = sum(
                            1 for p in pods.items
                            if p.status.phase == "Running"
                            and p.status.container_statuses
                            and all(c.ready for c in p.status.container_statuses)
                        )
                        fleet_status = LuxFleetStatus.RUNNING if ready == total else (
                            LuxFleetStatus.DEGRADED if ready > 0 else LuxFleetStatus.ERROR
                        )
                        fleets.append(LuxFleetSummary(
                            id=f"{cluster_id}:luxd-{network.value}",
                            name=f"luxd-{network.value}",
                            network=network,
                            status=fleet_status,
                            replicas=total,
                            ready_replicas=ready,
                            cluster_id=cluster_id,
                            created_at="",
                        ))
            except Exception as e:
                logger.warning("Failed to list fleet in %s: %s", cfg.namespace, e)
                continue

        return fleets

    async def get_status_incluster(
        self,
        name: str,
        network: LuxNetwork,
        cluster_id: str,
    ) -> LuxFleetResponse:
        """Get full fleet status using in-cluster k8s access."""
        core_v1, apps_v1 = self._get_k8s_client()
        namespace = self._namespace(network)
        net_cfg = NETWORK_CONFIGS[network]

        # Get pods
        pod_list = core_v1.list_namespaced_pod(
            namespace=namespace,
            label_selector="app=luxd",
        )
        total = len(pod_list.items)

        if total == 0:
            return LuxFleetResponse(
                id=self._fleet_id(name, network),
                name=name,
                cluster_id=cluster_id,
                network=network,
                status=LuxFleetStatus.ERROR,
                replicas=0,
                namespace=namespace,
                error="No pods found",
            )

        ready_count = 0
        for p in pod_list.items:
            if (p.status.phase == "Running"
                    and p.status.container_statuses
                    and all(c.ready for c in p.status.container_statuses)):
                ready_count += 1

        # Get services for endpoint discovery
        svc_list = core_v1.list_namespaced_service(namespace=namespace)
        rpc_endpoint = None
        staking_endpoint = None
        for svc in svc_list.items:
            if svc.status.load_balancer and svc.status.load_balancer.ingress:
                for ing in svc.status.load_balancer.ingress:
                    ext_ip = ing.ip
                    if ext_ip and svc.spec.ports:
                        for port in svc.spec.ports:
                            if port.port == net_cfg.http_port:
                                rpc_endpoint = f"http://{ext_ip}:{net_cfg.http_port}"
                            elif port.port == net_cfg.staking_port:
                                staking_endpoint = f"{ext_ip}:{net_cfg.staking_port}"

        # Build node info
        nodes = []
        sorted_pods = sorted(pod_list.items, key=lambda p: p.metadata.name)
        for i, pod in enumerate(sorted_pods):
            pod_ready = (
                pod.status.phase == "Running"
                and pod.status.container_statuses
                and all(c.ready for c in pod.status.container_statuses)
            )
            if pod_ready:
                node_status = LuxNodeStatus.HEALTHY
            elif pod.status.phase == "Pending":
                node_status = LuxNodeStatus.PENDING
            else:
                node_status = LuxNodeStatus.UNHEALTHY

            nodes.append(LuxNodeInfo(
                pod_name=pod.metadata.name,
                pod_index=i,
                status=node_status,
                http_port=net_cfg.http_port,
                staking_port=net_cfg.staking_port,
            ))

        # Determine fleet status
        if ready_count == total:
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
            rpc_endpoint=rpc_endpoint,
            staking_endpoint=staking_endpoint,
            nodes=nodes,
        )

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
