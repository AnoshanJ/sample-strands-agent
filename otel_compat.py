"""Workaround for two crashes in OpenLLMetry's Bedrock instrumentor (0.62.3).

`is_guardrail_activated` reads a missing `amazon-bedrock-guardrailAction` key as
"guardrail activated", and the guardrail helpers dereference metric counters
that the same package sets to None whenever TRACELOOP_METRICS_ENABLED=false.
Drop this once upstream fixes it.
"""

import functools
import logging

logger = logging.getLogger(__name__)

_METRICS = (
    "token_histogram",
    "choice_counter",
    "duration_histogram",
    "exception_counter",
    "guardrail_activation",
    "guardrail_latency_histogram",
    "guardrail_coverage",
    "guardrail_sensitive_info",
    "guardrail_topic",
    "guardrail_content",
    "guardrail_words",
    "prompt_caching",
)


class _NoopMetric:
    def add(self, *args, **kwargs):
        pass

    def record(self, *args, **kwargs):
        pass


def _is_guardrail_activated(response) -> bool:
    for message in response.get("results", []):
        if message.get("completionReason") == "CONTENT_FILTERED":
            return True
    if response.get("stopReason") == "guardrail_intervened":
        return True
    return response.get("amazon-bedrock-guardrailAction", "NONE") != "NONE"


def _fill_missing_metrics(metric_params) -> None:
    for name in _METRICS:
        if getattr(metric_params, name, False) is None:
            setattr(metric_params, name, _NoopMetric())


def _guarded(func):
    @functools.wraps(func)
    def wrapper(span, response, vendor, model, metric_params, *args, **kwargs):
        _fill_missing_metrics(metric_params)
        return func(span, response, vendor, model, metric_params, *args, **kwargs)

    return wrapper


def apply() -> None:
    try:
        from opentelemetry.instrumentation import bedrock
        from opentelemetry.instrumentation.bedrock import guardrail
    except ImportError:
        return

    guardrail.is_guardrail_activated = _is_guardrail_activated
    # bedrock/__init__.py binds these by value, so both modules need patching.
    for name in ("guardrail_converse", "guardrail_handling"):
        wrapped = _guarded(getattr(guardrail, name))
        setattr(guardrail, name, wrapped)
        setattr(bedrock, name, wrapped)
    logger.info("Patched OpenLLMetry Bedrock guardrail instrumentation")
