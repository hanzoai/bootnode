"""Helm CLI deployer for Lux validator fleets.

Wraps the helm and kubectl CLIs via asyncio subprocess for deploying
Helm releases to remote DOKS clusters. NOT a DeployTarget subclass --
different interface (Helm release-oriented, not ServiceType-oriented).
"""

import asyncio
import json
import logging
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


class HelmReleaseStatus(str, Enum):
    DEPLOYED = "deployed"
    FAILED = "failed"
    PENDING_INSTALL = "pending-install"
    PENDING_UPGRADE = "pending-upgrade"
    PENDING_ROLLBACK = "pending-rollback"
    SUPERSEDED = "superseded"
    UNINSTALLED = "uninstalled"
    UNINSTALLING = "uninstalling"
    UNKNOWN = "unknown"


class HelmError(Exception):
    """Raised when a helm/kubectl command fails."""

    def __init__(self, message: str, stderr: str = "", returncode: int = 1):
        super().__init__(message)
        self.stderr = stderr
        self.returncode = returncode


@dataclass
class HelmRelease:
    name: str
    namespace: str
    revision: int
    status: HelmReleaseStatus
    chart: str = ""
    app_version: str = ""
    updated: str = ""


@dataclass
class PodInfo:
    name: str
    ready: bool
    status: str
    restarts: int = 0
    node: str = ""
    ip: str = ""
    age: str = ""


