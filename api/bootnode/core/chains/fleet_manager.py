"""Fleet manager — blockchain node fleet lifecycle via K8s CRDs.

Supports two CRD backends:
  1. Bootnode Cluster CRDs (bootnode.dev/v1alpha1) — generic, any chain
  2. Lux Operator LuxNetwork CRDs (lux.network/v1alpha1) — native lux validators

The manager tries bootnode CRDs first, then falls back to lux-operator CRDs
for Lux chain discovery. This allows managing both bootnode-provisioned fleets
and pre-existing lux-operator-managed validators from the same API.
"""

import logging
from typing import Optional

from bootnode.core.chains.fleet_models import (
    CRD_GROUP,
    CRD_PLURAL,
    CRD_VERSION,
    CHAIN_NETWORKS,
    FleetCreate,
    FleetResponse,
    FleetStatus,
    FleetSummary,
    FleetUpdate,
    ImageConfig,
    NodeInfo,
    NodeStatus,
    crd_status_to_fleet_response,
    fleet_create_to_crd,
    fleet_update_to_crd_patch,
    get_network_config,
)

logger = logging.getLogger(__name__)

# Lux Operator CRD constants
LUX_CRD_GROUP = "lux.network"
LUX_CRD_VERSION = "v1alpha1"
LUX_CRD_PLURAL = "luxnetworks"


