"""Workaround for a crash in WSO2's bundled OpenLLMetry Bedrock instrumentor.

openllmetry 0.62.3 reads a missing `amazon-bedrock-guardrailAction` key as
"guardrail activated", then increments a counter that is None because the
platform forces TRACELOOP_METRICS_ENABLED=false. Drop this once that is fixed.
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
