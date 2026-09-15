"""Exports Strands' built-in agent spans to AMP over OTLP/HTTP.

Strands resolves the global tracer provider, so installing one here is all the
wiring its instrumentation needs. Requires AMP's auto-instrumentation to be
disabled on the component, otherwise both export the same spans.
"""

import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

_TRACES_PATH = "/v1/traces"
_configured = False


def _traces_endpoint(base: str) -> str:
    base = base.rstrip("/")
    return base if base.endswith(_TRACES_PATH) else base + _TRACES_PATH


def setup() -> None:
    global _configured
    if _configured:
        return

    endpoint = (os.environ.get("AMP_OTEL_ENDPOINT") or "").strip()
    api_key = (os.environ.get("AMP_AGENT_API_KEY") or "").strip()
    if not endpoint or not api_key:
        logger.info("AMP tracing env vars not set, skipping telemetry setup")
        return

    resource = Resource.create(
        {"service.name": os.environ.get("OTEL_SERVICE_NAME", "strands-simple")}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=_traces_endpoint(endpoint),
                headers={"x-amp-api-key": api_key},
            )
        )
    )
    trace.set_tracer_provider(provider)
    _configured = True
    logger.info("OTLP exporter configured for AMP")
