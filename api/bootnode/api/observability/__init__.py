"""Observability API — platform health, metrics, alerts, logs, and events.

Provides /v1/o11y/* endpoints for cloud.lux.network dashboard.

Backend stack (Hanzo O11y — same as Hanzo console):
  - Traces:    OTEL Collector → Datastore (otel DB)
  - Metrics:   OTEL Collector → Datastore + Prometheus :8889
  - Logs:      Loki (Promtail scrapes bootnode namespace)
  - Analytics: DataStore (bootnode DB, api_usage table)
  - Dashboards: Grafana (grafana.hanzo.ai)
"""

import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from bootnode.api.deps import ProjectDep, DbDep
from bootnode.core.datastore import datastore_client
from bootnode.core.deploy import ServiceStatus, ServiceType, get_deployer

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Models
# =============================================================================


class ServiceHealth(BaseModel):
    """Health of a single service."""

    name: str
    healthy: bool
    replicas: int
    ready_replicas: int
    latency_ms: float | None = None


class HealthOverview(BaseModel):
    """Aggregate health across all services."""

    total_services: int
    healthy: int
    unhealthy: int
    degraded: int
    uptime_percent: float
    services: list[ServiceHealth]
    checked_at: str


class MetricPoint(BaseModel):
    """A single metric data point."""

    name: str
    value: float
    unit: str
    labels: dict[str, str] = {}


class MetricsResponse(BaseModel):
    """Platform metrics snapshot."""

    requests_per_sec: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    error_rate: float
    active_connections: int
    total_requests_24h: int
    metrics: list[MetricPoint]
    collected_at: str


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Alert(BaseModel):
    """An active alert."""

    id: str
    severity: AlertSeverity
    service: str
    message: str
    metric: str | None = None
    threshold: float | None = None
    current_value: float | None = None
    fired_at: str
    resolved_at: str | None = None


class AlertRule(BaseModel):
    """Alert rule definition."""

    service: str
    metric: str
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    message: str | None = None


class AlertRuleResponse(BaseModel):
    """Created alert rule."""

    id: str
    service: str
    metric: str
    threshold: float
    severity: str
    created_at: str


class EventType(str, Enum):
    DEPLOY = "deploy"
    SCALE = "scale"
    RESTART = "restart"
    ERROR = "error"
    ALERT = "alert"
    HEALTH_CHANGE = "health_change"


class PlatformEvent(BaseModel):
    """A platform event."""

    id: str
    type: EventType
    service: str | None = None
    message: str
    metadata: dict[str, Any] = {}
    timestamp: str


class ServiceMapNode(BaseModel):
    """A node in the service dependency graph."""

    name: str
    type: str
    healthy: bool
    connections: list[str]


