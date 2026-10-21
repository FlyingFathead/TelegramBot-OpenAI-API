from __future__ import annotations

import ast
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from openai_reasoning_compat import apply_reasoning_effort  # noqa: E402


def _load_payload_builder(function_specs):
    """Load only the pure payload-builder functions without bot runtime imports."""
    source_path = SRC_DIR / "text_message_handler.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    wanted = {"model_supports_temperature", "build_openai_tools", "build_chat_payload"}
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)

    namespace = {
        "apply_reasoning_effort": apply_reasoning_effort,
        "custom_functions": function_specs,
    }
    exec(compile(module, str(source_path), "exec"), namespace)
    return namespace["build_chat_payload"]


class _Bot:
    def __init__(self, model: str, reasoning_effort: str):
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.temperature = 0.9
        self.logger = logging.getLogger("payload-test")


def test_gpt6_luna_keeps_existing_custom_function_tools_and_forces_none() -> None:
    functions = [
        {
            "name": "existing_chatkeke_tool",
            "description": "existing tool",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ]
    build_chat_payload = _load_payload_builder(functions)
    messages = [{"role": "user", "content": "hello"}]

    payload = build_chat_payload(_Bot("gpt-6-luna", "medium"), messages)

    assert payload["model"] == "gpt-6-luna"
    assert payload["messages"] == messages
    assert payload["tools"] == [{"type": "function", "function": functions[0]}]
    assert payload["tool_choice"] == "auto"
    assert payload["parallel_tool_calls"] is False
    assert payload["reasoning_effort"] == "none"
    assert "temperature" not in payload


def test_gpt56_tool_payload_honors_configured_reasoning() -> None:
    functions = [
        {
            "name": "existing_chatkeke_tool",
            "description": "existing tool",
            "parameters": {"type": "object", "properties": {}},
        }
    ]
    build_chat_payload = _load_payload_builder(functions)

    payload = build_chat_payload(
        _Bot("gpt-5.6-luna", "medium"),
        [{"role": "user", "content": "hello"}],
    )

    assert payload["tools"][0]["function"]["name"] == "existing_chatkeke_tool"
    assert payload["reasoning_effort"] == "medium"
