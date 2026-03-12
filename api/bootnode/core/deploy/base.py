"""Abstract base class for deployment targets."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncIterator

from pydantic import BaseModel


class ServiceType(str, Enum):
    """Bootnode service types.

    Core platform services plus all blockchain infrastructure services
    deployable per-network per-org.
    """

    # Core platform
    API = "api"
    WEB = "web"
    INDEXER = "indexer"
    WEBHOOK_WORKER = "webhook-worker"
    BUNDLER = "bundler"

    # Block explorer
    EXPLORER = "explorer"

    # The Graph
    GRAPH_NODE = "graph-node"
    GRAPH_POSTGRES = "graph-postgres"
    GRAPH_IPFS = "graph-ipfs"

    # DeFi / exchange
    BRIDGE = "bridge"
    EXCHANGE = "exchange"
    MARKET = "market"
    STAKING = "staking"

    # Security / multisig
    MPC = "mpc"
    MPC_POSTGRES = "mpc-postgres"
    SAFE = "safe"
    SAFE_TRANSACTION = "safe-transaction"
    SAFE_CONFIG = "safe-config"

    # Networking
    GATEWAY = "gateway"
    RPC_PROXY = "rpc-proxy"
    VALIDATOR = "validator"

    # Tools
    FAUCET = "faucet"


class ServiceStatus(BaseModel):
    """Status of a deployed service."""

    name: str
    running: bool
    replicas: int
    ready_replicas: int
    cpu_usage: float | None = None
    memory_usage: float | None = None
    image: str | None = None
    started_at: str | None = None


class DeployTarget(ABC):
    """Abstract base class for deployment targets.

    Implementations handle deploying, scaling, and managing Bootnode services
    across different infrastructure backends (Docker, Kubernetes, local processes).
    """

    @abstractmethod
    async def deploy(
        self,
        service: ServiceType,
        image: str,
        replicas: int = 1,
        env: dict[str, str] | None = None,
    ) -> bool:
        """Deploy or update a service.

        Args:
            service: The service type to deploy.
            image: Container image or command to run.
            replicas: Number of replicas to run.
            env: Environment variables to set.

        Returns:
            True if deployment succeeded, False otherwise.
        """
        ...

    @abstractmethod
    async def scale(self, service: ServiceType, replicas: int) -> bool:
        """Scale a service to the specified number of replicas.

        Args:
            service: The service type to scale.
            replicas: Target number of replicas.

        Returns:
            True if scaling succeeded, False otherwise.
        """
        ...

    @abstractmethod
    async def status(self, service: ServiceType) -> ServiceStatus:
        """Get the current status of a service.

        Args:
            service: The service type to check.

        Returns:
            ServiceStatus with current state information.
        """
        ...

    @abstractmethod
    async def logs(
        self,
        service: ServiceType,
        tail: int = 100,
        follow: bool = False,
    ) -> AsyncIterator[str]:
        """Stream logs from a service.

        Args:
            service: The service type to get logs from.
            tail: Number of recent lines to return.
            follow: If True, continue streaming new logs.

        Yields:
            Log lines as strings.
        """
        ...

    @abstractmethod
    async def destroy(self, service: ServiceType) -> bool:
        """Stop and remove a service.

        Args:
            service: The service type to destroy.

        Returns:
            True if destruction succeeded, False otherwise.
        """
        ...

    async def health(self, service: ServiceType) -> bool:
        """Check if a service is healthy.

        Default implementation checks if service is running with ready replicas.

        Args:
            service: The service type to check.

        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            st = await self.status(service)
            return st.running and st.ready_replicas > 0
        except Exception:
            return False

    async def restart(self, service: ServiceType) -> bool:
        """Restart a service.

        Default implementation destroys and redeploys.

        Args:
            service: The service type to restart.

        Returns:
            True if restart succeeded, False otherwise.
        """
        st = await self.status(service)
        if not st.image:
            return False
        await self.destroy(service)
        return await self.deploy(service, st.image, st.replicas)