@dataclass
class HelmDeployer:
    """Deploys Helm charts to K8s clusters via CLI.

    Each instance is bound to a specific kubeconfig (cluster).
    Create per-request via LuxFleetManager._get_deployer().
    """

    chart_path: Path
    kubeconfig_path: Optional[Path] = None
    kube_context: Optional[str] = None
    helm_binary: str = "helm"
    kubectl_binary: str = "kubectl"
    _locks: dict = field(default_factory=dict, repr=False)

    def _get_lock(self, release_name: str) -> asyncio.Lock:
        if release_name not in self._locks:
            self._locks[release_name] = asyncio.Lock()
        return self._locks[release_name]

    def _base_helm_args(self) -> list[str]:
        args = [self.helm_binary]
        if self.kubeconfig_path:
            args += ["--kubeconfig", str(self.kubeconfig_path)]
        if self.kube_context:
            args += ["--kube-context", self.kube_context]
        return args

    def _base_kubectl_args(self) -> list[str]:
        args = [self.kubectl_binary]
        if self.kubeconfig_path:
            args += ["--kubeconfig", str(self.kubeconfig_path)]
        if self.kube_context:
            args += ["--context", self.kube_context]
        return args

    async def _run(self, args: list[str], timeout: int = 300) -> str:
        logger.debug("Running: %s", " ".join(args))
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise HelmError(f"Command timed out after {timeout}s: {' '.join(args[:3])}")

        out = stdout.decode().strip()
        err = stderr.decode().strip()

        if proc.returncode != 0:
            raise HelmError(
                f"Command failed (rc={proc.returncode}): {err or out}",
                stderr=err,
                returncode=proc.returncode,
            )
        return out

    def _write_values_file(self, values: dict) -> Path:
        """Write a values dict to a temp YAML file for helm -f.

        Temp files are tracked and cleaned up via cleanup_temp_files().
        """
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", prefix="helm-values-", delete=False
        )
        yaml.safe_dump(values, tmp, default_flow_style=False)
        tmp.flush()
        tmp.close()
        path = Path(tmp.name)
        if not hasattr(self, "_temp_files"):
            self._temp_files: list[Path] = []
        self._temp_files.append(path)
        return path

    def cleanup_temp_files(self) -> None:
        """Remove all temp files created by this deployer."""
        for f in getattr(self, "_temp_files", []):
            try:
                f.unlink(missing_ok=True)
            except OSError:
                pass
        self._temp_files = []

    # ---- Helm operations ----

    async def install(
        self,
        release_name: str,
        namespace: str,
        values: dict | None = None,
        values_files: list[Path] | None = None,
        wait: bool = False,
        create_namespace: bool = True,
        timeout: int = 600,
    ) -> HelmRelease:
        """helm install."""
        async with self._get_lock(release_name):
            args = self._base_helm_args() + [
                "upgrade", "--install", release_name, str(self.chart_path),
                "--namespace", namespace,
                "--output", "json",
            ]
            if create_namespace:
                args.append("--create-namespace")
            if wait:
                args += ["--wait", "--timeout", f"{timeout}s"]

            # Network-specific values files first (lower priority)
            for vf in (values_files or []):
                args += ["-f", str(vf)]

            # Computed values override (highest priority)
            if values:
                vf_path = self._write_values_file(values)
                args += ["-f", str(vf_path)]

            out = await self._run(args, timeout=timeout + 30)

            try:
                data = json.loads(out)
                info = data.get("info", {})
                return HelmRelease(
                    name=release_name,
                    namespace=namespace,
                    revision=data.get("version", 1),
                    status=HelmReleaseStatus(info.get("status", "unknown")),
                    chart=data.get("chart", {}).get("metadata", {}).get("name", ""),
                    app_version=data.get("chart", {}).get("metadata", {}).get("appVersion", ""),
                    updated=info.get("last_deployed", ""),
                )
            except (json.JSONDecodeError, KeyError):
                # Fallback: command succeeded but output wasn't JSON
                return HelmRelease(
                    name=release_name,
                    namespace=namespace,
                    revision=1,
                    status=HelmReleaseStatus.DEPLOYED,
                )

    async def upgrade(
        self,
        release_name: str,
        namespace: str,
        values: dict | None = None,
        values_files: list[Path] | None = None,
        reuse_values: bool = True,
        wait: bool = False,
        timeout: int = 600,
    ) -> HelmRelease:
        """helm upgrade (existing release)."""
        async with self._get_lock(release_name):
            args = self._base_helm_args() + [
                "upgrade", release_name, str(self.chart_path),
                "--namespace", namespace,
                "--output", "json",
            ]
            if reuse_values:
                args.append("--reuse-values")
            if wait:
                args += ["--wait", "--timeout", f"{timeout}s"]

            for vf in (values_files or []):
                args += ["-f", str(vf)]

            if values:
                vf_path = self._write_values_file(values)
                args += ["-f", str(vf_path)]

            out = await self._run(args, timeout=timeout + 30)

            try:
                data = json.loads(out)
                info = data.get("info", {})
                return HelmRelease(
                    name=release_name,
                    namespace=namespace,
                    revision=data.get("version", 1),
                    status=HelmReleaseStatus(info.get("status", "unknown")),
                    updated=info.get("last_deployed", ""),
                )
            except (json.JSONDecodeError, KeyError):
                return HelmRelease(
                    name=release_name,
                    namespace=namespace,
                    revision=1,
                    status=HelmReleaseStatus.DEPLOYED,
                )

    async def uninstall(self, release_name: str, namespace: str) -> bool:
        """helm uninstall."""
        async with self._get_lock(release_name):
            args = self._base_helm_args() + [
                "uninstall", release_name,
                "--namespace", namespace,
            ]
            try:
                await self._run(args)
                return True
            except HelmError as e:
                if "not found" in e.stderr.lower():
                    return True
                raise

    async def rollback(
        self, release_name: str, namespace: str, revision: int = 0
    ) -> HelmRelease:
        """helm rollback (0 = previous revision)."""
        async with self._get_lock(release_name):
            args = self._base_helm_args() + [
                "rollback", release_name, str(revision),
                "--namespace", namespace,
            ]
            await self._run(args)
            return await self.status(release_name, namespace)

    async def status(self, release_name: str, namespace: str) -> HelmRelease:
        """helm status."""
        args = self._base_helm_args() + [
            "status", release_name,
            "--namespace", namespace,
            "--output", "json",
        ]
        out = await self._run(args)
        data = json.loads(out)
        info = data.get("info", {})
        return HelmRelease(
            name=data.get("name", release_name),
            namespace=namespace,
            revision=data.get("version", 0),
            status=HelmReleaseStatus(info.get("status", "unknown")),
            updated=info.get("last_deployed", ""),
        )

    async def list_releases(
        self,
        namespace: str = "",
        all_namespaces: bool = False,
        filter_pattern: str = "",
    ) -> list[HelmRelease]:
        """helm list."""
        args = self._base_helm_args() + ["list", "--output", "json"]
        if all_namespaces:
            args.append("--all-namespaces")
        elif namespace:
            args += ["--namespace", namespace]
        if filter_pattern:
            args += ["--filter", filter_pattern]

        out = await self._run(args)
        releases = []
        for r in json.loads(out or "[]"):
            releases.append(HelmRelease(
                name=r.get("name", ""),
                namespace=r.get("namespace", ""),
                revision=int(r.get("revision", "0")),
                status=HelmReleaseStatus(r.get("status", "unknown")),
                chart=r.get("chart", ""),
                app_version=r.get("app_version", ""),
                updated=r.get("updated", ""),
            ))
        return releases

    # ---- Kubectl operations ----

    async def get_pods(
        self, namespace: str, label_selector: str = ""
    ) -> list[PodInfo]:
        """kubectl get pods."""
        args = self._base_kubectl_args() + [
            "get", "pods",
            "--namespace", namespace,
            "--output", "json",
        ]
        if label_selector:
            args += ["-l", label_selector]

        out = await self._run(args)
        data = json.loads(out)
        pods = []
        for item in data.get("items", []):
            meta = item.get("metadata", {})
            status = item.get("status", {})
            conditions = {c["type"]: c["status"] for c in status.get("conditions", [])}
            container_statuses = status.get("containerStatuses", [])
            restarts = sum(cs.get("restartCount", 0) for cs in container_statuses)

            pods.append(PodInfo(
                name=meta.get("name", ""),
                ready=conditions.get("Ready") == "True",
                status=status.get("phase", "Unknown"),
                restarts=restarts,
                node=item.get("spec", {}).get("nodeName", ""),
                ip=status.get("podIP", ""),
            ))
        return pods

    async def get_services(self, namespace: str, label_selector: str = "") -> list[dict]:
        """kubectl get services, returns raw dicts."""
        args = self._base_kubectl_args() + [
            "get", "services",
            "--namespace", namespace,
            "--output", "json",
        ]
        if label_selector:
            args += ["-l", label_selector]

        out = await self._run(args)
        data = json.loads(out)
        services = []
        for item in data.get("items", []):
            meta = item.get("metadata", {})
            spec = item.get("spec", {})
            lb_status = item.get("status", {}).get("loadBalancer", {})
            external_ips = [
                ing.get("ip", ing.get("hostname", ""))
                for ing in lb_status.get("ingress", [])
            ]
            services.append({
                "name": meta.get("name", ""),
                "type": spec.get("type", ""),
                "cluster_ip": spec.get("clusterIP", ""),
                "external_ips": external_ips,
                "ports": [
                    {"name": p.get("name", ""), "port": p.get("port"), "target_port": p.get("targetPort")}
                    for p in spec.get("ports", [])
                ],
            })
        return services

    async def get_pod_logs(
        self,
        pod_name: str,
        namespace: str,
        tail: int = 100,
        container: str = "",
    ) -> str:
        """kubectl logs."""
        args = self._base_kubectl_args() + [
            "logs", pod_name,
            "--namespace", namespace,
            f"--tail={tail}",
        ]
        if container:
            args += ["-c", container]
        return await self._run(args, timeout=30)

    async def delete_pod(self, pod_name: str, namespace: str) -> bool:
        """kubectl delete pod (for OnDelete rolling update)."""
        args = self._base_kubectl_args() + [
            "delete", "pod", pod_name,
            "--namespace", namespace,
        ]
        try:
            await self._run(args)
            return True
        except HelmError:
            return False

    _K8S_NAME_RE = __import__("re").compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$")

    async def exec_pod(
        self, pod_name: str, namespace: str, command: list[str], timeout: int = 30
    ) -> str:
        """kubectl exec for running commands in a pod.

        Validates pod_name and namespace to prevent injection.
        """
        if not self._K8S_NAME_RE.match(pod_name):
            raise ValueError(f"Invalid pod name: {pod_name}")
        if not self._K8S_NAME_RE.match(namespace):
            raise ValueError(f"Invalid namespace: {namespace}")
        args = self._base_kubectl_args() + [
            "exec", pod_name,
            "--namespace", namespace,
            "--",
        ] + command
        return await self._run(args, timeout=timeout)
