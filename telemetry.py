"""Ships Strands' built-in agent spans to AMP over OTLP/HTTP."""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup() -> None:
    endpoint = (os.environ.get("AMP_OTEL_ENDPOINT") or "").strip().rstrip("/")
    api_key = (os.environ.get("AMP_AGENT_API_KEY") or "").strip()
    if not endpoint or not api_key:
        return
    if not endpoint.endswith("/v1/traces"):
        endpoint += "/v1/traces"

    resource = Resource.create(
        {"service.name": os.environ.get("OTEL_SERVICE_NAME", "strands-agent")}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=endpoint, headers={"x-amp-api-key": api_key})
        )
    )
    trace.set_tracer_provider(provider)
