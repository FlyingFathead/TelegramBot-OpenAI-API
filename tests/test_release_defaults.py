from __future__ import annotations

import configparser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_v086_defaults_to_gpt6_luna_with_none_reasoning() -> None:
    config = configparser.ConfigParser()
    config.read(ROOT_DIR / "config" / "config.ini")

    assert (ROOT_DIR / "VERSION").read_text(encoding="utf-8").strip() == "0.8.6"
    assert config["DEFAULT"].get("Model") == "gpt-6-luna"
    assert config["DEFAULT"].get("ReasoningEffort") == "none"
    assert config["ModelAutoSwitch"].get("PremiumModel") == "gpt-6-luna"

    main_source = (ROOT_DIR / "src" / "main.py").read_text(encoding="utf-8")
    ddg_source = (ROOT_DIR / "src" / "api_get_duckduckgo_search.py").read_text(encoding="utf-8")
    assert "self.config.get('Model', 'gpt-6-luna')" in main_source
    assert 'DEFAULT_MODEL = "gpt-6-luna"' in ddg_source


def test_elasticsearch_rag_still_feeds_tool_enabled_chat_payload() -> None:
    source = (ROOT_DIR / "src" / "text_message_handler.py").read_text(encoding="utf-8")

    # Regression guard: the RAG/action-token path must still feed the exact
    # message list used by the existing tool-enabled Chat Completions request.
    assert 'chat_history_with_es_context = [{"role": "system", "content": "Elasticsearch RAG data: " + es_context}] + chat_history_with_system_message' in source
    assert 'payload = build_chat_payload(bot, chat_history_with_es_context)' in source
