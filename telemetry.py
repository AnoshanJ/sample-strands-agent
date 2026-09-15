"""Ships Strands' built-in agent spans to AMP over OTLP/HTTP."""

import os

from strands.telemetry import StrandsTelemetry


def setup() -> None:
    endpoint = (os.environ.get("AMP_OTEL_ENDPOINT") or "").strip().rstrip("/")
    api_key = (os.environ.get("AMP_AGENT_API_KEY") or "").strip()
    if not endpoint or not api_key:
        return
    if not endpoint.endswith("/v1/traces"):
        endpoint += "/v1/traces"
    StrandsTelemetry().setup_otlp_exporter(
        endpoint=endpoint, headers={"x-amp-api-key": api_key}
    )