class LogEntry(BaseModel):
    """Aggregated log entry."""

    timestamp: str
    service: str
    level: str
    message: str
    metadata: dict[str, Any] = {}


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/health", response_model=HealthOverview)
async def get_health_overview(
    project: ProjectDep,
    fail_if_unhealthy: bool = Query(False, alias="failIfUnhealthy"),
) -> HealthOverview:
    """Aggregate health across all services and fleets.

    Mirrors console's /api/public/health pattern with optional failure conditions.
    """
    deployer = get_deployer()
    services: list[ServiceHealth] = []

    for svc in ServiceType:
        try:
            t0 = time.monotonic()
            status = await deployer.status(svc)
            latency = (time.monotonic() - t0) * 1000
            services.append(ServiceHealth(
                name=svc.value,
                healthy=status.running and status.ready_replicas > 0,
                replicas=status.replicas,
                ready_replicas=status.ready_replicas,
                latency_ms=round(latency, 2),
            ))
        except Exception:
            services.append(ServiceHealth(
                name=svc.value,
                healthy=False,
                replicas=0,
                ready_replicas=0,
            ))

    total = len(services)
    healthy = sum(1 for s in services if s.healthy)
    unhealthy = sum(1 for s in services if not s.healthy and s.replicas > 0)
    degraded = sum(1 for s in services if s.healthy and s.ready_replicas < s.replicas)
    uptime = (healthy / total * 100) if total > 0 else 0.0

    overview = HealthOverview(
        total_services=total,
        healthy=healthy,
        unhealthy=unhealthy,
        degraded=degraded,
        uptime_percent=round(uptime, 2),
        services=services,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )

    if fail_if_unhealthy and unhealthy > 0:
        from fastapi import HTTPException
        raise HTTPException(503, detail=overview.model_dump())

    return overview


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    project: ProjectDep,
) -> MetricsResponse:
    """Platform-wide metrics snapshot.

    Queries ClickHouse (Datastore) api_usage table for real metrics.
    Falls back to zeros if Datastore is unavailable.
    """
    now = datetime.now(timezone.utc)
    rps = 0.0
    p50 = 0.0
    p95 = 0.0
    p99 = 0.0
    error_rate = 0.0
    total_24h = 0

    if datastore_client.is_connected:
        try:
            row = await datastore_client.fetchone(
                """
                SELECT
                    count() / 86400 AS rps,
                    quantile(0.50)(response_time_ms) AS p50,
                    quantile(0.95)(response_time_ms) AS p95,
                    quantile(0.99)(response_time_ms) AS p99,
                    countIf(status_code >= 500) / greatest(count(), 1) AS error_rate,
                    count() AS total_24h
                FROM api_usage
                WHERE project_id = {project_id:String}
                  AND timestamp >= now() - INTERVAL 24 HOUR
                """,
                {"project_id": str(project.id)},
            )
            if row:
                rps = float(row.get("rps", 0))
                p50 = float(row.get("p50", 0))
                p95 = float(row.get("p95", 0))
                p99 = float(row.get("p99", 0))
                error_rate = float(row.get("error_rate", 0))
                total_24h = int(row.get("total_24h", 0))
        except Exception as e:
            logger.warning("Failed to query Datastore for metrics: %s", e)

    return MetricsResponse(
        requests_per_sec=round(rps, 2),
        latency_p50_ms=round(p50, 1),
        latency_p95_ms=round(p95, 1),
        latency_p99_ms=round(p99, 1),
        error_rate=round(error_rate, 4),
        active_connections=0,  # TODO: from Redis pub/sub or WS manager
        total_requests_24h=total_24h,
        metrics=[
            MetricPoint(name="rpc_requests_total", value=total_24h, unit="count"),
            MetricPoint(name="rpc_error_rate", value=round(error_rate * 100, 2), unit="percent"),
            MetricPoint(name="rpc_latency_p95", value=round(p95, 1), unit="ms"),
        ],
        collected_at=now.isoformat(),
    )


