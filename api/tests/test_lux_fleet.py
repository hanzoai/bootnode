"""Comprehensive tests for Lux fleet management.

Covers:
  - lux_models.py: Pydantic models, validators, enums, helm value translation
  - helm.py: HelmDeployer internals (mocked subprocess)
  - lux.py: LuxFleetManager helper methods (mocked HelmDeployer)
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from bootnode.core.chains.lux_models import (
    APIConfig,
    BootstrapConfig,
    ChainTrackingConfig,
    ConsensusConfig,
    ImageConfig,
    LuxFleetCreate,
    LuxFleetStatus,
    LuxFleetUpdate,
    LuxNetwork,
    LuxNetworkConfig,
    LuxNodeStatus,
    NETWORK_CONFIGS,
    NodeServicesConfig,
    RLPImportConfig,
    ResourceConfig,
    ResourceSpec,
    StorageConfig,
    fleet_create_to_helm_values,
    fleet_update_to_helm_values,
)
from bootnode.core.deploy.helm import (
    HelmDeployer,
    HelmError,
    HelmRelease,
    HelmReleaseStatus,
    PodInfo,
)
from bootnode.core.chains.lux import (
    LuxFleetManager,
    NETWORK_VALUES_FILES,
)


# =========================================================================
# 1. lux_models.py -- pure unit tests
# =========================================================================

class TestLuxNetworkEnum:
    """LuxNetwork enum values."""

    def test_values(self):
        assert LuxNetwork.MAINNET.value == "mainnet"
        assert LuxNetwork.TESTNET.value == "testnet"
        assert LuxNetwork.DEVNET.value == "devnet"

    def test_from_string(self):
        assert LuxNetwork("mainnet") == LuxNetwork.MAINNET
        assert LuxNetwork("testnet") == LuxNetwork.TESTNET
        assert LuxNetwork("devnet") == LuxNetwork.DEVNET

    def test_member_count(self):
        assert len(LuxNetwork) == 3


class TestLuxFleetStatusEnum:
    """LuxFleetStatus enum values."""

    def test_all_values(self):
        expected = {
            "pending", "deploying", "running", "degraded",
            "updating", "error", "destroying", "destroyed",
        }
        actual = {s.value for s in LuxFleetStatus}
        assert actual == expected

    def test_member_count(self):
        assert len(LuxFleetStatus) == 8


class TestLuxNodeStatusEnum:
    """LuxNodeStatus enum values."""

    def test_all_values(self):
        expected = {
            "pending", "init", "starting", "bootstrapping",
            "healthy", "unhealthy", "terminated",
        }
        actual = {s.value for s in LuxNodeStatus}
        assert actual == expected

    def test_member_count(self):
        assert len(LuxNodeStatus) == 7


class TestNetworkConfigs:
    """NETWORK_CONFIGS canonical reference data."""

    def test_all_networks_present(self):
        assert set(NETWORK_CONFIGS.keys()) == {
            LuxNetwork.MAINNET,
            LuxNetwork.TESTNET,
            LuxNetwork.DEVNET,
        }

    def test_mainnet_config(self):
        cfg = NETWORK_CONFIGS[LuxNetwork.MAINNET]
        assert cfg.network_id == 1
        assert cfg.chain_id == 96369
        assert cfg.http_port == 9630
        assert cfg.staking_port == 9631
        assert cfg.namespace == "lux-mainnet"

    def test_testnet_config(self):
        cfg = NETWORK_CONFIGS[LuxNetwork.TESTNET]
        assert cfg.network_id == 2
        assert cfg.chain_id == 96368
        assert cfg.http_port == 9640
        assert cfg.staking_port == 9641
        assert cfg.namespace == "lux-testnet"

    def test_devnet_config(self):
        cfg = NETWORK_CONFIGS[LuxNetwork.DEVNET]
        assert cfg.network_id == 3
        assert cfg.chain_id == 96370
        assert cfg.http_port == 9650
        assert cfg.staking_port == 9651
        assert cfg.namespace == "lux-devnet"

    def test_unique_network_ids(self):
        ids = [c.network_id for c in NETWORK_CONFIGS.values()]
        assert len(ids) == len(set(ids))

    def test_unique_chain_ids(self):
        ids = [c.chain_id for c in NETWORK_CONFIGS.values()]
        assert len(ids) == len(set(ids))

    def test_unique_namespaces(self):
        ns = [c.namespace for c in NETWORK_CONFIGS.values()]
        assert len(ns) == len(set(ns))


class TestBootstrapConfig:
    """BootstrapConfig validator tests."""

    def test_valid_node_ids(self):
        cfg = BootstrapConfig(node_ids=["NodeID-abc123", "NodeID-xyz789"])
        assert len(cfg.node_ids) == 2

    def test_empty_node_ids(self):
        cfg = BootstrapConfig(node_ids=[])
        assert cfg.node_ids == []

    def test_invalid_node_id_format(self):
        with pytest.raises(ValueError, match="Invalid node ID format"):
            BootstrapConfig(node_ids=["bad-id"])

    def test_invalid_node_id_mixed(self):
        """One valid + one invalid should fail."""
        with pytest.raises(ValueError, match="Invalid node ID format"):
            BootstrapConfig(node_ids=["NodeID-good", "missing-prefix"])

    def test_defaults(self):
        cfg = BootstrapConfig()
        assert cfg.node_ids == []
        assert cfg.use_hostnames is True
        assert cfg.external_ips == []
        assert cfg.rlp_import.enabled is False


class TestLuxFleetCreate:
    """LuxFleetCreate validation tests."""

    def _valid_params(self, **overrides):
        defaults = {"name": "my-fleet", "cluster_id": "cluster-abc"}
        defaults.update(overrides)
        return defaults

    def test_valid_minimal(self):
        req = LuxFleetCreate(**self._valid_params())
        assert req.name == "my-fleet"
        assert req.cluster_id == "cluster-abc"
        assert req.network == LuxNetwork.DEVNET
        assert req.replicas == 5

    def test_valid_name_lowercase_with_hyphens(self):
        req = LuxFleetCreate(**self._valid_params(name="fleet-01"))
        assert req.name == "fleet-01"

    def test_valid_name_single_char(self):
        req = LuxFleetCreate(**self._valid_params(name="a"))
        assert req.name == "a"

    def test_invalid_name_uppercase(self):
        with pytest.raises(ValueError):
            LuxFleetCreate(**self._valid_params(name="MyFleet"))

    def test_invalid_name_starts_with_digit(self):
        with pytest.raises(ValueError):
            LuxFleetCreate(**self._valid_params(name="1fleet"))

    def test_invalid_name_starts_with_hyphen(self):
        with pytest.raises(ValueError):
            LuxFleetCreate(**self._valid_params(name="-fleet"))

    def test_invalid_name_underscore(self):
        with pytest.raises(ValueError):
            LuxFleetCreate(**self._valid_params(name="my_fleet"))

    def test_invalid_name_empty(self):
        with pytest.raises(ValueError):
            LuxFleetCreate(**self._valid_params(name=""))

    def test_invalid_name_too_long(self):
        with pytest.raises(ValueError):
            LuxFleetCreate(**self._valid_params(name="a" * 64))

    def test_name_max_length_63(self):
        req = LuxFleetCreate(**self._valid_params(name="a" * 63))
        assert len(req.name) == 63

    def test_replicas_default(self):
        req = LuxFleetCreate(**self._valid_params())
        assert req.replicas == 5

    def test_replicas_min_1(self):
        req = LuxFleetCreate(**self._valid_params(replicas=1))
        assert req.replicas == 1

    def test_replicas_max_20(self):
        req = LuxFleetCreate(**self._valid_params(replicas=20))
        assert req.replicas == 20

    def test_replicas_below_min(self):
        with pytest.raises(ValueError):
            LuxFleetCreate(**self._valid_params(replicas=0))

    def test_replicas_above_max(self):
        with pytest.raises(ValueError):
            LuxFleetCreate(**self._valid_params(replicas=21))

    def test_all_networks_accepted(self):
        for net in LuxNetwork:
            req = LuxFleetCreate(**self._valid_params(network=net))
            assert req.network == net

    def test_optional_overrides_default_none(self):
        req = LuxFleetCreate(**self._valid_params())
        assert req.image is None
        assert req.bootstrap is None
        assert req.consensus is None
        assert req.chain_tracking is None
        assert req.resources is None
        assert req.storage is None
        assert req.node_services is None
        assert req.api is None

    def test_log_level_default(self):
        req = LuxFleetCreate(**self._valid_params())
        assert req.log_level == "info"

    def test_db_type_default(self):
        req = LuxFleetCreate(**self._valid_params())
        assert req.db_type == "badgerdb"


class TestLuxFleetUpdate:
    """LuxFleetUpdate partial update tests."""

    def test_all_none_by_default(self):
        req = LuxFleetUpdate()
        assert req.replicas is None
        assert req.image is None
        assert req.consensus is None
        assert req.chain_tracking is None
        assert req.resources is None
        assert req.log_level is None

    def test_replicas_bounds(self):
        req = LuxFleetUpdate(replicas=10)
        assert req.replicas == 10

    def test_replicas_min(self):
        req = LuxFleetUpdate(replicas=1)
        assert req.replicas == 1

    def test_replicas_max(self):
        req = LuxFleetUpdate(replicas=20)
        assert req.replicas == 20

    def test_replicas_below_min(self):
        with pytest.raises(ValueError):
            LuxFleetUpdate(replicas=0)

    def test_replicas_above_max(self):
        with pytest.raises(ValueError):
            LuxFleetUpdate(replicas=21)


class TestFleetCreateToHelmValues:
    """fleet_create_to_helm_values() translation tests."""

    def _minimal_req(self, **overrides):
        defaults = {"name": "test", "cluster_id": "c1"}
        defaults.update(overrides)
        return LuxFleetCreate(**defaults)

    def test_minimal_devnet(self):
        req = self._minimal_req()
        vals = fleet_create_to_helm_values(req)
        assert vals["network"] == "devnet"
        assert vals["replicas"] == 5
        assert vals["logLevel"] == "info"
        assert vals["dbType"] == "badgerdb"

    def test_mainnet(self):
        req = self._minimal_req(network=LuxNetwork.MAINNET)
        vals = fleet_create_to_helm_values(req)
        assert vals["network"] == "mainnet"

    def test_testnet(self):
        req = self._minimal_req(network=LuxNetwork.TESTNET)
        vals = fleet_create_to_helm_values(req)
        assert vals["network"] == "testnet"

    def test_custom_replicas(self):
        req = self._minimal_req(replicas=10)
        vals = fleet_create_to_helm_values(req)
        assert vals["replicas"] == 10

    def test_no_image_keys_when_none(self):
        req = self._minimal_req()
        vals = fleet_create_to_helm_values(req)
        assert "image.repository" not in vals
        assert "image.tag" not in vals

    def test_image_override(self):
        req = self._minimal_req(image=ImageConfig(
            repository="ghcr.io/test/luxd",
            tag="v2.0.0",
            pull_policy="IfNotPresent",
        ))
        vals = fleet_create_to_helm_values(req)
        assert vals["image.repository"] == "ghcr.io/test/luxd"
        assert vals["image.tag"] == "v2.0.0"
        assert vals["image.pullPolicy"] == "IfNotPresent"

    def test_bootstrap_with_node_ids(self):
        req = self._minimal_req(bootstrap=BootstrapConfig(
            node_ids=["NodeID-aaa", "NodeID-bbb"],
            use_hostnames=False,
        ))
        vals = fleet_create_to_helm_values(req)
        assert vals["bootstrap.useHostnames"] is False
        assert vals["bootstrap.nodeIDs"] == ["NodeID-aaa", "NodeID-bbb"]

    def test_bootstrap_rlp_import(self):
        req = self._minimal_req(bootstrap=BootstrapConfig(
            rlp_import=RLPImportConfig(
                enabled=True,
                base_url="https://example.com",
                rlp_filename="chain.rlp",
                timeout=3600,
            ),
        ))
        vals = fleet_create_to_helm_values(req)
        assert vals["bootstrap.rlpImport.enabled"] is True
        assert vals["bootstrap.rlpImport.baseUrl"] == "https://example.com"
        assert vals["bootstrap.rlpImport.rlpFilename"] == "chain.rlp"
        assert vals["bootstrap.rlpImport.timeout"] == 3600

    def test_consensus_override(self):
        req = self._minimal_req(consensus=ConsensusConfig(
            sample_size=10,
            quorum_size=8,
            sybil_protection_enabled=True,
        ))
        vals = fleet_create_to_helm_values(req)
        assert vals["consensus.sampleSize"] == 10
        assert vals["consensus.quorumSize"] == 8
        assert vals["consensus.sybilProtectionEnabled"] is True

    def test_chain_tracking_override(self):
        req = self._minimal_req(chain_tracking=ChainTrackingConfig(
            track_all_chains=False,
            tracked_chains=["X", "P", "C"],
            aliases=["zoo"],
        ))
        vals = fleet_create_to_helm_values(req)
        assert vals["chainTracking.trackAllChains"] is False
        assert vals["chainTracking.trackedChains"] == ["X", "P", "C"]
        assert vals["chainTracking.aliases"] == ["zoo"]

    def test_resources_override(self):
        req = self._minimal_req(resources=ResourceConfig(
            requests=ResourceSpec(memory="2Gi", cpu="1"),
            limits=ResourceSpec(memory="8Gi", cpu="4"),
        ))
        vals = fleet_create_to_helm_values(req)
        assert vals["resources.requests.memory"] == "2Gi"
        assert vals["resources.requests.cpu"] == "1"
        assert vals["resources.limits.memory"] == "8Gi"
        assert vals["resources.limits.cpu"] == "4"

    def test_storage_override(self):
        req = self._minimal_req(storage=StorageConfig(
            size="500Gi",
            storage_class="premium-rwo",
        ))
        vals = fleet_create_to_helm_values(req)
        assert vals["storage.size"] == "500Gi"
        assert vals["storage.storageClass"] == "premium-rwo"

    def test_node_services_override(self):
        req = self._minimal_req(node_services=NodeServicesConfig(
            enabled=False,
            type="ClusterIP",
        ))
        vals = fleet_create_to_helm_values(req)
        assert vals["nodeServices.enabled"] is False
        assert vals["nodeServices.type"] == "ClusterIP"

    def test_api_override(self):
        req = self._minimal_req(api=APIConfig(
            admin_enabled=False,
            metrics_enabled=True,
            index_enabled=False,
            http_allowed_hosts="127.0.0.1",
        ))
        vals = fleet_create_to_helm_values(req)
        assert vals["api.adminEnabled"] is False
        assert vals["api.metricsEnabled"] is True
        assert vals["api.indexEnabled"] is False
        assert vals["api.httpAllowedHosts"] == "127.0.0.1"

    def test_all_three_networks_produce_correct_network_key(self):
        for net in LuxNetwork:
            req = self._minimal_req(network=net)
            vals = fleet_create_to_helm_values(req)
            assert vals["network"] == net.value


class TestFleetUpdateToHelmValues:
    """fleet_update_to_helm_values() partial translation tests."""

    def test_empty_update_produces_empty_dict(self):
        req = LuxFleetUpdate()
        vals = fleet_update_to_helm_values(req)
        assert vals == {}

    def test_replicas_only(self):
        req = LuxFleetUpdate(replicas=3)
        vals = fleet_update_to_helm_values(req)
        assert vals == {"replicas": 3}

    def test_log_level_only(self):
        req = LuxFleetUpdate(log_level="debug")
        vals = fleet_update_to_helm_values(req)
        assert vals == {"logLevel": "debug"}

    def test_image_only(self):
        req = LuxFleetUpdate(image=ImageConfig(
            repository="test", tag="v1", pull_policy="Never",
        ))
        vals = fleet_update_to_helm_values(req)
        assert vals["image.repository"] == "test"
        assert vals["image.tag"] == "v1"
        assert vals["image.pullPolicy"] == "Never"
        assert "replicas" not in vals
        assert "logLevel" not in vals

    def test_consensus_only(self):
        req = LuxFleetUpdate(consensus=ConsensusConfig(
            sample_size=7,
            quorum_size=5,
            sybil_protection_enabled=True,
        ))
        vals = fleet_update_to_helm_values(req)
        assert vals["consensus.sampleSize"] == 7
        assert vals["consensus.quorumSize"] == 5
        assert vals["consensus.sybilProtectionEnabled"] is True
        assert "replicas" not in vals

    def test_resources_only(self):
        req = LuxFleetUpdate(resources=ResourceConfig())
        vals = fleet_update_to_helm_values(req)
        assert "resources.requests.memory" in vals
        assert "resources.limits.cpu" in vals
        assert "replicas" not in vals

    def test_chain_tracking_only(self):
        req = LuxFleetUpdate(chain_tracking=ChainTrackingConfig(
            track_all_chains=True,
        ))
        vals = fleet_update_to_helm_values(req)
        assert vals["chainTracking.trackAllChains"] is True

    def test_multiple_fields(self):
        req = LuxFleetUpdate(replicas=8, log_level="warn")
        vals = fleet_update_to_helm_values(req)
        assert vals["replicas"] == 8
        assert vals["logLevel"] == "warn"
        assert len(vals) == 2


# =========================================================================
# 2. helm.py -- HelmDeployer tests (mock subprocess)
# =========================================================================

class TestHelmReleaseStatusEnum:
    """HelmReleaseStatus enum values."""

    def test_all_values(self):
        expected = {
            "deployed", "failed", "pending-install", "pending-upgrade",
            "pending-rollback", "superseded", "uninstalled", "uninstalling",
            "unknown",
        }
        actual = {s.value for s in HelmReleaseStatus}
        assert actual == expected

    def test_member_count(self):
        assert len(HelmReleaseStatus) == 9


class TestHelmRelease:
    """HelmRelease dataclass creation."""

    def test_basic_creation(self):
        r = HelmRelease(
            name="luxd-devnet",
            namespace="lux-devnet",
            revision=3,
            status=HelmReleaseStatus.DEPLOYED,
        )
        assert r.name == "luxd-devnet"
        assert r.namespace == "lux-devnet"
        assert r.revision == 3
        assert r.status == HelmReleaseStatus.DEPLOYED
        assert r.chart == ""
        assert r.app_version == ""
        assert r.updated == ""

    def test_full_creation(self):
        r = HelmRelease(
            name="luxd-mainnet",
            namespace="lux-mainnet",
            revision=7,
            status=HelmReleaseStatus.DEPLOYED,
            chart="lux-0.1.0",
            app_version="1.23.11",
            updated="2026-02-10T00:00:00Z",
        )
        assert r.chart == "lux-0.1.0"
        assert r.app_version == "1.23.11"
        assert r.updated == "2026-02-10T00:00:00Z"


class TestHelmError:
    """HelmError exception."""

    def test_basic(self):
        e = HelmError("deploy failed")
        assert str(e) == "deploy failed"
        assert e.stderr == ""
        assert e.returncode == 1

    def test_with_details(self):
        e = HelmError("timeout", stderr="connection refused", returncode=2)
        assert e.stderr == "connection refused"
        assert e.returncode == 2


class TestPodInfo:
    """PodInfo dataclass."""

    def test_creation(self):
        p = PodInfo(name="luxd-0", ready=True, status="Running")
        assert p.name == "luxd-0"
        assert p.ready is True
        assert p.restarts == 0
        assert p.node == ""
        assert p.ip == ""


class TestHelmDeployerBaseArgs:
    """HelmDeployer._base_helm_args() tests."""

    def test_no_kubeconfig(self):
        d = HelmDeployer(chart_path=Path("/charts/lux"))
        args = d._base_helm_args()
        assert args == ["helm"]

    def test_with_kubeconfig(self):
        d = HelmDeployer(
            chart_path=Path("/charts/lux"),
            kubeconfig_path=Path("/tmp/kube.conf"),
        )
        args = d._base_helm_args()
        assert args == ["helm", "--kubeconfig", "/tmp/kube.conf"]

    def test_with_context(self):
        d = HelmDeployer(
            chart_path=Path("/charts/lux"),
            kube_context="my-ctx",
        )
        args = d._base_helm_args()
        assert args == ["helm", "--kube-context", "my-ctx"]

    def test_with_kubeconfig_and_context(self):
        d = HelmDeployer(
            chart_path=Path("/charts/lux"),
            kubeconfig_path=Path("/tmp/kc"),
            kube_context="ctx",
        )
        args = d._base_helm_args()
        assert args == [
            "helm",
            "--kubeconfig", "/tmp/kc",
            "--kube-context", "ctx",
        ]

    def test_custom_binary(self):
        d = HelmDeployer(
            chart_path=Path("/charts/lux"),
            helm_binary="/usr/local/bin/helm3",
        )
        args = d._base_helm_args()
        assert args[0] == "/usr/local/bin/helm3"


class TestHelmDeployerBaseKubectlArgs:
    """HelmDeployer._base_kubectl_args() tests."""

    def test_no_config(self):
        d = HelmDeployer(chart_path=Path("/charts/lux"))
        args = d._base_kubectl_args()
        assert args == ["kubectl"]

    def test_with_kubeconfig(self):
        d = HelmDeployer(
            chart_path=Path("/charts/lux"),
            kubeconfig_path=Path("/tmp/kc"),
        )
        args = d._base_kubectl_args()
        assert args == ["kubectl", "--kubeconfig", "/tmp/kc"]

    def test_with_context(self):
        d = HelmDeployer(
            chart_path=Path("/charts/lux"),
            kube_context="ctx",
        )
        args = d._base_kubectl_args()
        # kubectl uses --context not --kube-context
        assert args == ["kubectl", "--context", "ctx"]


class TestHelmDeployerWriteValues:
    """HelmDeployer._write_values_file() tests."""

    def test_creates_valid_yaml(self):
        d = HelmDeployer(chart_path=Path("/charts/lux"))
        values = {
            "network": "devnet",
            "replicas": 5,
            "logLevel": "info",
            "nested": {"key": "value"},
        }
        path = d._write_values_file(values)
        try:
            assert path.exists()
            assert path.suffix == ".yaml"
            assert "helm-values-" in path.name
            content = yaml.safe_load(path.read_text())
            assert content["network"] == "devnet"
            assert content["replicas"] == 5
            assert content["logLevel"] == "info"
            assert content["nested"]["key"] == "value"
        finally:
            path.unlink(missing_ok=True)

    def test_empty_dict(self):
        d = HelmDeployer(chart_path=Path("/charts/lux"))
        path = d._write_values_file({})
        try:
            assert path.exists()
            content = yaml.safe_load(path.read_text())
            # yaml.safe_load returns None for empty doc
            assert content is None or content == {}
        finally:
            path.unlink(missing_ok=True)

    def test_list_values(self):
        d = HelmDeployer(chart_path=Path("/charts/lux"))
        values = {"nodeIDs": ["NodeID-a", "NodeID-b"]}
        path = d._write_values_file(values)
        try:
            content = yaml.safe_load(path.read_text())
            assert content["nodeIDs"] == ["NodeID-a", "NodeID-b"]
        finally:
            path.unlink(missing_ok=True)


class TestHelmDeployerLock:
    """HelmDeployer._get_lock() tests."""

    def test_same_release_returns_same_lock(self):
        d = HelmDeployer(chart_path=Path("/charts/lux"))
        lock1 = d._get_lock("luxd-devnet")
        lock2 = d._get_lock("luxd-devnet")
        assert lock1 is lock2

    def test_different_releases_return_different_locks(self):
        d = HelmDeployer(chart_path=Path("/charts/lux"))
        lock1 = d._get_lock("luxd-devnet")
        lock2 = d._get_lock("luxd-mainnet")
        assert lock1 is not lock2


# =========================================================================
# 3. lux.py -- LuxFleetManager tests (mock HelmDeployer)
# =========================================================================

class TestLuxFleetManagerReleaseName:
    """LuxFleetManager._release_name() tests."""

    def test_mainnet(self):
        mgr = LuxFleetManager()
        assert mgr._release_name(LuxNetwork.MAINNET) == "luxd-mainnet"

    def test_testnet(self):
        mgr = LuxFleetManager()
        assert mgr._release_name(LuxNetwork.TESTNET) == "luxd-testnet"

    def test_devnet(self):
        mgr = LuxFleetManager()
        assert mgr._release_name(LuxNetwork.DEVNET) == "luxd-devnet"


class TestLuxFleetManagerNamespace:
    """LuxFleetManager._namespace() tests."""

    def test_mainnet(self):
        mgr = LuxFleetManager()
        assert mgr._namespace(LuxNetwork.MAINNET) == "lux-mainnet"

    def test_testnet(self):
        mgr = LuxFleetManager()
        assert mgr._namespace(LuxNetwork.TESTNET) == "lux-testnet"

    def test_devnet(self):
        mgr = LuxFleetManager()
        assert mgr._namespace(LuxNetwork.DEVNET) == "lux-devnet"


class TestLuxFleetManagerFleetId:
    """LuxFleetManager._fleet_id() tests."""

    def test_format(self):
        mgr = LuxFleetManager()
        assert mgr._fleet_id("my-fleet", LuxNetwork.DEVNET) == "my-fleet-devnet"
        assert mgr._fleet_id("prod", LuxNetwork.MAINNET) == "prod-mainnet"


class TestLuxFleetManagerGetValuesFiles:
    """LuxFleetManager._get_values_files() tests."""

    def test_mainnet_returns_file_if_exists(self, tmp_path):
        chart_dir = tmp_path / "charts" / "lux"
        chart_dir.mkdir(parents=True)
        values_file = chart_dir / "values-mainnet.yaml"
        values_file.write_text("network: mainnet\n")

        mgr = LuxFleetManager(chart_path=chart_dir)
        files = mgr._get_values_files(LuxNetwork.MAINNET)
        assert len(files) == 1
        assert files[0] == values_file

    def test_testnet_returns_file_if_exists(self, tmp_path):
        chart_dir = tmp_path / "charts" / "lux"
        chart_dir.mkdir(parents=True)
        values_file = chart_dir / "values-testnet.yaml"
        values_file.write_text("network: testnet\n")

        mgr = LuxFleetManager(chart_path=chart_dir)
        files = mgr._get_values_files(LuxNetwork.TESTNET)
        assert len(files) == 1
        assert files[0] == values_file

    def test_devnet_returns_empty_list(self, tmp_path):
        """Devnet has no network-specific values file in NETWORK_VALUES_FILES."""
        chart_dir = tmp_path / "charts" / "lux"
        chart_dir.mkdir(parents=True)

        mgr = LuxFleetManager(chart_path=chart_dir)
        files = mgr._get_values_files(LuxNetwork.DEVNET)
        assert files == []

    def test_mainnet_returns_empty_if_file_missing(self, tmp_path):
        chart_dir = tmp_path / "charts" / "lux"
        chart_dir.mkdir(parents=True)
        # Do not create the values-mainnet.yaml file

        mgr = LuxFleetManager(chart_path=chart_dir)
        files = mgr._get_values_files(LuxNetwork.MAINNET)
        assert files == []


class TestNetworkValuesFiles:
    """NETWORK_VALUES_FILES constant."""

    def test_mainnet_has_values_file(self):
        assert "mainnet" in NETWORK_VALUES_FILES
        assert NETWORK_VALUES_FILES["mainnet"] == "values-mainnet.yaml"

    def test_testnet_has_values_file(self):
        assert "testnet" in NETWORK_VALUES_FILES
        assert NETWORK_VALUES_FILES["testnet"] == "values-testnet.yaml"

    def test_devnet_has_no_values_file(self):
        assert "devnet" not in NETWORK_VALUES_FILES


class TestLuxFleetManagerGetDeployer:
    """LuxFleetManager._get_deployer() creates HelmDeployer from kubeconfig."""

    async def test_creates_deployer_with_kubeconfig(self):
        mgr = LuxFleetManager(chart_path=Path("/opt/charts/lux"))
        kubeconfig_yaml = "apiVersion: v1\nkind: Config\nclusters: []\n"
        deployer = await mgr._get_deployer(kubeconfig_yaml)
        assert isinstance(deployer, HelmDeployer)
        assert deployer.chart_path == Path("/opt/charts/lux")
        assert deployer.kubeconfig_path is not None
        assert deployer.kubeconfig_path.exists()
        content = deployer.kubeconfig_path.read_text()
        assert "apiVersion: v1" in content
        # Cleanup
        deployer.kubeconfig_path.unlink(missing_ok=True)


# =========================================================================
# Sub-model default value tests
# =========================================================================

class TestSubModelDefaults:
    """Verify defaults of sub-models match chart expectations."""

    def test_rlp_import_defaults(self):
        r = RLPImportConfig()
        assert r.enabled is False
        assert r.base_url == ""
        assert r.rlp_filename == ""
        assert r.multi_part is False
        assert r.parts == []
        assert r.min_height == 1
        assert r.timeout == 7200

    def test_consensus_defaults(self):
        c = ConsensusConfig()
        assert c.sample_size == 5
        assert c.quorum_size == 4
        assert c.sybil_protection_enabled is False
        assert c.require_validator_to_connect is False
        assert c.allow_private_ips is True

    def test_chain_tracking_defaults(self):
        ct = ChainTrackingConfig()
        assert ct.track_all_chains is True
        assert ct.tracked_chains == []
        assert ct.aliases == ["zoo", "hanzo", "spc", "pars"]

    def test_image_defaults(self):
        img = ImageConfig()
        assert img.repository == "registry.digitalocean.com/hanzo/bootnode"
        assert img.tag == "luxd-v1.23.11"
        assert img.pull_policy == "Always"

    def test_resource_defaults(self):
        r = ResourceConfig()
        assert r.requests.memory == "1Gi"
        assert r.requests.cpu == "500m"
        assert r.limits.memory == "4Gi"
        assert r.limits.cpu == "2"

    def test_storage_defaults(self):
        s = StorageConfig()
        assert s.size == "100Gi"
        assert s.storage_class == "do-block-storage"

    def test_node_services_defaults(self):
        ns = NodeServicesConfig()
        assert ns.enabled is True
        assert ns.type == "LoadBalancer"
        assert ns.annotations == {}

    def test_api_defaults(self):
        a = APIConfig()
        assert a.admin_enabled is True
        assert a.metrics_enabled is True
        assert a.index_enabled is True
        assert a.http_allowed_hosts == "*"
