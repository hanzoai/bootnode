"""Hanzo O11y — OpenTelemetry instrumentation for Bootnode API.

Full observability stack:
  Traces  → OTEL Collector → Datastore (otel DB)
  Metrics → OTEL Collector → Datastore + Prometheus
  Logs    → OTEL Collector → Datastore + Loki

OTEL Collector endpoint: otel-collector.hanzo.svc:4317 (gRPC)

Prometheus /metrics endpoint served by this module for ServiceMonitor scraping.
"""

from __future__ import annotations

import os
import time
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Prometheus metrics (lightweight, no external dep required)
# ---------------------------------------------------------------------------

_request_count: dict[str, int] = {}
_request_errors: dict[str, int] = {}
_request_latency_sum: dict[str, float] = {}
_request_latency_count: dict[str, int] = {}
_request_latency_buckets: dict[str, dict[float, int]] = {}

LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


def _bucket_key(method: str, path: str, status: int) -> str:
    return f"{method}|{path}|{status}"


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect request metrics for /metrics endpoint."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        # Normalize path to reduce cardinality (strip IDs)
        path = _normalize_path(request.url.path)
        start = time.perf_counter()

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            duration = time.perf_counter() - start
            key = _bucket_key(method, path, status)

            _request_count[key] = _request_count.get(key, 0) + 1
            _request_latency_sum[key] = _request_latency_sum.get(key, 0.0) + duration
            _request_latency_count[key] = _request_latency_count.get(key, 0) + 1

            if status >= 500:
                err_key = f"{method}|{path}"
                _request_errors[err_key] = _request_errors.get(err_key, 0) + 1

            # Histogram buckets
            if key not in _request_latency_buckets:
                _request_latency_buckets[key] = {b: 0 for b in LATENCY_BUCKETS}
            for bucket in LATENCY_BUCKETS:
                if duration <= bucket:
                    _request_latency_buckets[key][bucket] += 1

        return response


def _normalize_path(path: str) -> str:
    """Reduce path cardinality by replacing UUIDs and hex strings with {id}."""
    import re
    # UUID pattern
    path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "{id}",
        path,
    )
    # Hex hashes (32+ chars)
    path = re.sub(r"0x[0-9a-fA-F]{40,}", "{hash}", path)
    # Numeric IDs
    path = re.sub(r"/\d+(/|$)", "/{id}\\1", path)
    return path


def render_metrics() -> str:
    """Render Prometheus text exposition format."""
    lines: list[str] = []

    # http_server_requests_total
    lines.append("# HELP http_server_requests_total Total HTTP requests")
    lines.append("# TYPE http_server_requests_total counter")
    for key, count in sorted(_request_count.items()):
        method, path, status = key.split("|")
        lines.append(
            f'http_server_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
        )

    # http_server_request_duration_seconds (histogram)
    lines.append("")
    lines.append("# HELP http_server_request_duration_seconds Request latency histogram")
    lines.append("# TYPE http_server_request_duration_seconds histogram")
    for key in sorted(_request_latency_buckets):
        method, path, status = key.split("|")
        labels = f'method="{method}",path="{path}",status="{status}"'
        buckets = _request_latency_buckets[key]
        cumulative = 0
        for bucket_le in LATENCY_BUCKETS:
            cumulative += buckets.get(bucket_le, 0)
            lines.append(
                f'http_server_request_duration_seconds_bucket{{{labels},le="{bucket_le}"}} {cumulative}'
            )
        total_count = _request_latency_count.get(key, 0)
        lines.append(
            f'http_server_request_duration_seconds_bucket{{{labels},le="+Inf"}} {total_count}'
        )
        lines.append(
            f"http_server_request_duration_seconds_sum{{{labels}}} {_request_latency_sum.get(key, 0.0):.6f}"
        )
        lines.append(
            f"http_server_request_duration_seconds_count{{{labels}}} {total_count}"
        )

    # http_server_errors_total
    lines.append("")
    lines.append("# HELP http_server_errors_total Total 5xx errors")
    lines.append("# TYPE http_server_errors_total counter")
    for key, count in sorted(_request_errors.items()):
        method, path = key.split("|")
        lines.append(
            f'http_server_errors_total{{method="{method}",path="{path}"}} {count}'
        )

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# OTEL SDK setup
# ---------------------------------------------------------------------------


def setup_otel(app: FastAPI) -> None:
    """Initialize full OTEL stack: traces + metrics + logs.

    Sends to OTEL Collector at otel-collector.hanzo.svc:4317.
    Gracefully degrades if OTEL packages not installed or endpoint not set.
    """
    endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://otel-collector.hanzo.svc:4317",
    )
    service_name = os.getenv("OTEL_SERVICE_NAME", "bootnode-api")
    service_version = os.getenv("OTEL_SERVICE_VERSION", "2.0.0")

    # Always add metrics middleware (no external deps)
    app.add_middleware(MetricsMiddleware)

    # Add /metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        return Response(
            content=render_metrics(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # OTEL SDK (traces, metrics export to collector)
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") and not os.getenv("OTEL_ENABLED"):
        logger.info("OTEL tracing disabled (no OTEL_EXPORTER_OTLP_ENDPOINT)")
        return

    try:
        from opentelemetry import trace, metrics as otel_metrics
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        resource = Resource.create({
            "service.name": service_name,
            "service.version": service_version,
            "service.namespace": "bootnode",
            "deployment.environment": os.getenv("APP_ENV", "production"),
        })

        # Traces
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
        )
        trace.set_tracer_provider(tracer_provider)

        # Metrics (OTEL metrics → collector → datastore)
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=endpoint, insecure=True),
            export_interval_millis=30000,
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        otel_metrics.set_meter_provider(meter_provider)

        # Auto-instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)

        logger.info(
            "hanzo11y: OTEL tracing + metrics enabled",
            endpoint=endpoint,
            service=service_name,
        )
    except ImportError as e:
        logger.info("OTEL SDK not installed, traces disabled", missing=str(e))
    except Exception as e:
        logger.warning("OTEL init failed", error=str(e))


def setup_otel_logging() -> None:
    """Configure OTEL log export (structured logs → collector → datastore + loki).

    Call this early, before any logging happens.
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    try:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
            OTLPLogExporter,
        )
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({
            "service.name": os.getenv("OTEL_SERVICE_NAME", "bootnode-api"),
        })

        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint, insecure=True))
        )
        set_logger_provider(logger_provider)

        # Attach OTEL handler to Python root logger
        import logging
        handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)

    except ImportError:
        pass
    except Exception as e:
        structlog.get_logger().warning("OTEL log export init failed", error=str(e))
