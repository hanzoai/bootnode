"""Native ZAP Server Implementation.

Implements the Zap interface from zap.capnp for native Cap'n Proto RPC.
This allows AI agents to connect directly via zap://bootnode:9999.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import capnp
import structlog

from bootnode.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Load the Bootnode schema (compiled from bootnode.zap)
SCHEMA_PATH = Path(__file__).parent / "bootnode.capnp"
bootnode_capnp = capnp.load(str(SCHEMA_PATH))


class BootnodeZapImpl(bootnode_capnp.Bootnode.Server):
    """Native ZAP interface implementation for Bootnode cloud APIs.

    Implements the full Zap interface with tools for:
    - RPC calls to any supported blockchain
    - Token balance/metadata queries
    - NFT ownership/metadata queries
    - Smart wallet creation/management
    - Webhook management
    - Gas estimation
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self._tools = self._build_tools()
        self._resources = self._build_resources()

    def _build_tools(self) -> list[dict[str, Any]]:
        """Build tool definitions for cloud APIs."""
        return [
            {
                "name": "rpc_call",
                "description": "Execute JSON-RPC on any supported blockchain",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "chain": {"type": "string", "description": "Chain name (ethereum, polygon, etc.)"},
                        "network": {"type": "string", "default": "mainnet"},
                        "method": {"type": "string", "description": "RPC method"},
                        "params": {"type": "array", "default": []},
                    },
                    "required": ["chain", "method"],
                }).encode(),
            },
            {
                "name": "get_token_balances",
                "description": "Get all ERC-20 token balances for an address",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "address": {"type": "string"},
                        "chain": {"type": "string"},
                        "network": {"type": "string", "default": "mainnet"},
                    },
                    "required": ["address", "chain"],
                }).encode(),
            },
            {
                "name": "get_token_metadata",
                "description": "Get ERC-20 token metadata (name, symbol, decimals)",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "contract": {"type": "string"},
                        "chain": {"type": "string"},
                        "network": {"type": "string", "default": "mainnet"},
                    },
                    "required": ["contract", "chain"],
                }).encode(),
            },
            {
                "name": "get_nfts_owned",
                "description": "Get all NFTs owned by an address",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "address": {"type": "string"},
                        "chain": {"type": "string"},
                        "network": {"type": "string", "default": "mainnet"},
                    },
                    "required": ["address", "chain"],
                }).encode(),
            },
            {
                "name": "get_nft_metadata",
                "description": "Get NFT metadata (name, description, image, attributes)",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "contract": {"type": "string"},
                        "token_id": {"type": "string"},
                        "chain": {"type": "string"},
                        "network": {"type": "string", "default": "mainnet"},
                    },
                    "required": ["contract", "token_id", "chain"],
                }).encode(),
            },
            {
                "name": "create_smart_wallet",
                "description": "Create an ERC-4337 smart wallet",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Owner EOA address"},
                        "chain": {"type": "string"},
                        "network": {"type": "string", "default": "mainnet"},
                    },
                    "required": ["owner", "chain"],
                }).encode(),
            },
            {
                "name": "get_smart_wallet",
                "description": "Get smart wallet details",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "address": {"type": "string"},
                        "chain": {"type": "string"},
                        "network": {"type": "string", "default": "mainnet"},
                    },
                    "required": ["address", "chain"],
                }).encode(),
            },
            {
                "name": "create_webhook",
                "description": "Create a webhook for blockchain events",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "event_type": {"type": "string", "enum": [
                            "ADDRESS_ACTIVITY",
                            "TOKEN_TRANSFER",
                            "NFT_TRANSFER",
                            "CONTRACT_EVENT",
                        ]},
                        "chain": {"type": "string"},
                        "network": {"type": "string", "default": "mainnet"},
                        "filters": {"type": "object"},
                    },
                    "required": ["url", "event_type", "chain"],
                }).encode(),
            },
            {
                "name": "list_webhooks",
                "description": "List all configured webhooks",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {},
                }).encode(),
            },
            {
                "name": "delete_webhook",
                "description": "Delete a webhook by ID",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                    },
                    "required": ["id"],
                }).encode(),
            },
            {
                "name": "estimate_gas",
                "description": "Get current gas prices for a chain",
                "schema": json.dumps({
                    "type": "object",
                    "properties": {
                        "chain": {"type": "string"},
                    },
                    "required": ["chain"],
                }).encode(),
            },
        ]

    def _build_resources(self) -> list[dict[str, Any]]:
        """Build resource definitions."""
        return [
            {
                "uri": "bootnode://chains",
                "name": "Supported Chains",
                "description": "List of all supported blockchain networks",
                "mimeType": "application/json",
            },
            {
                "uri": "bootnode://usage",
                "name": "Usage Statistics",
                "description": "API usage for current billing period",
                "mimeType": "application/json",
            },
            {
                "uri": "bootnode://config",
                "name": "Configuration",
                "description": "Current API configuration and limits",
                "mimeType": "application/json",
            },
        ]

    async def init(self, client, _context, **_kwargs):
        """Initialize connection and return server info."""
        logger.info("ZAP client connected", client_name=client.name, client_version=client.version)

        return bootnode_capnp.ServerInfo.new_message(
            name="bootnode",
            version="2.0.0",
            capabilities=bootnode_capnp.ServerInfo.Capabilities.new_message(
                tools=True,
                resources=True,
                prompts=False,
                logging=True,
            ),
        )

    async def listTools(self, _context, **_kwargs):
        """List available tools."""
        tools_msg = bootnode_capnp.ToolList.new_message()
        tools_list = tools_msg.init("tools", len(self._tools))

        for i, tool in enumerate(self._tools):
            tools_list[i].name = tool["name"]
            tools_list[i].description = tool["description"]
            tools_list[i].schema = tool["schema"]

        return tools_msg

    async def callTool(self, call, _context, **_kwargs):
        """Execute a tool call."""
        tool_name = call.name
        tool_id = call.id
        args = json.loads(call.args.decode()) if call.args else {}

        logger.info("ZAP tool call", tool=tool_name, id=tool_id)

        try:
            result = await self._execute_tool(tool_name, args)
            return bootnode_capnp.ToolResult.new_message(
                id=tool_id,
                content=json.dumps(result).encode(),
                error="",
            )
        except Exception as e:
            logger.error("Tool call failed", tool=tool_name, error=str(e))
            return bootnode_capnp.ToolResult.new_message(
                id=tool_id,
                content=b"",
                error=str(e),
            )

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> Any:
        """Execute tool by name with args. Routes to bootnode services."""
        # Import services lazily to avoid circular imports
        from bootnode.core.chains import ChainRegistry, RPCClient

        if name == "rpc_call":
            chain = args["chain"]
            network = args.get("network", "mainnet")
            method = args["method"]
            params = args.get("params", [])

            if not ChainRegistry.is_supported(chain, network):
                raise ValueError(f"Chain not supported: {chain}/{network}")

            async with RPCClient(chain, network) as rpc:
                result = await rpc.call(method, params)
            return {"result": result, "chain": chain, "network": network, "method": method}

        elif name == "get_token_balances":
            # TODO: Implement via token service
            return {"balances": [], "chain": args["chain"]}

        elif name == "get_token_metadata":
            # TODO: Implement via token service
            return {"contract": args["contract"], "chain": args["chain"]}

        elif name == "get_nfts_owned":
            # TODO: Implement via NFT service
            return {"nfts": [], "chain": args["chain"]}

        elif name == "get_nft_metadata":
            # TODO: Implement via NFT service
            return {"contract": args["contract"], "token_id": args["token_id"]}

        elif name == "create_smart_wallet":
            # TODO: Implement via wallet service
            return {"address": "0x...", "owner": args["owner"], "chain": args["chain"]}

        elif name == "get_smart_wallet":
            # TODO: Implement via wallet service
            return {"address": args["address"], "chain": args["chain"]}

        elif name == "create_webhook":
            # TODO: Implement via webhook service
            return {"id": "wh_...", "url": args["url"], "event_type": args["event_type"]}

        elif name == "list_webhooks":
            # TODO: Implement via webhook service
            return {"webhooks": []}

        elif name == "delete_webhook":
            # TODO: Implement via webhook service
            return {"success": True}

        elif name == "estimate_gas":
            chain = args["chain"]
            network = args.get("network", "mainnet")

            if not ChainRegistry.is_supported(chain, network):
                raise ValueError(f"Chain not supported: {chain}")

            async with RPCClient(chain, network) as rpc:
                gas_price = await rpc.get_gas_price()
            return {"chain": chain, "gas_price": hex(gas_price), "gas_price_gwei": gas_price / 1e9}

        else:
            raise ValueError(f"Unknown tool: {name}")

    async def listResources(self, _context, **_kwargs):
        """List available resources."""
        resources_msg = bootnode_capnp.ResourceList.new_message()
        resources_list = resources_msg.init("resources", len(self._resources))

        for i, resource in enumerate(self._resources):
            resources_list[i].uri = resource["uri"]
            resources_list[i].name = resource["name"]
            resources_list[i].description = resource["description"]
            resources_list[i].mimeType = resource["mimeType"]

        return resources_msg

    async def readResource(self, uri, _context, **_kwargs):
        """Read a resource by URI."""
        from bootnode.core.chains import ChainRegistry

        if uri == "bootnode://chains":
            all_chains = ChainRegistry.get_all_chains()
            chains_data = [
                {
                    "name": chain.name,
                    "slug": chain.slug,
                    "type": chain.chain_type.value,
                    "networks": list(chain.networks.keys()),
                }
                for chain in all_chains.values()
            ]
            content_msg = bootnode_capnp.ResourceContent.new_message(
                uri=uri,
                mimeType="application/json",
            )
            content_msg.content.text = json.dumps(chains_data)
            return content_msg

        elif uri == "bootnode://usage":
            # TODO: Get actual usage from billing service
            content_msg = bootnode_capnp.ResourceContent.new_message(
                uri=uri,
                mimeType="application/json",
            )
            content_msg.content.text = json.dumps({
                "requests": 0,
                "compute_units": 0,
                "period": "current",
            })
            return content_msg

        elif uri == "bootnode://config":
            content_msg = bootnode_capnp.ResourceContent.new_message(
                uri=uri,
                mimeType="application/json",
            )
            content_msg.content.text = json.dumps({
                "version": "2.0.0",
                "rate_limit": 1000,
            })
            return content_msg

        else:
            raise ValueError(f"Unknown resource: {uri}")

    async def subscribe(self, uri, _context, **_kwargs):
        """Subscribe to resource updates."""
        # TODO: Implement resource subscription
        raise NotImplementedError("Resource subscription not yet implemented")

    async def listPrompts(self, _context, **_kwargs):
        """List available prompts (none for bootnode)."""
        return bootnode_capnp.PromptList.new_message()

    async def getPrompt(self, name, args, _context, **_kwargs):
        """Get prompt messages (not implemented)."""
        raise NotImplementedError("Prompts not supported")

    async def log(self, level, message, _data, _context, **_kwargs):
        """Handle log messages from clients."""
        level_map = {0: "debug", 1: "info", 2: "warning", 3: "error"}
        log_level = level_map.get(level, "info")
        getattr(logger, log_level)("ZAP client log", message=message)


