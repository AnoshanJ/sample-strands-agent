"""Workaround for a crash in OpenLLMetry's Bedrock instrumentor (0.62.3).

`is_guardrail_activated` reads a missing `amazon-bedrock-guardrailAction` key as
"guardrail activated", then increments a counter the same package sets to None
whenever TRACELOOP_METRICS_ENABLED=false. Drop this once upstream fixes it.
"""

import logging

logger = logging.getLogger(__name__)


def _is_guardrail_activated(response) -> bool:
    for message in response.get("results", []):
        if message.get("completionReason") == "CONTENT_FILTERED":
            return True
    if response.get("stopReason") == "guardrail_intervened":
        return True
    return response.get("amazon-bedrock-guardrailAction", "NONE") != "NONE"


def apply() -> None:
    try:
        from opentelemetry.instrumentation.bedrock import guardrail
    except ImportError:
        return
    guardrail.is_guardrail_activated = _is_guardrail_activated
    logger.info("Patched Bedrock instrumentor guardrail activation check")
