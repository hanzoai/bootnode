"""Bootnode API - Main application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from bootnode.api import router as api_router
from bootnode.config import get_settings
from bootnode.core.cache import redis_client
from bootnode.core.datastore import datastore_client
from bootnode.core.kms import inject_secrets
from bootnode.db.session import engine, init_db
from bootnode.ws import router as ws_router
from bootnode.zap import start_zap_server, stop_zap_server

# Load secrets from Hanzo KMS before settings
inject_secrets()

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Bootnode API", env=settings.app_env)
    await init_db()
    await redis_client.initialize()

    # Initialize DataStore (ClickHouse) - optional, won't fail startup
    try:
        await datastore_client.initialize()
        logger.info("DataStore connected")
    except Exception as e:
        logger.warning("DataStore not available", error=str(e))

    # Start native ZAP server (Cap'n Proto RPC over TCP)
    zap_server = None
    if settings.zap_enabled:
        try:
            zap_server = await start_zap_server(
                host=settings.zap_host,
                port=settings.zap_port,
            )
            logger.info(
                "ZAP server started",
                url=f"zap://{settings.zap_host}:{settings.zap_port}",
            )
        except Exception as e:
            logger.warning("ZAP server failed to start", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down Bootnode API")

    # Stop ZAP server
    if zap_server:
        try:
            await stop_zap_server()
            logger.info("ZAP server stopped")
        except Exception as e:
            logger.warning("ZAP server stop error", error=str(e))

    await engine.dispose()
    await redis_client.close()
    await datastore_client.close()


app = FastAPI(
    title="Bootnode API",
    description="Blockchain Development Platform - Multi-chain RPC, Token API, NFT API, Smart Wallets, and more",
    version="2.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# CORS - all cloud domains for white-label multi-network support
production_origins = [
    "https://bootno.de",
    "https://cloud.lux.network",
    "https://cloud.pars.network",
    "https://cloud.zoo.network",
    "https://cloud.hanzo.network",
    "https://cloud.hanzo.ai",
]
# Add frontend_url if set
if settings.frontend_url:
    origin = settings.frontend_url.rstrip("/")
    if origin not in production_origins:
        production_origins.append(origin)
# Add extra origins from ALLOWED_ORIGINS env var
for extra in settings.allowed_origins:
    origin = extra.strip().rstrip("/")
    if origin and origin not in production_origins:
        production_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else production_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)

# Include WebSocket routes
app.include_router(ws_router, prefix=f"{settings.api_prefix}/ws", tags=["WebSocket"])


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": "Bootnode API",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "operational",
    }
