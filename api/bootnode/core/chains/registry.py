"""Chain registry - supported blockchains and networks."""

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from bootnode.config import get_settings


class ChainType(str, Enum):
    """Blockchain type."""

    EVM = "evm"
    SOLANA = "solana"
    BITCOIN = "bitcoin"


@dataclass
class Network:
    """Network configuration."""

    name: str
    chain_id: int | None  # None for non-EVM
    is_testnet: bool
    rpc_env_var: str
    explorer_url: str | None = None
    native_currency: str = "ETH"
    native_decimals: int = 18


@dataclass
class Chain:
    """Blockchain configuration."""

    name: str
    slug: str
    chain_type: ChainType
    networks: dict[str, Network] = field(default_factory=dict)
    logo_url: str | None = None

    def get_rpc_url(self, network: str = "mainnet") -> str | None:
        """Get RPC URL for a network from environment."""
        settings = get_settings()
        net = self.networks.get(network)
        if not net:
            return None
        return getattr(settings, net.rpc_env_var, None) or None


class ChainRegistry:
    """Registry of supported blockchains."""

    _chains: ClassVar[dict[str, Chain]] = {}
    _initialized: ClassVar[bool] = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize the chain registry with supported chains."""
        if cls._initialized:
            return

        # Ethereum
        cls._chains["ethereum"] = Chain(
            name="Ethereum",
            slug="ethereum",
            chain_type=ChainType.EVM,
            networks={
                "mainnet": Network(
                    name="Mainnet",
                    chain_id=1,
                    is_testnet=False,
                    rpc_env_var="eth_mainnet_rpc",
                    explorer_url="https://etherscan.io",
                ),
                "sepolia": Network(
                    name="Sepolia",
                    chain_id=11155111,
                    is_testnet=True,
                    rpc_env_var="eth_sepolia_rpc",
                    explorer_url="https://sepolia.etherscan.io",
                ),
                "holesky": Network(
                    name="Holesky",
                    chain_id=17000,
                    is_testnet=True,
                    rpc_env_var="eth_holesky_rpc",
                    explorer_url="https://holesky.etherscan.io",
                ),
            },
        )

        # Polygon
        cls._chains["polygon"] = Chain(
            name="Polygon",
            slug="polygon",
            chain_type=ChainType.EVM,
            networks={
                "mainnet": Network(
                    name="Mainnet",
                    chain_id=137,
                    is_testnet=False,
                    rpc_env_var="polygon_mainnet_rpc",
                    explorer_url="https://polygonscan.com",
                    native_currency="MATIC",
                ),
                "amoy": Network(
                    name="Amoy",
                    chain_id=80002,
                    is_testnet=True,
                    rpc_env_var="polygon_amoy_rpc",
                    explorer_url="https://amoy.polygonscan.com",
                    native_currency="MATIC",
                ),
            },
        )

        # Arbitrum
        cls._chains["arbitrum"] = Chain(
            name="Arbitrum",
            slug="arbitrum",
            chain_type=ChainType.EVM,
            networks={
                "mainnet": Network(
                    name="One",
                    chain_id=42161,
                    is_testnet=False,
                    rpc_env_var="arbitrum_mainnet_rpc",
                    explorer_url="https://arbiscan.io",
                ),
                "sepolia": Network(
                    name="Sepolia",
                    chain_id=421614,
                    is_testnet=True,
                    rpc_env_var="arbitrum_sepolia_rpc",
                    explorer_url="https://sepolia.arbiscan.io",
                ),
            },
        )

        # Optimism
        cls._chains["optimism"] = Chain(
            name="Optimism",
            slug="optimism",
            chain_type=ChainType.EVM,
            networks={
                "mainnet": Network(
                    name="Mainnet",
                    chain_id=10,
                    is_testnet=False,
                    rpc_env_var="optimism_mainnet_rpc",
                    explorer_url="https://optimistic.etherscan.io",
                ),
                "sepolia": Network(
                    name="Sepolia",
                    chain_id=11155420,
                    is_testnet=True,
                    rpc_env_var="optimism_sepolia_rpc",
                    explorer_url="https://sepolia-optimism.etherscan.io",
                ),
            },
        )

        # Base
        cls._chains["base"] = Chain(
            name="Base",
            slug="base",
            chain_type=ChainType.EVM,
            networks={
                "mainnet": Network(
                    name="Mainnet",
                    chain_id=8453,
                    is_testnet=False,
                    rpc_env_var="base_mainnet_rpc",
                    explorer_url="https://basescan.org",
                ),
                "sepolia": Network(
                    name="Sepolia",
                    chain_id=84532,
                    is_testnet=True,
                    rpc_env_var="base_sepolia_rpc",
                    explorer_url="https://sepolia.basescan.org",
                ),
            },
        )

        # Avalanche
        cls._chains["avalanche"] = Chain(
            name="Avalanche",
            slug="avalanche",
            chain_type=ChainType.EVM,
            networks={
                "mainnet": Network(
                    name="C-Chain",
                    chain_id=43114,
                    is_testnet=False,
                    rpc_env_var="avalanche_mainnet_rpc",
                    explorer_url="https://snowtrace.io",
                    native_currency="AVAX",
                ),
                "fuji": Network(
                    name="Fuji",
                    chain_id=43113,
                    is_testnet=True,
                    rpc_env_var="avalanche_fuji_rpc",
                    explorer_url="https://testnet.snowtrace.io",
                    native_currency="AVAX",
                ),
            },
        )

        # BNB Chain
        cls._chains["bsc"] = Chain(
            name="BNB Smart Chain",
            slug="bsc",
            chain_type=ChainType.EVM,
            networks={
                "mainnet": Network(
                    name="Mainnet",
                    chain_id=56,
                    is_testnet=False,
                    rpc_env_var="bsc_mainnet_rpc",
                    explorer_url="https://bscscan.com",
                    native_currency="BNB",
                ),
                "testnet": Network(
                    name="Testnet",
                    chain_id=97,
                    is_testnet=True,
                    rpc_env_var="bsc_testnet_rpc",
                    explorer_url="https://testnet.bscscan.com",
                    native_currency="BNB",
                ),
            },
        )

        # Lux
        cls._chains["lux"] = Chain(
            name="Lux",
            slug="lux",
            chain_type=ChainType.EVM,
            networks={
                "mainnet": Network(
                    name="Mainnet",
                    chain_id=96369,
                    is_testnet=False,
                    rpc_env_var="lux_mainnet_rpc",
                    explorer_url="https://explore.lux.network",
                    native_currency="LUX",
                ),
                "testnet": Network(
                    name="Testnet",
                    chain_id=96368,
                    is_testnet=True,
                    rpc_env_var="lux_testnet_rpc",
                    explorer_url="https://explore.testnet.lux.network",
                    native_currency="LUX",
                ),
                "devnet": Network(
                    name="Devnet",
                    chain_id=96370,
                    is_testnet=True,
                    rpc_env_var="lux_devnet_rpc",
                    explorer_url="https://explore.devnet.lux.network",
                    native_currency="LUX",
                ),
            },
        )

        # Bitcoin
        cls._chains["bitcoin"] = Chain(
            name="Bitcoin",
            slug="bitcoin",
            chain_type=ChainType.BITCOIN,
            networks={
                "mainnet": Network(
                    name="Mainnet",
                    chain_id=None,
                    is_testnet=False,
                    rpc_env_var="btc_mainnet_rpc",
                    explorer_url="https://mempool.space",
                    native_currency="BTC",
                    native_decimals=8,
                ),
                "testnet": Network(
                    name="Testnet",
                    chain_id=None,
                    is_testnet=True,
                    rpc_env_var="btc_testnet_rpc",
                    explorer_url="https://mempool.space/testnet",
                    native_currency="BTC",
                    native_decimals=8,
                ),
            },
        )

        # Solana
        cls._chains["solana"] = Chain(
            name="Solana",
            slug="solana",
            chain_type=ChainType.SOLANA,
            networks={
                "mainnet": Network(
                    name="Mainnet Beta",
                    chain_id=None,
                    is_testnet=False,
                    rpc_env_var="solana_mainnet_rpc",
                    explorer_url="https://solscan.io",
                    native_currency="SOL",
                    native_decimals=9,
                ),
                "devnet": Network(
                    name="Devnet",
                    chain_id=None,
                    is_testnet=True,
                    rpc_env_var="solana_devnet_rpc",
                    explorer_url="https://solscan.io?cluster=devnet",
                    native_currency="SOL",
                    native_decimals=9,
                ),
            },
        )

        cls._initialized = True

    @classmethod
    def get_chain(cls, slug: str) -> Chain | None:
        """Get chain by slug."""
        cls.initialize()
        return cls._chains.get(slug)

    @classmethod
    def get_all_chains(cls) -> dict[str, Chain]:
        """Get all supported chains."""
        cls.initialize()
        return cls._chains.copy()

    @classmethod
    def get_evm_chains(cls) -> dict[str, Chain]:
        """Get all EVM-compatible chains."""
        cls.initialize()
        return {k: v for k, v in cls._chains.items() if v.chain_type == ChainType.EVM}

    @classmethod
    def is_supported(cls, chain: str, network: str = "mainnet") -> bool:
        """Check if chain/network combination is supported."""
        cls.initialize()
        chain_config = cls._chains.get(chain)
        if not chain_config:
            return False
        return network in chain_config.networks