class ZapServer:
    """Native ZAP TCP server for bootnode."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9999,
    ) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.Server | None = None
        self._running = False
        self._task: asyncio.Task | None = None

    async def _handle_connection(self, stream: capnp.AsyncIoStream) -> None:
        """Handle a new ZAP client connection."""
        logger.info("ZAP client connected", host=self.host, port=self.port)
        try:
            await capnp.TwoPartyServer(stream, bootstrap=BootnodeZapImpl()).on_disconnect()
        except Exception as e:
            logger.error("ZAP connection error", error=str(e))
        finally:
            logger.info("ZAP client disconnected")

    async def _serve(self) -> None:
        """Inner serve loop — all capnp ops must run inside kj_loop context."""
        self._server = await capnp.AsyncIoStream.create_server(
            self._handle_connection,
            self.host,
            self.port,
        )
        self._running = True
        logger.info("ZAP server started", host=self.host, port=self.port, url=f"zap://{self.host}:{self.port}")
        try:
            async with self._server:
                await asyncio.Future()  # run until cancelled
        finally:
            self._running = False

    async def start(self) -> None:
        """Start the ZAP server in a background task inside its own kj_loop."""
        if self._running:
            return

        async def _run_with_kj_loop() -> None:
            async with capnp.kj_loop():
                await self._serve()

        self._task = asyncio.create_task(_run_with_kj_loop())

        # Wait up to 1 s for the server to signal it is running
        for _ in range(20):
            await asyncio.sleep(0.05)
            if self._running:
                return

        raise RuntimeError(f"ZAP server failed to start on {self.host}:{self.port}")

    async def serve_forever(self) -> None:
        """Compatibility shim — start (non-blocking) then wait for the task."""
        await self.start()
        if self._task:
            await self._task

    async def stop(self) -> None:
        """Stop the ZAP server."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._running = False
        self._task = None
        logger.info("ZAP server stopped")


# Global server instance
_zap_server: ZapServer | None = None


async def start_zap_server(
    host: str | None = None,
    port: int | None = None,
) -> ZapServer:
    """Start the global ZAP server inside a background task with its own kj_loop.

    Args:
        host: Bind address (default: 0.0.0.0 or ZAP_HOST env var)
        port: Port number (default: 9999 or ZAP_PORT env var)

    Returns:
        Running ZapServer instance
    """
    global _zap_server

    if _zap_server is not None:
        return _zap_server

    _host = host or os.environ.get("ZAP_HOST", "0.0.0.0")
    _port = port or int(os.environ.get("ZAP_PORT", "9999"))

    _zap_server = ZapServer(host=_host, port=_port)
    await _zap_server.start()  # non-blocking — spawns background task
    return _zap_server


async def stop_zap_server() -> None:
    """Stop the global ZAP server."""
    global _zap_server

    if _zap_server:
        await _zap_server.stop()
        _zap_server = None
