"""ZAP Protocol REST Endpoints.

ZAP (Zero-Copy App Proto) is a Cap'n Proto-based binary RPC protocol.
Bootnode implements native ZAP - connect directly via `zap://host:9999`.

This module provides REST endpoints for:
1. ZAP connection info and schema export
2. Health checks for ZAP discovery
3. Tool/resource manifests for documentation
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from bootnode.api.deps import ApiKeyDep
from bootnode.config import get_settings

router = APIRouter()
settings = get_settings()
logger = structlog.get_logger()


# =============================================================================
# Models
# =============================================================================


class ZapConnectionInfo(BaseModel):
    """ZAP connection information."""

    protocol: str = "zap"
    host: str
    port: int
    url: str
    transport: str = "tcp"


class ZapServerInfo(BaseModel):
    """ZAP server capabilities."""

    name: str = "bootnode"
    version: str = "2.0.0"
    capabilities: dict[str, bool]
    tools_count: int
    resources_count: int


# =============================================================================
# REST Endpoints
# =============================================================================


@router.get("/connect")
async def get_zap_connection(_api_key: ApiKeyDep) -> dict[str, Any]:
    """Get ZAP connection information.

    Connect to bootnode's native ZAP server for high-performance RPC:
    ```python
    from hanzo_zap import Client

    async with Client.connect("zap://api.bootno.de:9999") as client:
        tools = await client.list_tools()
        result = await client.call_tool("rpc_call", {
            "chain": "ethereum",
            "method": "eth_blockNumber"
        })
    ```
    """
    host = settings.zap_host if settings.zap_host != "0.0.0.0" else "api.bootno.de"
    port = settings.zap_port

    return {
        "connection": ZapConnectionInfo(
            host=host,
            port=port,
            url=f"zap://{host}:{port}",
        ).model_dump(),
        "status": "available" if settings.zap_enabled else "disabled",
        "example": {
            "python": f'client = await Client.connect("zap://{host}:{port}")',
            "rust": f'let client = zap::Client::connect("zap://{host}:{port}").await?;',
            "go": f'client, err := zap.Connect("zap://{host}:{port}")',
        },
    }


@router.get("/info")
async def get_zap_server_info(_api_key: ApiKeyDep) -> dict[str, Any]:
    """Get ZAP server information and capabilities."""
    return {
        "server": ZapServerInfo(
            capabilities={
                "tools": True,
                "resources": True,
                "prompts": False,
                "logging": True,
            },
            tools_count=11,
            resources_count=3,
        ).model_dump(),
        "protocol": {
            "name": "ZAP",
            "version": "1.0.0",
            "transport": "Cap'n Proto RPC over TCP",
            "schema": "zap.capnp",
        },
    }


@router.get("/tools")
async def list_zap_tools(_api_key: ApiKeyDep) -> dict[str, Any]:
    """List available ZAP tools.

    Tools are the primary way to interact with bootnode via ZAP.
    Each tool has a name, description, and JSON Schema for arguments.
    """
    tools = [
        {
            "name": "rpc_call",
            "description": "Execute JSON-RPC on any supported blockchain",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chain": {"type": "string", "description": "Chain name (ethereum, polygon, etc.)"},
                    "network": {"type": "string", "default": "mainnet"},
                    "method": {"type": "string", "description": "RPC method"},
                    "params": {"type": "array", "default": []},
                },
                "required": ["chain", "method"],
            },
        },
        {
            "name": "get_token_balances",
            "description": "Get all ERC-20 token balances for an address",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "chain": {"type": "string"},
                    "network": {"type": "string", "default": "mainnet"},
                },
                "required": ["address", "chain"],
            },
        },
        {
            "name": "get_nfts_owned",
            "description": "Get all NFTs owned by an address",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "chain": {"type": "string"},
                    "network": {"type": "string", "default": "mainnet"},
                },
                "required": ["address", "chain"],
            },
        },
        {
            "name": "create_smart_wallet",
            "description": "Create an ERC-4337 smart wallet",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Owner EOA address"},
                    "chain": {"type": "string"},
                    "network": {"type": "string", "default": "mainnet"},
                },
                "required": ["owner", "chain"],
            },
        },
        {
            "name": "estimate_gas",
            "description": "Get current gas prices for a chain",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chain": {"type": "string"},
                },
                "required": ["chain"],
            },
        },
    ]

    return {
        "tools": tools,
        "total": len(tools),
        "note": "Connect via ZAP for full tool list with all parameters",
    }


@router.get("/resources")
async def list_zap_resources(_api_key: ApiKeyDep) -> dict[str, Any]:
    """List available ZAP resources."""
    resources = [
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

    return {
        "resources": resources,
        "total": len(resources),
    }


@router.get("/health")
async def zap_health() -> dict[str, str]:
    """Health check for ZAP server."""
    return {
        "status": "ok" if settings.zap_enabled else "disabled",
        "service": "bootnode-zap",
        "port": str(settings.zap_port),
    }


@router.get("/schema")
async def get_zap_schema(_api_key: ApiKeyDep) -> dict[str, Any]:
    """Get the bootnode ZAP schema.

    The schema defines the full RPC interface for bootnode.
    Returns the clean whitespace-significant .zap format.
    Use `zapc compile bootnode.zap` to generate .capnp for code generation.
    """
    from pathlib import Path

    schema_path = Path(__file__).parent.parent / "zap" / "bootnode.zap"
    schema_content = ""
    if schema_path.exists():
        schema_content = schema_path.read_text()

    return {
        "schema": schema_content,
        "format": "zap",
        "version": "2.0.0",
        "interfaces": ["Bootnode"],
        "compile": "zapc compile bootnode.zap --out=bootnode.capnp",
    }


@router.get("/schema.capnp")
async def get_capnp_schema(_api_key: ApiKeyDep) -> dict[str, Any]:
    """Get the compiled Cap'n Proto schema.

    Pre-compiled version for direct use with pycapnp, capnp-rust, etc.
    """
    from pathlib import Path

    schema_path = Path(__file__).parent.parent / "zap" / "bootnode.capnp"
    schema_content = ""
    if schema_path.exists():
        schema_content = schema_path.read_text()

    return {
        "schema": schema_content,
        "format": "capnp",
        "version": "2.0.0",
    }