@router.get("/metrics/{service}", response_model=MetricsResponse)
async def get_service_metrics(
    service: str,
    project: ProjectDep,
) -> MetricsResponse:
    """Per-service metrics.

    TODO: Wire to per-service Prometheus metrics.
    """
    try:
        ServiceType(service)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(400, f"Unknown service: {service}")

    return MetricsResponse(
        requests_per_sec=0.0,
        latency_p50_ms=0.0,
        latency_p95_ms=0.0,
        latency_p99_ms=0.0,
        error_rate=0.0,
        active_connections=0,
        total_requests_24h=0,
        metrics=[],
        collected_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/alerts", response_model=list[Alert])
async def get_alerts(
    project: ProjectDep,
    severity: AlertSeverity | None = None,
    active_only: bool = True,
) -> list[Alert]:
    """Active alerts and recent incidents.

    TODO: Wire to alert rules engine + Redis pub/sub.
    """
    # TODO: Query alert state from DB/Redis
    return []


@router.post("/alerts", response_model=AlertRuleResponse)
async def create_alert_rule(
    rule: AlertRule,
    project: ProjectDep,
    db: DbDep,
) -> AlertRuleResponse:
    """Create an alert rule (threshold on a metric).

    TODO: Persist to DB and register with metrics poller.
    """
    import uuid
    # TODO: Persist alert rule to database
    return AlertRuleResponse(
        id=str(uuid.uuid4()),
        service=rule.service,
        metric=rule.metric,
        threshold=rule.threshold,
        severity=rule.severity.value,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/service-map", response_model=list[ServiceMapNode])
async def get_service_map(
    project: ProjectDep,
) -> list[ServiceMapNode]:
    """Service dependency graph.

    Returns nodes and their connections for visualization.
    """
    deployer = get_deployer()
    nodes: list[ServiceMapNode] = []

    # Build a static dependency map
    deps: dict[str, list[str]] = {
        "api": ["web", "indexer", "bundler", "webhook-worker", "rpc-proxy"],
        "web": [],
        "rpc-proxy": ["validator"],
        "explorer": ["rpc-proxy", "graph-node"],
        "graph-node": ["graph-postgres", "graph-ipfs", "rpc-proxy"],
        "graph-postgres": [],
        "graph-ipfs": [],
        "bridge": ["rpc-proxy"],
        "exchange": ["rpc-proxy"],
        "safe": ["safe-transaction", "safe-config"],
        "safe-transaction": ["rpc-proxy"],
        "safe-config": [],
        "mpc": ["mpc-postgres"],
        "mpc-postgres": [],
        "gateway": ["api"],
        "faucet": ["rpc-proxy"],
        "market": ["rpc-proxy", "graph-node"],
        "staking": ["rpc-proxy"],
        "validator": [],
        "indexer": [],
        "bundler": ["rpc-proxy"],
        "webhook-worker": [],
    }

    for svc in ServiceType:
        try:
            status = await deployer.status(svc)
            healthy = status.running and status.ready_replicas > 0
        except Exception:
            healthy = False

        nodes.append(ServiceMapNode(
            name=svc.value,
            type="core" if svc.value in ("api", "web", "indexer", "bundler", "webhook-worker") else "infra",
            healthy=healthy,
            connections=deps.get(svc.value, []),
        ))

    return nodes


@router.get("/logs", response_model=list[LogEntry])
async def search_logs(
    project: ProjectDep,
    q: str | None = None,
    service: str | None = None,
    level: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[LogEntry]:
    """Search aggregated logs across services.

    Queries Loki (loki.hanzo.svc:3100) for container logs from the
    bootnode namespace. Falls back to ClickHouse otel_logs table.
    """
    import os
    import httpx

    loki_url = os.getenv("LOKI_URL", "http://loki.hanzo.svc:3100")
    entries: list[LogEntry] = []

    # Build LogQL query
    label_selectors = ['namespace="bootnode"']
    if service:
        label_selectors.append(f'app="{service}"')
    logql = '{' + ','.join(label_selectors) + '}'
    if level:
        logql += f' | level="{level.upper()}"'
    if q:
        logql += f' |= "{q}"'

    params: dict[str, Any] = {
        "query": logql,
        "limit": str(limit),
        "direction": "backward",
    }
    if since:
        params["start"] = since
    if until:
        params["end"] = until

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{loki_url}/loki/api/v1/query_range", params=params)
            if resp.status_code == 200:
                data = resp.json()
                for stream in data.get("data", {}).get("result", []):
                    labels = stream.get("stream", {})
                    for ts, line in stream.get("values", []):
                        entries.append(LogEntry(
                            timestamp=datetime.fromtimestamp(
                                int(ts) / 1e9, tz=timezone.utc
                            ).isoformat(),
                            service=labels.get("app", labels.get("container", "unknown")),
                            level=labels.get("level", "info"),
                            message=line,
                            metadata=labels,
                        ))
    except Exception as e:
        logger.warning("Loki query failed, falling back to empty: %s", e)

    return entries[:limit]


@router.get("/events", response_model=list[PlatformEvent])
async def get_events(
    project: ProjectDep,
    type: EventType | None = None,
    service: str | None = None,
    limit: int = Query(50, ge=1, le=500),
) -> list[PlatformEvent]:
    """Recent platform events (deploys, scales, restarts, errors).

    TODO: Wire to events table in DB.
    """
    # TODO: Query events from database
    return []
