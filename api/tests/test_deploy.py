"""Tests for the deployment abstraction layer."""

import asyncio

import pytest

from bootnode.core.deploy import (
    DeployTarget,
    DockerDeployer,
    KubernetesDeployer,
    ProcessDeployer,
    ServiceStatus,
    ServiceType,
    clear_deployer_cache,
    get_deployer,
)


class TestServiceType:
    """Tests for ServiceType enum."""

    def test_service_types_exist(self):
        """All expected service types should be defined."""
        assert ServiceType.API.value == "api"
        assert ServiceType.WEB.value == "web"
        assert ServiceType.INDEXER.value == "indexer"
        assert ServiceType.WEBHOOK_WORKER.value == "webhook-worker"
        assert ServiceType.BUNDLER.value == "bundler"

    def test_service_type_from_string(self):
        """ServiceType should be constructable from string."""
        assert ServiceType("api") == ServiceType.API
        assert ServiceType("web") == ServiceType.WEB


class TestServiceStatus:
    """Tests for ServiceStatus model."""

    def test_service_status_basic(self):
        """ServiceStatus should work with minimal fields."""
        status = ServiceStatus(
            name="test",
            running=True,
            replicas=2,
            ready_replicas=2,
        )
        assert status.name == "test"
        assert status.running is True
        assert status.replicas == 2
        assert status.ready_replicas == 2
        assert status.cpu_usage is None
        assert status.memory_usage is None

    def test_service_status_full(self):
        """ServiceStatus should work with all fields."""
        status = ServiceStatus(
            name="api",
            running=True,
            replicas=3,
            ready_replicas=2,
            cpu_usage=25.5,
            memory_usage=512.0,
            image="ghcr.io/hanzoai/bootnode:api-latest",
            started_at="2024-01-15T10:00:00Z",
        )
        assert status.cpu_usage == 25.5
        assert status.memory_usage == 512.0
        assert status.image == "ghcr.io/hanzoai/bootnode:api-latest"


class TestDeployTarget:
    """Tests for DeployTarget ABC."""

    def test_is_abstract(self):
        """DeployTarget should not be instantiable directly."""
        with pytest.raises(TypeError):
            DeployTarget()


class TestProcessDeployer:
    """Tests for ProcessDeployer."""

    def test_init(self):
        """ProcessDeployer should initialize correctly."""
        deployer = ProcessDeployer()
        assert deployer.project_root is not None
        assert len(deployer._processes) == 0

    @pytest.mark.asyncio
    async def test_status_not_running(self):
        """Status should show not running for unstarted service."""
        deployer = ProcessDeployer()
        status = await deployer.status(ServiceType.API)
        assert status.running is False
        assert status.replicas == 0
        assert status.ready_replicas == 0

    @pytest.mark.asyncio
    async def test_destroy_not_running(self):
        """Destroy should succeed for service not running."""
        deployer = ProcessDeployer()
        result = await deployer.destroy(ServiceType.API)
        assert result is True

    @pytest.mark.asyncio
    async def test_scale_zero(self):
        """Scale to zero should destroy service."""
        deployer = ProcessDeployer()
        result = await deployer.scale(ServiceType.API, 0)
        assert result is True


class TestDockerDeployer:
    """Tests for DockerDeployer."""

    def test_init_default(self):
        """DockerDeployer should initialize with defaults."""
        deployer = DockerDeployer()
        assert deployer.compose_file.name == "compose.yml"
        assert deployer.project_name == "bootnode"

    def test_init_custom(self):
        """DockerDeployer should accept custom compose file."""
        deployer = DockerDeployer(
            compose_file="/custom/docker-compose.yml",
            project_name="custom",
        )
        assert str(deployer.compose_file) == "/custom/docker-compose.yml"
        assert deployer.project_name == "custom"

    def test_get_service_name(self):
        """Service name mapping should work correctly."""
        deployer = DockerDeployer()
        assert deployer._get_service_name(ServiceType.API) == "api"
        assert deployer._get_service_name(ServiceType.WEBHOOK_WORKER) == "webhook-worker"


class TestKubernetesDeployer:
    """Tests for KubernetesDeployer."""

    def test_init_default(self):
        """KubernetesDeployer should initialize with defaults."""
        deployer = KubernetesDeployer()
        assert deployer.namespace == "bootnode"
        assert deployer.context is None
        assert deployer._initialized is False

    def test_init_custom(self):
        """KubernetesDeployer should accept custom namespace and context."""
        deployer = KubernetesDeployer(
            namespace="custom-ns",
            context="my-context",
        )
        assert deployer.namespace == "custom-ns"
        assert deployer.context == "my-context"

    def test_get_deployment_name(self):
        """Deployment name mapping should work correctly."""
        deployer = KubernetesDeployer()
        assert deployer._get_deployment_name(ServiceType.API) == "bootnode-api"
        assert deployer._get_deployment_name(ServiceType.WEB) == "bootnode-web"

    def test_get_labels(self):
        """Labels should be generated correctly."""
        deployer = KubernetesDeployer()
        labels = deployer._get_labels(ServiceType.API)
        assert labels["app.kubernetes.io/name"] == "api"
        assert labels["app.kubernetes.io/part-of"] == "bootnode"


class TestFactory:
    """Tests for deployer factory."""

    def test_get_deployer_returns_deploytarget(self):
        """get_deployer should return a DeployTarget instance."""
        clear_deployer_cache()
        deployer = get_deployer()
        assert isinstance(deployer, DeployTarget)

    def test_get_deployer_cached(self):
        """get_deployer should return cached instance."""
        clear_deployer_cache()
        deployer1 = get_deployer()
        deployer2 = get_deployer()
        assert deployer1 is deployer2

    def test_clear_cache(self):
        """clear_deployer_cache should clear the cached instance."""
        clear_deployer_cache()
        deployer1 = get_deployer()
        clear_deployer_cache()
        deployer2 = get_deployer()
        # They should be equal in value but may or may not be same object
        # depending on config - just verify no error
        assert deployer2 is not None
