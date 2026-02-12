"""Kubernetes deployment target."""

import asyncio
from typing import AsyncIterator

import structlog

from bootnode.core.deploy.base import DeployTarget, ServiceStatus, ServiceType

logger = structlog.get_logger()


# Deployment name mapping for Kubernetes
DEPLOYMENT_NAMES: dict[ServiceType, str] = {
    ServiceType.API: "bootnode-api",
    ServiceType.WEB: "bootnode-web",
    ServiceType.INDEXER: "bootnode-indexer",
    ServiceType.WEBHOOK_WORKER: "bootnode-webhook-worker",
    ServiceType.BUNDLER: "bootnode-bundler",
}

# Default container ports
SERVICE_PORTS: dict[ServiceType, int] = {
    ServiceType.API: 8000,
    ServiceType.WEB: 3000,
    ServiceType.INDEXER: 8001,
    ServiceType.WEBHOOK_WORKER: 8002,
    ServiceType.BUNDLER: 8003,
}


class KubernetesDeployer(DeployTarget):
    """Deploy services to Kubernetes.

    Uses the official kubernetes python client for all operations.
    """

    def __init__(
        self,
        namespace: str = "bootnode",
        context: str | None = None,
        in_cluster: bool = False,
    ) -> None:
        self.namespace = namespace
        self.context = context
        self.in_cluster = in_cluster
        self._apps_v1 = None
        self._core_v1 = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Initialize Kubernetes clients lazily."""
        if self._initialized:
            return

        try:
            from kubernetes import client, config

            if self.in_cluster:
                config.load_incluster_config()
            elif self.context:
                config.load_kube_config(context=self.context)
            else:
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config()

            self._apps_v1 = client.AppsV1Api()
            self._core_v1 = client.CoreV1Api()
            self._initialized = True
            logger.info(
                "Kubernetes client initialized",
                namespace=self.namespace,
                context=self.context,
            )
        except Exception as e:
            logger.error("Failed to initialize Kubernetes client", error=str(e))
            raise RuntimeError("Kubernetes not available") from e

    @property
    def apps_v1(self):
        """Get AppsV1 API client."""
        self._ensure_initialized()
        return self._apps_v1

    @property
    def core_v1(self):
        """Get CoreV1 API client."""
        self._ensure_initialized()
        return self._core_v1

    def _get_deployment_name(self, service: ServiceType) -> str:
        """Get Kubernetes deployment name."""
        return DEPLOYMENT_NAMES.get(service, f"bootnode-{service.value}")

    def _get_labels(self, service: ServiceType) -> dict[str, str]:
        """Get standard labels for a service."""
        return {
            "app.kubernetes.io/name": service.value,
            "app.kubernetes.io/component": service.value,
            "app.kubernetes.io/part-of": "bootnode",
            "app.kubernetes.io/managed-by": "bootnode-deployer",
        }

    async def deploy(
        self,
        service: ServiceType,
        image: str,
        replicas: int = 1,
        env: dict[str, str] | None = None,
    ) -> bool:
        """Deploy or update a service in Kubernetes."""
        from kubernetes import client
        from kubernetes.client.rest import ApiException

        deployment_name = self._get_deployment_name(service)
        labels = self._get_labels(service)
        port = SERVICE_PORTS.get(service, 8000)

        # Build environment variables
        env_vars = []
        if env:
            for key, value in env.items():
                env_vars.append(client.V1EnvVar(name=key, value=value))

        # Build container spec
        container = client.V1Container(
            name=service.value,
            image=image,
            ports=[client.V1ContainerPort(container_port=port)],
            env=env_vars if env_vars else None,
            resources=client.V1ResourceRequirements(
                requests={"cpu": "100m", "memory": "128Mi"},
                limits={"cpu": "1000m", "memory": "512Mi"},
            ),
            liveness_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(path="/health", port=port),
                initial_delay_seconds=10,
                period_seconds=10,
            ),
            readiness_probe=client.V1Probe(
                http_get=client.V1HTTPGetAction(path="/health", port=port),
                initial_delay_seconds=5,
                period_seconds=5,
            ),
        )

        # Build deployment spec
        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(
                name=deployment_name,
                namespace=self.namespace,
                labels=labels,
            ),
            spec=client.V1DeploymentSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(match_labels=labels),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels=labels),
                    spec=client.V1PodSpec(containers=[container]),
                ),
            ),
        )

        try:
            # Try to update existing deployment
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace,
                body=deployment,
            )
            logger.info(
                "Deployment updated",
                deployment=deployment_name,
                image=image,
                replicas=replicas,
            )
        except ApiException as e:
            if e.status == 404:
                # Create new deployment
                self.apps_v1.create_namespaced_deployment(
                    namespace=self.namespace,
                    body=deployment,
                )
                logger.info(
                    "Deployment created",
                    deployment=deployment_name,
                    image=image,
                    replicas=replicas,
                )
            else:
                logger.error(
                    "Failed to deploy",
                    deployment=deployment_name,
                    error=str(e),
                )
                return False

        return True

    async def scale(self, service: ServiceType, replicas: int) -> bool:
        """Scale a deployment to the specified number of replicas."""
        from kubernetes.client.rest import ApiException

        deployment_name = self._get_deployment_name(service)

        try:
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=self.namespace,
                body={"spec": {"replicas": replicas}},
            )
            logger.info(
                "Deployment scaled",
                deployment=deployment_name,
                replicas=replicas,
            )
            return True
        except ApiException as e:
            logger.error(
                "Failed to scale",
                deployment=deployment_name,
                error=str(e),
            )
            return False

    async def status(self, service: ServiceType) -> ServiceStatus:
        """Get the current status of a deployment."""
        from kubernetes.client.rest import ApiException

        deployment_name = self._get_deployment_name(service)

        try:
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace,
            )

            status = deployment.status
            spec = deployment.spec

            # Get image from container spec
            image = None
            if spec.template.spec.containers:
                image = spec.template.spec.containers[0].image

            # Get creation timestamp
            started_at = None
            if deployment.metadata.creation_timestamp:
                started_at = deployment.metadata.creation_timestamp.isoformat()

            # Get resource metrics if available
            cpu_usage = None
            memory_usage = None
            try:
                # Try to get metrics from metrics server
                from kubernetes import client as k8s_client

                custom_api = k8s_client.CustomObjectsApi()
                metrics = custom_api.list_namespaced_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    namespace=self.namespace,
                    plural="pods",
                    label_selector=f"app.kubernetes.io/name={service.value}",
                )
                for item in metrics.get("items", []):
                    for container in item.get("containers", []):
                        usage = container.get("usage", {})
                        # Parse CPU (e.g., "100m" -> 0.1)
                        cpu = usage.get("cpu", "0")
                        if cpu.endswith("m"):
                            cpu_usage = (cpu_usage or 0) + int(cpu[:-1]) / 1000
                        elif cpu.endswith("n"):
                            cpu_usage = (cpu_usage or 0) + int(cpu[:-1]) / 1e9
                        # Parse memory (e.g., "128Mi" -> 128)
                        mem = usage.get("memory", "0")
                        if mem.endswith("Ki"):
                            memory_usage = (memory_usage or 0) + int(mem[:-2]) / 1024
                        elif mem.endswith("Mi"):
                            memory_usage = (memory_usage or 0) + int(mem[:-2])
            except Exception:
                pass

            return ServiceStatus(
                name=deployment_name,
                running=status.available_replicas is not None and status.available_replicas > 0,
                replicas=status.replicas or 0,
                ready_replicas=status.ready_replicas or 0,
                cpu_usage=round(cpu_usage, 3) if cpu_usage else None,
                memory_usage=round(memory_usage, 2) if memory_usage else None,
                image=image,
                started_at=started_at,
            )

        except ApiException as e:
            if e.status == 404:
                return ServiceStatus(
                    name=deployment_name,
                    running=False,
                    replicas=0,
                    ready_replicas=0,
                )
            logger.error(
                "Failed to get status",
                deployment=deployment_name,
                error=str(e),
            )
            raise

    async def logs(
        self,
        service: ServiceType,
        tail: int = 100,
        follow: bool = False,
    ) -> AsyncIterator[str]:
        """Stream logs from pods in a deployment."""
        from kubernetes.client.rest import ApiException

        labels = self._get_labels(service)
        label_selector = ",".join(f"{k}={v}" for k, v in labels.items())

        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=label_selector,
            )

            if not pods.items:
                return

            # Get logs from first running pod
            for pod in pods.items:
                if pod.status.phase == "Running":
                    if follow:
                        # Streaming logs
                        from kubernetes import watch

                        w = watch.Watch()
                        try:
                            for line in w.stream(
                                self.core_v1.read_namespaced_pod_log,
                                name=pod.metadata.name,
                                namespace=self.namespace,
                                tail_lines=tail,
                                follow=True,
                            ):
                                yield line
                        finally:
                            w.stop()
                    else:
                        # Static logs
                        logs = self.core_v1.read_namespaced_pod_log(
                            name=pod.metadata.name,
                            namespace=self.namespace,
                            tail_lines=tail,
                        )
                        for line in logs.splitlines():
                            yield line
                    break

        except ApiException as e:
            logger.error(
                "Failed to get logs",
                service=service.value,
                error=str(e),
            )

    async def destroy(self, service: ServiceType) -> bool:
        """Delete a deployment."""
        from kubernetes.client.rest import ApiException

        deployment_name = self._get_deployment_name(service)

        try:
            self.apps_v1.delete_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace,
            )
            logger.info("Deployment deleted", deployment=deployment_name)
            return True
        except ApiException as e:
            if e.status == 404:
                return True
            logger.error(
                "Failed to delete deployment",
                deployment=deployment_name,
                error=str(e),
            )
            return False

    async def restart(self, service: ServiceType) -> bool:
        """Restart a deployment by patching the template annotation."""
        from datetime import datetime, timezone

        from kubernetes.client.rest import ApiException

        deployment_name = self._get_deployment_name(service)

        try:
            # Patch the deployment with a new annotation to trigger rollout
            now = datetime.now(timezone.utc).isoformat()
            patch = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "bootno.de/restartedAt": now,
                            }
                        }
                    }
                }
            }

            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace,
                body=patch,
            )
            logger.info("Deployment restarted", deployment=deployment_name)
            return True
        except ApiException as e:
            logger.error(
                "Failed to restart deployment",
                deployment=deployment_name,
                error=str(e),
            )
            return False
