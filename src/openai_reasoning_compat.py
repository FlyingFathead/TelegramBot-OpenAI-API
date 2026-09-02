"""Compatibility helpers for OpenAI Chat Completions reasoning effort.

ChatKeke supports a wide range of old and new model names.  The
``reasoning_effort`` field must therefore be opt-in and model-aware: older
models may reject it, and supported effort values differ between model
families.

Unknown models are intentionally treated as unsupported.  That is the safe
backwards-compatible behaviour: omit the optional field rather than risk a
400 response from an older or third-party model endpoint.
"""

from __future__ import annotations

from typing import Optional


# Explicitly documented Chat Completions-compatible model families.
# Keep this conservative.  Unknown/future models simply use their API default.
_REASONING_EFFORTS_BY_PREFIX = (
    ("gpt-5.6", ("none", "low", "medium", "high", "xhigh", "max")),
    ("gpt-5.5", ("none", "low", "medium", "high", "xhigh")),
    ("gpt-5.4", ("none", "low", "medium", "high", "xhigh")),
    ("gpt-5.2", ("none", "low", "medium", "high", "xhigh")),
    ("gpt-5.1", ("none", "low", "medium", "high")),
)

# Original GPT-5 used ``minimal`` instead of ``none``.  Keep this separate so
# names such as gpt-5-mini / gpt-5-chat-latest are not accidentally matched.
_GPT5_BASE_EFFORTS = ("minimal", "low", "medium", "high")

_DEFAULT_SENTINELS = {"", "auto", "default", "model-default", "model_default"}


def supported_reasoning_efforts(model: str) -> Optional[tuple[str, ...]]:
    """Return supported Chat Completions reasoning-effort values for *model*.

    ``None`` means "do not send reasoning_effort".  In particular, Pro models
    in the older GPT-5.x families are Responses-API-only and are deliberately
    excluded from this Chat Completions compatibility helper.
    """
    name = (model or "").strip().lower()
    if not name:
        return None

    if "-pro" in name:
        return None

    for prefix, efforts in _REASONING_EFFORTS_BY_PREFIX:
        if name.startswith(prefix):
            return efforts

    # Match the original gpt-5 alias and dated snapshots, but not gpt-5-mini,
    # gpt-5-nano, gpt-5-chat-latest, etc. unless explicitly added later.
    if name == "gpt-5" or name.startswith("gpt-5-20"):
        return _GPT5_BASE_EFFORTS

    return None


def resolve_reasoning_effort(
    model: str,
    configured_effort: str | None,
    *,
    has_function_tools: bool = False,
    logger=None,
) -> Optional[str]:
    """Resolve a configured effort to a value safe to send to Chat Completions.

    ``default``/``auto``/blank normally means omit the parameter and let the
    selected model use its own default. GPT-5.6 Luna is the exception when
    function tools are attached to Chat Completions: its default/higher effort
    is rejected by that endpoint, so this helper explicitly returns ``none``.

    Explicit values are otherwise sent only when the selected model is in the
    compatibility table *and* that exact value is supported. Unsupported values
    are omitted and a warning is logged.
    """
    effort = (configured_effort or "default").strip().lower()
    name = (model or "").strip().lower()

    # Live API behaviour observed for GPT-5.6 Luna on /v1/chat/completions:
    # function tools cannot be combined with Luna's default/higher reasoning
    # efforts. The endpoint explicitly requires reasoning_effort="none" (or
    # migration to /v1/responses). Force the safe Chat Completions value when
    # function tools are present so a config value cannot turn every tool-enabled
    # request into HTTP 400.
    if has_function_tools and name.startswith("gpt-5.6-luna"):
        if effort not in _DEFAULT_SENTINELS and effort != "none" and logger is not None:
            logger.warning(
                "GPT-5.6 Luna with function tools on Chat Completions requires "
                "ReasoningEffort=none; forcing none instead of configured value %s. "
                "Use the Responses API for higher reasoning effort with tools.",
                effort,
            )
        elif effort in _DEFAULT_SENTINELS and logger is not None:
            logger.info(
                "GPT-5.6 Luna with function tools on Chat Completions cannot use "
                "its default reasoning effort; explicitly setting reasoning_effort=none."
            )
        return "none"

    if effort in _DEFAULT_SENTINELS:
        return None

    supported = supported_reasoning_efforts(model)
    if supported is None:
        if logger is not None:
            logger.warning(
                "ReasoningEffort=%s requested, but model %s is not in the "
                "Chat Completions reasoning-effort compatibility table; "
                "omitting reasoning_effort for backwards compatibility.",
                effort,
                model,
            )
        return None

    if effort not in supported:
        if logger is not None:
            logger.warning(
                "ReasoningEffort=%s is not supported by model %s (supported: %s); "
                "omitting reasoning_effort rather than sending an invalid request.",
                effort,
                model,
                ", ".join(supported),
            )
        return None

    return effort


def apply_reasoning_effort(
    payload: dict,
    model: str,
    configured_effort: str | None,
    *,
    has_function_tools: bool = False,
    logger=None,
) -> dict:
    """Add flat Chat Completions ``reasoning_effort`` when safe.

    The Responses API uses ``reasoning: {"effort": ...}``; ChatKeke currently
    uses ``/v1/chat/completions``, where the corresponding field is the flat
    ``reasoning_effort`` parameter.
    """
    effort = resolve_reasoning_effort(
        model,
        configured_effort,
        has_function_tools=has_function_tools,
        logger=logger,
    )
    if effort is not None:
        payload["reasoning_effort"] = effort
    return payload