class FleetManager:
    """Manages blockchain node fleet lifecycle via Cluster CRDs.

    Works for any chain — lux, avalanche, ethereum, bitcoin, etc.
    For Lux specifically, also discovers lux-operator-managed validators.
    """

    def _cr_name(self, chain: str, network: str) -> str:
        return f"{chain}d-{network}"

    def _namespace(self, chain: str, network: str) -> str:
        return get_network_config(chain, network).namespace

    def _fleet_id(self, cluster_id: str, chain: str, network: str) -> str:
        return f"{cluster_id}:{self._cr_name(chain, network)}"

    def _get_k8s_clients(self, kubeconfig_data: Optional[str] = None):
        """Get K8s API clients.

        If kubeconfig_data is provided, loads config from that YAML string.
        Otherwise uses in-cluster config.
        """
        from kubernetes import client, config
        import tempfile
        import os

        if kubeconfig_data:
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".kubeconfig", delete=False
            )
            tmp.write(kubeconfig_data)
            tmp.flush()
            tmp.close()
            config.load_kube_config(config_file=tmp.name)
            os.unlink(tmp.name)
        else:
            config.load_incluster_config()

        return client.CustomObjectsApi(), client.CoreV1Api()

    # ---- Lux Operator native discovery ----

    def _luxnetwork_to_fleet_response(
        self, cr: dict, cluster_id: str, network: str,
    ) -> FleetResponse:
        """Convert a LuxNetwork CR into a FleetResponse."""
        spec = cr.get("spec", {})
        status = cr.get("status", {})
        metadata = cr.get("metadata", {})

        phase = status.get("phase", "Pending")
        status_map = {
            "Pending": FleetStatus.PENDING,
            "Creating": FleetStatus.DEPLOYING,
            "Bootstrapping": FleetStatus.DEPLOYING,
            "Running": FleetStatus.RUNNING,
            "Degraded": FleetStatus.DEGRADED,
        }
        fleet_status = status_map.get(phase, FleetStatus.ERROR)

        # Build node list from nodeStatuses (dict of pod_name -> status)
        node_statuses = status.get("nodeStatuses", {})
        external_ips = status.get("externalIps", {})
        nodes = []
        for i, (pod_name, ns) in enumerate(sorted(node_statuses.items())):
            if isinstance(ns, str):
                # Sometimes nodeStatuses is just a list of strings
                nodes.append(NodeInfo(
                    pod_name=ns, pod_index=i,
                    status=NodeStatus.HEALTHY, healthy=True,
                    external_ip=external_ips.get(ns),
                ))
                continue
            nodes.append(NodeInfo(
                pod_name=pod_name,
                pod_index=i,
                node_id=ns.get("nodeId"),
                status=NodeStatus.HEALTHY if ns.get("healthy") else NodeStatus.UNHEALTHY,
                external_ip=ns.get("externalIp") or external_ips.get(pod_name),
                healthy=ns.get("healthy", False),
                bootstrapped=ns.get("bootstrapped", False),
                peers=ns.get("connectedPeers"),
                extra={
                    k: v for k, v in ns.items()
                    if k not in ("healthy", "bootstrapped", "connectedPeers",
                                 "nodeId", "externalIp")
                },
            ))

        img_spec = spec.get("image", {})
        image = ImageConfig(
            repository=img_spec.get("repository", "ghcr.io/luxfi/node"),
            tag=img_spec.get("tag", "latest"),
            pull_policy=img_spec.get("pullPolicy", "IfNotPresent"),
        ) if img_spec else None

        net_cfg = get_network_config("lux", network)
        # RPC endpoint from first external IP
        rpc_endpoint = None
        if external_ips:
            first_ip = next(iter(external_ips.values()))
            rpc_endpoint = f"http://{first_ip}:{net_cfg.http_port}/ext/bc/C/rpc"

        chain_statuses = status.get("chainStatuses", {})

        return FleetResponse(
            id=f"{cluster_id}:luxd-{network}",
            name=metadata.get("name", f"luxd-{network}"),
            cluster_id=cluster_id,
            chain="lux",
            network=network,
            status=fleet_status,
            replicas=status.get("totalValidators", spec.get("validators", 0)),
            ready_replicas=status.get("readyValidators", 0),
            image=image,
            namespace=metadata.get("namespace", ""),
            rpc_endpoint=rpc_endpoint,
            nodes=nodes,
            created_at=metadata.get("creationTimestamp", ""),
            updated_at=None,
            error="; ".join(
                r.get("message", "")
                for r in status.get("degradedReasons", [])
                if r.get("message")
            ) or None,
        )

    def _luxnetwork_to_fleet_summary(
        self, cr: dict, cluster_id: str, network: str,
    ) -> FleetSummary:
        """Convert a LuxNetwork CR into a FleetSummary."""
        spec = cr.get("spec", {})
        status = cr.get("status", {})
        metadata = cr.get("metadata", {})

        phase = status.get("phase", "Pending")
        status_map = {
            "Pending": FleetStatus.PENDING,
            "Creating": FleetStatus.DEPLOYING,
            "Bootstrapping": FleetStatus.DEPLOYING,
            "Running": FleetStatus.RUNNING,
            "Degraded": FleetStatus.DEGRADED,
        }

        return FleetSummary(
            id=f"{cluster_id}:luxd-{network}",
            name=metadata.get("name", f"luxd-{network}"),
            chain="lux",
            network=network,
            status=status_map.get(phase, FleetStatus.ERROR),
            replicas=status.get("totalValidators", spec.get("validators", 0)),
            ready_replicas=status.get("readyValidators", 0),
            cluster_id=cluster_id,
            created_at=metadata.get("creationTimestamp", ""),
        )

    async def _list_lux_native_fleets(
        self, custom_api, cluster_id: str,
    ) -> list[FleetSummary]:
        """Discover lux-operator managed validators via LuxNetwork CRDs."""
        fleets = []
        lux_nets = CHAIN_NETWORKS.get("lux", {})

        for network_name, cfg in lux_nets.items():
            try:
                result = custom_api.list_namespaced_custom_object(
                    group=LUX_CRD_GROUP,
                    version=LUX_CRD_VERSION,
                    namespace=cfg.namespace,
                    plural=LUX_CRD_PLURAL,
                )
                for cr in result.get("items", []):
                    fleets.append(
                        self._luxnetwork_to_fleet_summary(cr, cluster_id, network_name)
                    )
            except Exception as e:
                logger.debug("No LuxNetwork CRs in %s: %s", cfg.namespace, e)
                continue

        return fleets

    async def _get_lux_native_status(
        self, custom_api, chain: str, network: str, cluster_id: str,
    ) -> Optional[FleetResponse]:
        """Get status from a LuxNetwork CR."""
        if chain != "lux":
            return None

        namespace = self._namespace(chain, network)
        try:
            # The LuxNetwork CR is typically named "luxd" in each namespace
            cr = custom_api.get_namespaced_custom_object(
                group=LUX_CRD_GROUP,
                version=LUX_CRD_VERSION,
                namespace=namespace,
                plural=LUX_CRD_PLURAL,
                name="luxd",
            )
            return self._luxnetwork_to_fleet_response(cr, cluster_id, network)
        except Exception as e:
            logger.debug("No LuxNetwork 'luxd' in %s: %s", namespace, e)
            return None

    # ---- Fleet lifecycle ----

    async def create(
        self,
        kubeconfig: str,
        params: FleetCreate,
    ) -> FleetResponse:
        """Create a new node fleet by creating a Cluster CR."""
        namespace = self._namespace(params.chain, params.network)

        logger.info(
            "Creating fleet: chain=%s network=%s namespace=%s replicas=%d",
            params.chain, params.network, namespace, params.replicas,
        )

        try:
            custom_api, core_api = self._get_k8s_clients(kubeconfig)
            body = fleet_create_to_crd(params)

            # Ensure namespace exists
            from kubernetes import client
            try:
                core_api.read_namespace(namespace)
            except client.ApiException as e:
                if e.status == 404:
                    core_api.create_namespace(
                        client.V1Namespace(
                            metadata=client.V1ObjectMeta(name=namespace)
                        )
                    )

            custom_api.create_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural=CRD_PLURAL,
                body=body,
            )

            return FleetResponse(
                id=self._fleet_id(params.cluster_id, params.chain, params.network),
                name=self._cr_name(params.chain, params.network),
                cluster_id=params.cluster_id,
                chain=params.chain,
                network=params.network,
                status=FleetStatus.DEPLOYING,
                replicas=params.replicas,
                namespace=namespace,
                image=params.image,
            )
        except Exception as e:
            logger.error("Fleet creation failed: %s", e)
            return FleetResponse(
                id=self._fleet_id(params.cluster_id, params.chain, params.network),
                name=self._cr_name(params.chain, params.network),
                cluster_id=params.cluster_id,
                chain=params.chain,
                network=params.network,
                status=FleetStatus.ERROR,
                replicas=params.replicas,
                namespace=namespace,
                error=str(e),
            )

    async def update(
        self,
        kubeconfig: str,
        chain: str,
        network: str,
        cluster_id: str,
        params: FleetUpdate,
    ) -> FleetResponse:
        """Update an existing fleet by patching the CR.

        Tries bootnode CRD first, falls back to LuxNetwork CRD for scale ops.
        """
        namespace = self._namespace(chain, network)
        cr_name = self._cr_name(chain, network)

        logger.info("Updating fleet: cr=%s namespace=%s", cr_name, namespace)

        try:
            custom_api, _ = self._get_k8s_clients(kubeconfig)
            patch = fleet_update_to_crd_patch(params)

            if patch:
                try:
                    custom_api.patch_namespaced_custom_object(
                        group=CRD_GROUP, version=CRD_VERSION,
                        namespace=namespace, plural=CRD_PLURAL,
                        name=cr_name, body=patch,
                    )
                except Exception:
                    # Try LuxNetwork CRD for scale operations
                    if chain == "lux" and params.replicas is not None:
                        lux_patch = {"spec": {"validators": params.replicas}}
                        custom_api.patch_namespaced_custom_object(
                            group=LUX_CRD_GROUP, version=LUX_CRD_VERSION,
                            namespace=namespace, plural=LUX_CRD_PLURAL,
                            name="luxd", body=lux_patch,
                        )
                    else:
                        raise

            # Try bootnode CRD status first, then lux native
            try:
                cr = custom_api.get_namespaced_custom_object(
                    group=CRD_GROUP, version=CRD_VERSION,
                    namespace=namespace, plural=CRD_PLURAL, name=cr_name,
                )
                resp = crd_status_to_fleet_response(cr, cluster_id)
            except Exception:
                native = await self._get_lux_native_status(
                    custom_api, chain, network, cluster_id
                )
                if native:
                    resp = native
                else:
                    raise

            if patch:
                resp.status = FleetStatus.UPDATING
            return resp

        except Exception as e:
            logger.error("Fleet update failed: %s", e)
            return FleetResponse(
                id=self._fleet_id(cluster_id, chain, network),
                name=cr_name,
                cluster_id=cluster_id,
                chain=chain,
                network=network,
                status=FleetStatus.ERROR,
                replicas=params.replicas or 0,
                namespace=namespace,
                error=str(e),
            )

    async def scale(
        self,
        kubeconfig: str,
        chain: str,
        network: str,
        cluster_id: str,
        replicas: int,
    ) -> FleetResponse:
        """Scale a fleet's replica count."""
        return await self.update(
            kubeconfig=kubeconfig,
            chain=chain,
            network=network,
            cluster_id=cluster_id,
            params=FleetUpdate(replicas=replicas),
        )

    async def destroy(
        self,
        kubeconfig: str,
        chain: str,
        network: str,
    ) -> bool:
        """Destroy a fleet by deleting the Cluster CR. PVCs persist."""
        namespace = self._namespace(chain, network)
        cr_name = self._cr_name(chain, network)

        try:
            custom_api, _ = self._get_k8s_clients(kubeconfig)
            custom_api.delete_namespaced_custom_object(
                group=CRD_GROUP, version=CRD_VERSION,
                namespace=namespace, plural=CRD_PLURAL, name=cr_name,
            )
            return True
        except Exception as e:
            logger.error("Fleet destruction failed: %s", e)
            return False

    async def get_status(
        self,
        kubeconfig: str,
        chain: str,
        network: str,
        cluster_id: str,
    ) -> FleetResponse:
        """Get full status of a fleet.

        Tries bootnode Cluster CRD first, then falls back to
        lux-operator LuxNetwork CRD for native validator discovery.
        """
        namespace = self._namespace(chain, network)
        cr_name = self._cr_name(chain, network)

        try:
            custom_api, _ = self._get_k8s_clients(kubeconfig)

            # Try bootnode CRD first
            try:
                cr = custom_api.get_namespaced_custom_object(
                    group=CRD_GROUP, version=CRD_VERSION,
                    namespace=namespace, plural=CRD_PLURAL, name=cr_name,
                )
                return crd_status_to_fleet_response(cr, cluster_id)
            except Exception:
                pass

            # Fall back to lux-operator CRD
            native = await self._get_lux_native_status(
                custom_api, chain, network, cluster_id
            )
            if native:
                return native

            return FleetResponse(
                id=self._fleet_id(cluster_id, chain, network),
                name=cr_name,
                cluster_id=cluster_id,
                chain=chain,
                network=network,
                status=FleetStatus.ERROR,
                replicas=0,
                namespace=namespace,
                error=f"No fleet CRD found in {namespace}",
            )

        except Exception as e:
            logger.error("Fleet status read failed: %s", e)
            return FleetResponse(
                id=self._fleet_id(cluster_id, chain, network),
                name=cr_name,
                cluster_id=cluster_id,
                chain=chain,
                network=network,
                status=FleetStatus.ERROR,
                replicas=0,
                namespace=namespace,
                error=str(e),
            )

    async def list_fleets(
        self,
        kubeconfig: Optional[str],
        cluster_id: str,
        chain: Optional[str] = None,
    ) -> list[FleetSummary]:
        """List node fleets across chains/networks.

        Discovers fleets from both bootnode Cluster CRDs and
        lux-operator LuxNetwork CRDs.
        """
        custom_api, _ = self._get_k8s_clients(kubeconfig)
        fleets: list[FleetSummary] = []
        seen_ids: set[str] = set()

        chains_to_check = {chain: CHAIN_NETWORKS[chain]} if chain else CHAIN_NETWORKS

        # 1. Try bootnode Cluster CRDs
        for chain_name, networks in chains_to_check.items():
            for network_name, cfg in networks.items():
                try:
                    result = custom_api.list_namespaced_custom_object(
                        group=CRD_GROUP, version=CRD_VERSION,
                        namespace=cfg.namespace, plural=CRD_PLURAL,
                    )
                    for cr in result.get("items", []):
                        status = cr.get("status", {})
                        spec = cr.get("spec", {})
                        phase = status.get("phase", "Pending")
                        metadata = cr.get("metadata", {})

                        status_map = {
                            "Running": FleetStatus.RUNNING,
                            "Degraded": FleetStatus.DEGRADED,
                            "Creating": FleetStatus.DEPLOYING,
                            "Bootstrapping": FleetStatus.DEPLOYING,
                        }
                        fleet_status = status_map.get(phase, FleetStatus.PENDING)
                        fleet_id = f"{cluster_id}:{metadata.get('name', '')}"

                        fleets.append(FleetSummary(
                            id=fleet_id,
                            name=metadata.get("name", ""),
                            chain=spec.get("chain", chain_name),
                            network=spec.get("network", network_name),
                            status=fleet_status,
                            replicas=status.get("totalNodes", spec.get("replicas", 0)),
                            ready_replicas=status.get("readyNodes", 0),
                            cluster_id=cluster_id,
                            created_at=metadata.get("creationTimestamp", ""),
                        ))
                        seen_ids.add(fleet_id)
                except Exception as e:
                    logger.debug("No bootnode CRDs in %s: %s", cfg.namespace, e)
                    continue

        # 2. Try lux-operator LuxNetwork CRDs (only for lux chain)
        if chain is None or chain == "lux":
            try:
                lux_fleets = await self._list_lux_native_fleets(custom_api, cluster_id)
                for f in lux_fleets:
                    if f.id not in seen_ids:
                        fleets.append(f)
                        seen_ids.add(f.id)
            except Exception as e:
                logger.debug("Lux native fleet discovery failed: %s", e)

        return fleets

    async def get_pod_logs(
        self,
        kubeconfig: str,
        chain: str,
        network: str,
        pod_name: str,
        tail: int = 100,
    ) -> str:
        """Get logs from a specific pod."""
        _, core_api = self._get_k8s_clients(kubeconfig)
        namespace = self._namespace(chain, network)
        return core_api.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail,
        )

    async def restart(
        self,
        kubeconfig: str,
        chain: str,
        network: str,
    ) -> list[str]:
        """Trigger a rolling restart.

        For bootnode CRDs: annotates the CR.
        For lux-operator CRDs: annotates the LuxNetwork CR.
        """
        namespace = self._namespace(chain, network)
        cr_name = self._cr_name(chain, network)
        custom_api, _ = self._get_k8s_clients(kubeconfig)

        from datetime import datetime
        restart_annotation = datetime.utcnow().isoformat() + "Z"

        # Try bootnode CRD first
        try:
            patch = {
                "metadata": {
                    "annotations": {
                        "bootnode.dev/restart-at": restart_annotation,
                    }
                }
            }
            custom_api.patch_namespaced_custom_object(
                group=CRD_GROUP, version=CRD_VERSION,
                namespace=namespace, plural=CRD_PLURAL,
                name=cr_name, body=patch,
            )
            cr = custom_api.get_namespaced_custom_object(
                group=CRD_GROUP, version=CRD_VERSION,
                namespace=namespace, plural=CRD_PLURAL, name=cr_name,
            )
            return [
                n.get("podName", f"node-{i}")
                for i, n in enumerate(cr.get("status", {}).get("nodes", []))
            ]
        except Exception:
            pass

        # Fall back to lux-operator CRD
        if chain == "lux":
            try:
                patch = {
                    "metadata": {
                        "annotations": {
                            "lux.network/restart-at": restart_annotation,
                        }
                    }
                }
                custom_api.patch_namespaced_custom_object(
                    group=LUX_CRD_GROUP, version=LUX_CRD_VERSION,
                    namespace=namespace, plural=LUX_CRD_PLURAL,
                    name="luxd", body=patch,
                )
                cr = custom_api.get_namespaced_custom_object(
                    group=LUX_CRD_GROUP, version=LUX_CRD_VERSION,
                    namespace=namespace, plural=LUX_CRD_PLURAL,
                    name="luxd",
                )
                return list(cr.get("status", {}).get("nodeStatuses", {}).keys())
            except Exception as e:
                logger.error("Restart via lux-operator failed: %s", e)
                raise

        raise RuntimeError(f"No fleet CRD found for {chain}-{network}")

    async def probe_node(
        self,
        kubeconfig: str,
        chain: str,
        network: str,
        pod_name: str,
    ) -> dict:
        """Get a node's health from CR status."""
        namespace = self._namespace(chain, network)
        cr_name = self._cr_name(chain, network)
        custom_api, _ = self._get_k8s_clients(kubeconfig)

        # Try bootnode CRD first
        try:
            cr = custom_api.get_namespaced_custom_object(
                group=CRD_GROUP, version=CRD_VERSION,
                namespace=namespace, plural=CRD_PLURAL, name=cr_name,
            )
            for node in cr.get("status", {}).get("nodes", []):
                if node.get("podName") == pod_name:
                    return {
                        "healthy": node.get("healthy", False),
                        "bootstrapped": node.get("bootstrapped", False),
                        "node_id": node.get("nodeId"),
                        "connected_peers": node.get("connectedPeers"),
                        "extra": node.get("extra", {}),
                    }
        except Exception:
            pass

        # Fall back to lux-operator CRD
        if chain == "lux":
            try:
                cr = custom_api.get_namespaced_custom_object(
                    group=LUX_CRD_GROUP, version=LUX_CRD_VERSION,
                    namespace=namespace, plural=LUX_CRD_PLURAL,
                    name="luxd",
                )
                node_statuses = cr.get("status", {}).get("nodeStatuses", {})
                ns = node_statuses.get(pod_name)
                if ns and isinstance(ns, dict):
                    return {
                        "healthy": ns.get("healthy", False),
                        "bootstrapped": ns.get("bootstrapped", False),
                        "node_id": ns.get("nodeId"),
                        "connected_peers": ns.get("connectedPeers"),
                        "extra": {
                            k: v for k, v in ns.items()
                            if k not in ("healthy", "bootstrapped",
                                         "connectedPeers", "nodeId", "externalIp")
                        },
                    }
            except Exception as e:
                logger.debug("Lux native probe failed: %s", e)

        return {"healthy": False, "error": f"Pod {pod_name} not found in fleet status"}
