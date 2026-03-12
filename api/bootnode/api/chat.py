"""AI Chat API — streaming chat with infrastructure control via ZAP/MCP tools.

Provides /v1/chat/* endpoints for the embedded AI assistant in the dashboard.
Proxies to Hanzo LLM gateway with bootnode-specific system prompt and tool definitions.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from bootnode.api.deps import ProjectDep
from bootnode.config import get_settings
from bootnode.core.cache import redis_client

router = APIRouter()
settings = get_settings()
logger = structlog.get_logger()


# =============================================================================
# Models
# =============================================================================


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str

    @property
    def safe_content(self) -> str:
        """Truncate content to prevent abuse."""
        return self.content[:8192]


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = True
    model: str | None = None

    def validated_messages(self) -> list[dict[str, str]]:
        """Return messages with validation applied."""
        # Cap conversation length to prevent context abuse
        recent = self.messages[-20:]  # max 20 turns
        return [{"role": m.role, "content": m.safe_content} for m in recent]


# =============================================================================
# System prompt for infrastructure-aware AI
# =============================================================================

SYSTEM_PROMPT = """\
You are the Bootnode AI assistant — an expert in blockchain infrastructure management.
You help users manage their blockchain nodes, services, fleets, and observability.

You have access to the following infrastructure tools:

**RPC & Blockchain**
- rpc_call: Execute JSON-RPC on any supported chain
- get_token_balances: Get ERC-20 balances for an address
- get_nfts_owned: Get NFTs owned by an address
- create_smart_wallet: Create ERC-4337 smart wallet
- estimate_gas: Get gas prices for a chain

**Fleet Management**
- fleet_list: List validator fleets across clusters
- fleet_get: Get fleet status including nodes and endpoints
- fleet_scale: Scale a fleet to target replica count
- fleet_restart: Rolling restart fleet pods

**Service Management**
- service_list: List all deployed infrastructure services
- service_deploy: Deploy or update a service (explorer, bridge, safe, etc.)
- service_scale: Scale a service
- service_logs: Get logs from a service

**Observability**
- o11y_health: Aggregate health across all services
- o11y_metrics: Platform metrics (rps, latency, error rate)
- o11y_logs: Search aggregated logs via Loki
- o11y_alerts: Active alerts and incidents

When users ask about their infrastructure, use the appropriate tools.
When users ask to perform actions (scale, restart, deploy), confirm before executing.
Be concise and direct. Use code blocks for RPC responses and log output.
Reference specific services, chains, and networks by name.
"""


# =============================================================================
# Endpoints
# =============================================================================


CHAT_RATE_LIMIT = 20  # requests per minute per project


@router.post("/completions")
async def chat_completions(
    request: ChatRequest,
    project: ProjectDep,
) -> Any:
    """AI chat completions with infrastructure context.

    Proxies to Hanzo AI gateway (api.hanzo.ai) with bootnode system prompt prepended.
    Supports streaming (SSE) and non-streaming responses.
    Rate limited per project: 20 req/min.
    """
    # Per-project rate limiting for chat (expensive LLM calls)
    rate_key = f"chat_rate:{project.id}"
    allowed, remaining = await redis_client.rate_limit_check(
        rate_key, CHAT_RATE_LIMIT
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Chat rate limit exceeded (20 req/min)",
            headers={"X-RateLimit-Remaining": "0", "Retry-After": "60"},
        )

    llm_url = os.getenv("LLM_GATEWAY_URL", "https://api.hanzo.ai")
    llm_key = os.getenv("HANZO_AI_API_KEY", "")
    if not llm_key:
        logger.error("HANZO_AI_API_KEY not configured — chat disabled")
        return {"error": "AI chat not configured", "status": 503}
    model = request.model or os.getenv("BOOTNODE_CHAT_MODEL", "zen-70b")

    # Prepend system prompt with validated/truncated messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *request.validated_messages(),
    ]

    payload = {
        "model": model,
        "messages": messages,
        "stream": request.stream,
        "max_tokens": 4096,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {llm_key}",
    }

    if request.stream:
        return StreamingResponse(
            _stream_response(llm_url, payload, headers),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{llm_url}/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        if resp.status_code != 200:
            logger.error("LLM upstream error", status=resp.status_code)
            return {"error": "AI service unavailable", "status": resp.status_code}
        return resp.json()


async def _stream_response(
    llm_url: str,
    payload: dict,
    headers: dict,
) -> Any:
    """Stream SSE chunks from LLM gateway."""
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{llm_url}/v1/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            async for chunk in resp.aiter_bytes():
                yield chunk


@router.get("/models")
async def list_chat_models(
    project: ProjectDep,
) -> dict[str, Any]:
    """List available chat models."""
    return {
        "models": [
            {"id": "zen-70b", "name": "Zen 70B", "description": "Fast, capable general model", "default": True},
            {"id": "zen-405b", "name": "Zen 405B", "description": "Most capable model for complex tasks"},
            {"id": "zen-8b", "name": "Zen 8B", "description": "Lightweight model for simple queries"},
        ],
        "default": "zen-70b",
    }
