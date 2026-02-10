"""Pluggable deployment abstraction layer.

This module provides a unified interface for deploying Bootnode services
across different infrastructure backends:

- Docker Compose (default): For containerized deployments
- Local Processes: For development without Docker
- Kubernetes: For production k8s clusters

Usage:
    from bootnode.core.deploy import get_deployer, ServiceType

    deployer = get_deployer()
    await deployer.deploy(ServiceType.API, "ghcr.io/hanzoai/bootnode:api-latest", replicas=2)
    status = await deployer.status(ServiceType.API)
    async for line in deployer.logs(ServiceType.API, tail=50):
        print(line)
"""

from bootnode.core.deploy.base import DeployTarget, ServiceStatus, ServiceType
from bootnode.core.deploy.docker import DockerDeployer
from bootnode.core.deploy.factory import clear_deployer_cache, get_deployer
from bootnode.core.deploy.kubernetes import KubernetesDeployer
from bootnode.core.deploy.helm import HelmDeployer
from bootnode.core.deploy.process import ProcessDeployer

__all__ = [
    # Base classes and types
    "DeployTarget",
    "ServiceStatus",
    "ServiceType",
    # Deployers
    "DockerDeployer",
    "HelmDeployer",
    "KubernetesDeployer",
    "ProcessDeployer",
    # Factory
    "get_deployer",
    "clear_deployer_cache",
]
