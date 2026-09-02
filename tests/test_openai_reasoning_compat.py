import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from openai_reasoning_compat import (  # noqa: E402
    apply_reasoning_effort,
    resolve_reasoning_effort,
    supported_reasoning_efforts,
)


def test_default_omits_parameter_for_every_model():
    for model in ("gpt-5.6-luna", "gpt-5.4-mini", "gpt-4o-mini", "gpt-3.5-turbo"):
        payload = {"model": model}
        apply_reasoning_effort(payload, model, "default")
        assert "reasoning_effort" not in payload


def test_gpt56_accepts_max():
    payload = {"model": "gpt-5.6-luna"}
    apply_reasoning_effort(payload, "gpt-5.6-luna", "max")
    assert payload["reasoning_effort"] == "max"




def test_luna_with_function_tools_forces_none_from_default():
    payload = {"model": "gpt-5.6-luna", "tools": [{"type": "function"}]}
    apply_reasoning_effort(
        payload,
        "gpt-5.6-luna",
        "default",
        has_function_tools=True,
    )
    assert payload["reasoning_effort"] == "none"


def test_luna_with_function_tools_forces_none_from_higher_effort(caplog):
    payload = {"model": "gpt-5.6-luna", "tools": [{"type": "function"}]}
    with caplog.at_level(logging.WARNING):
        apply_reasoning_effort(
            payload,
            "gpt-5.6-luna",
            "medium",
            has_function_tools=True,
            logger=logging.getLogger("test"),
        )
    assert payload["reasoning_effort"] == "none"
    assert "requires ReasoningEffort=none" in caplog.text


def test_luna_without_function_tools_can_use_higher_effort():
    payload = {"model": "gpt-5.6-luna"}
    apply_reasoning_effort(
        payload,
        "gpt-5.6-luna",
        "medium",
        has_function_tools=False,
    )
    assert payload["reasoning_effort"] == "medium"


def test_gpt54_rejects_max_without_malformed_payload(caplog):
    payload = {"model": "gpt-5.4-mini"}
    with caplog.at_level(logging.WARNING):
        apply_reasoning_effort(payload, "gpt-5.4-mini", "max", logger=logging.getLogger("test"))
    assert "reasoning_effort" not in payload
    assert "not supported" in caplog.text


def test_gpt54_accepts_xhigh():
    assert resolve_reasoning_effort("gpt-5.4-mini", "xhigh") == "xhigh"


def test_gpt51_accepts_high_but_not_xhigh():
    assert resolve_reasoning_effort("gpt-5.1", "high") == "high"
    assert resolve_reasoning_effort("gpt-5.1", "xhigh") is None


def test_legacy_models_never_receive_field():
    for model in ("gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo", "gpt-5.3-chat-latest"):
        payload = {"model": model}
        apply_reasoning_effort(payload, model, "medium")
        assert "reasoning_effort" not in payload


def test_original_gpt5_uses_minimal_vocabulary():
    assert "minimal" in supported_reasoning_efforts("gpt-5")
    assert resolve_reasoning_effort("gpt-5", "minimal") == "minimal"
    assert resolve_reasoning_effort("gpt-5", "none") is None


def test_pro_models_are_not_treated_as_chat_completions_compatible():
    assert supported_reasoning_efforts("gpt-5.4-pro") is None
    assert supported_reasoning_efforts("gpt-5.5-pro") is None
