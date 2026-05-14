# # # api_perplexity_search.py
# # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # # https://github.com/FlyingFathead/TelegramBot-OpenAI-API/
# # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
Perplexity API helper module for ChatKeke.

Purpose:
- Query Perplexity/Sonar as an external fact-checking/search context provider.
- Return plain text back to text_message_handler.py, where it is appended into
  chat history and then summarized/formatted by the selected OpenAI model.
- Keep old public function names intact so older imports do not explode.

Important:
- This module does NOT do OpenAI tool/function calling.
- The OpenAI call here is only the optional detect_language() helper.
- detect_language() avoids temperature/max_tokens payloads for newer non-GPT-4
  model families, matching the v0.77.1 OpenAI payload rules elsewhere.
"""

import asyncio
import configparser
import html
import logging
import os
import random
import re
from typing import Any, Dict, Iterable, List, Optional

import httpx

from config_paths import CONFIG_PATH


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

DEFAULT_PERPLEXITY_ENDPOINT = "https://api.perplexity.ai/chat/completions"
DEFAULT_PERPLEXITY_MODEL = "sonar"
DEFAULT_PERPLEXITY_MAX_TOKENS = 1024
DEFAULT_PERPLEXITY_TEMPERATURE = 0.0
DEFAULT_PERPLEXITY_MAX_RETRIES = 3
DEFAULT_PERPLEXITY_RETRY_DELAY = 25
DEFAULT_PERPLEXITY_TIMEOUT = 30
DEFAULT_CHUNK_SIZE = 1000
MAX_TELEGRAM_MESSAGE_LENGTH = 4000


def _cfg_get(section: str, option: str, fallback: str) -> str:
    try:
        return config.get(section, option, fallback=fallback)
    except Exception as exc:
        logging.warning(
            "Invalid config value for [%s] %s; using fallback %r: %s",
            section,
            option,
            fallback,
            exc,
        )
        return fallback


def _cfg_getint(section: str, option: str, fallback: int) -> int:
    try:
        return config.getint(section, option, fallback=fallback)
    except Exception as exc:
        logging.warning(
            "Invalid integer config value for [%s] %s; using fallback %r: %s",
            section,
            option,
            fallback,
            exc,
        )
        return fallback


def _cfg_getfloat(section: str, option: str, fallback: float) -> float:
    try:
        return config.getfloat(section, option, fallback=fallback)
    except Exception as exc:
        logging.warning(
            "Invalid float config value for [%s] %s; using fallback %r: %s",
            section,
            option,
            fallback,
            exc,
        )
        return fallback


PERPLEXITY_ENDPOINT = _cfg_get(
    "Perplexity",
    "Endpoint",
    DEFAULT_PERPLEXITY_ENDPOINT,
).strip()

PERPLEXITY_MODEL = _cfg_get(
    "Perplexity",
    "Model",
    DEFAULT_PERPLEXITY_MODEL,
).strip()

PERPLEXITY_MAX_TOKENS = _cfg_getint(
    "Perplexity",
    "MaxTokens",
    DEFAULT_PERPLEXITY_MAX_TOKENS,
)

PERPLEXITY_TEMPERATURE = _cfg_getfloat(
    "Perplexity",
    "Temperature",
    DEFAULT_PERPLEXITY_TEMPERATURE,
)

PERPLEXITY_MAX_RETRIES = max(
    1,
    _cfg_getint("Perplexity", "MaxRetries", DEFAULT_PERPLEXITY_MAX_RETRIES),
)

PERPLEXITY_RETRY_DELAY = max(
    1,
    _cfg_getint("Perplexity", "RetryDelay", DEFAULT_PERPLEXITY_RETRY_DELAY),
)

PERPLEXITY_TIMEOUT = max(
    1,
    _cfg_getint("Perplexity", "Timeout", DEFAULT_PERPLEXITY_TIMEOUT),
)

CHUNK_SIZE = max(
    100,
    _cfg_getint("Perplexity", "ChunkSize", DEFAULT_CHUNK_SIZE),
)

# Default OpenAI model from [DEFAULT] Model in config.ini.
# Used only as a fallback if bot.model is unavailable in legacy helper paths.
DEFAULT_OPENAI_MODEL = _cfg_get(
    "DEFAULT",
    "Model",
    "",
).strip()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")


# ---------------------------------------------------------------------------
# OpenAI compatibility helpers for optional detect_language()
# ---------------------------------------------------------------------------

def openai_model_supports_temperature(model: str) -> bool:
    """
    Local ChatKeke rule:
    - gpt-4* models get temperature.
    - newer non-GPT-4/reasoning-ish model families do not.
    """
    model = (model or "").strip().lower()
    return model.startswith("gpt-4")


def openai_token_limit_key(model: str) -> str:
    """
    Local ChatKeke rule:
    - gpt-4* => max_tokens
    - newer non-GPT-4 model families => max_completion_tokens
    """
    if openai_model_supports_temperature(model):
        return "max_tokens"
    return "max_completion_tokens"


def _get_openai_api_key_from_bot(bot: Any) -> Optional[str]:
    """
    Try the bot's configured key first, then environment fallback.
    """
    key = getattr(bot, "openai_api_key", None)
    if key:
        return key
    return os.getenv("OPENAI_API_KEY")


# ---------------------------------------------------------------------------
# Perplexity API core
# ---------------------------------------------------------------------------

def _build_perplexity_payload(question: str) -> Dict[str, Any]:
    return {
        "model": PERPLEXITY_MODEL,
        "stream": False,
        "max_tokens": PERPLEXITY_MAX_TOKENS,
        "temperature": PERPLEXITY_TEMPERATURE,
        "messages": [
            {
                "role": "user",
                "content": question,
            }
        ],
    }


def _is_retryable_status(status_code: int) -> bool:
    return status_code == 408 or status_code == 409 or status_code == 429 or status_code >= 500


def _backoff_delay(attempt: int) -> float:
    """
    Exponential backoff with jitter, capped by PERPLEXITY_RETRY_DELAY.
    """
    raw_delay = (2 ** attempt) + random.uniform(0, 1)
    return min(float(PERPLEXITY_RETRY_DELAY), raw_delay)


def _perplexity_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _extract_perplexity_content(response_data: Dict[str, Any]) -> str:
    """
    Extract OpenAI-compatible Chat Completions content:
        choices[0].message.content
    """
    choices = response_data.get("choices") or []
    if not choices:
        return ""

    first_choice = choices[0] or {}
    message = first_choice.get("message") or {}
    content = message.get("content") or ""

    if isinstance(content, list):
        # Defensive support for multi-part content payloads.
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))
        return "\n".join(parts).strip()

    return str(content).strip()


async def fact_check_with_perplexity(question: str) -> Optional[Dict[str, Any]]:
    """
    Call Perplexity/Sonar and return raw JSON.

    Returns:
        dict response on success
        {"error": "..."} on known failure
        None if retries exhausted
    """
    question = (question or "").strip()
    if not question:
        logging.warning("fact_check_with_perplexity called with an empty question.")
        return {"error": "empty_question"}

    if not PERPLEXITY_API_KEY:
        logging.error("PERPLEXITY_API_KEY is not set.")
        return {"error": "missing_api_key"}

    payload = _build_perplexity_payload(question)
    headers = _perplexity_headers()

    timeout = httpx.Timeout(PERPLEXITY_TIMEOUT)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(PERPLEXITY_MAX_RETRIES):
            try:
                response = await client.post(
                    PERPLEXITY_ENDPOINT,
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError as exc:
                        logging.error(
                            "Perplexity returned non-JSON response: %s; parse error: %s",
                            response.text[:1000],
                            exc,
                        )
                        return {"error": "bad_json"}

                if _is_retryable_status(response.status_code):
                    logging.error(
                        "Perplexity retryable API error %s on attempt %d/%d: %s",
                        response.status_code,
                        attempt + 1,
                        PERPLEXITY_MAX_RETRIES,
                        response.text[:1000],
                    )
                else:
                    logging.error(
                        "Perplexity non-retryable API error %s: %s",
                        response.status_code,
                        response.text[:1000],
                    )
                    return {"error": f"http_{response.status_code}"}

            except httpx.TimeoutException as exc:
                logging.error(
                    "Timeout while calling Perplexity on attempt %d/%d: %s",
                    attempt + 1,
                    PERPLEXITY_MAX_RETRIES,
                    exc,
                )
            except httpx.RequestError as exc:
                logging.error(
                    "Request error while calling Perplexity on attempt %d/%d: %s",
                    attempt + 1,
                    PERPLEXITY_MAX_RETRIES,
                    exc,
                )
            except Exception as exc:
                logging.exception(
                    "Unexpected error while calling Perplexity on attempt %d/%d: %s",
                    attempt + 1,
                    PERPLEXITY_MAX_RETRIES,
                    exc,
                )

            if attempt < PERPLEXITY_MAX_RETRIES - 1:
                await asyncio.sleep(_backoff_delay(attempt))

    logging.error("Perplexity request failed after all retry attempts.")
    return None


async def query_perplexity(bot: Any, chat_id: Any, question: str) -> str:
    """
    Main public entry point used by text_message_handler.py.

    Note:
    - bot and chat_id are kept in the signature for compatibility.
    - chat_id is intentionally unused here; sending is handled elsewhere.
    """
    del chat_id  # Compatibility argument; intentionally unused.

    logging.info("Querying Perplexity with question: %s", question)
    response_data = await fact_check_with_perplexity(question)

    if not response_data:
        logging.error("Perplexity returned no response data.")
        return "Perplexity API request failed after retries."

    error = response_data.get("error")
    if error:
        if error == "missing_api_key":
            return "Perplexity API key is not configured."
        if error == "empty_question":
            return "No question was provided for the Perplexity query."
        if error == "bad_json":
            return "Perplexity returned an invalid non-JSON response."
        if error.startswith("http_"):
            return f"Perplexity API returned an HTTP error: {error}."
        return f"Perplexity API error: {error}."

    bot_reply_content = _extract_perplexity_content(response_data)
    if bot_reply_content:
        return bot_reply_content

    logging.warning("Perplexity response had no usable message content: %s", response_data)
    return "Received an empty response from Perplexity. Please try again."


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def smart_chunk(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """
    Split text into semi-natural chunks while trying to preserve paragraphs.
    """
    text = text or ""
    if not text.strip():
        return []

    chunks: List[str] = []
    blocks = text.split("\n\n")
    current_chunk = ""

    for block in blocks:
        block = block.rstrip()
        if not block:
            continue

        if len(current_chunk) + len(block) + 2 <= chunk_size:
            current_chunk += block + "\n\n"
            continue

        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            current_chunk = ""

        if len(block) <= chunk_size:
            current_chunk = block + "\n\n"
            continue

        lines = block.split("\n")
        temp_chunk = ""

        for line in lines:
            line = line.rstrip()
            if len(temp_chunk) + len(line) + 1 <= chunk_size:
                temp_chunk += line + "\n"
                continue

            if temp_chunk.strip():
                chunks.append(temp_chunk.strip())
                temp_chunk = ""

            if len(line) <= chunk_size:
                temp_chunk = line + "\n"
                continue

            # Split very long lines by sentence-ish boundaries.
            sentence_parts = re.split(r"([.!?]\s+)", line)
            sentence_chunk = ""

            for part in sentence_parts:
                if not part:
                    continue

                if len(sentence_chunk) + len(part) <= chunk_size:
                    sentence_chunk += part
                else:
                    if sentence_chunk.strip():
                        chunks.append(sentence_chunk.strip())
                    sentence_chunk = part

            if sentence_chunk.strip():
                chunks.append(sentence_chunk.strip())

        if temp_chunk.strip():
            chunks.append(temp_chunk.strip())

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def rejoin_chunks(chunks: Iterable[str]) -> str:
    """
    Rejoin chunks with conservative paragraph breaks.
    """
    cleaned_chunks = [chunk.strip() for chunk in chunks if chunk and chunk.strip()]
    if not cleaned_chunks:
        return ""

    rejoined_text = cleaned_chunks[0]

    for chunk in cleaned_chunks[1:]:
        if (
            chunk.startswith("- ")
            or chunk.startswith("* ")
            or chunk.startswith("### ")
            or chunk.startswith("## ")
        ):
            rejoined_text += "\n" + chunk
        else:
            rejoined_text += "\n\n" + chunk

    return rejoined_text


def format_headers_for_telegram(translated_response: str) -> str:
    """
    Convert Markdown-ish headers into simple Telegram-compatible HTML headers.
    """
    translated_response = translated_response or ""
    lines = translated_response.split("\n")
    formatted_lines: List[str] = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("####"):
            if i > 0 and lines[i - 1].strip():
                formatted_lines.append("")
            formatted_lines.append("◦ <b>" + html.escape(stripped[4:].strip()) + "</b>")
            if i < len(lines) - 1 and lines[i + 1].strip():
                formatted_lines.append("")

        elif stripped.startswith("###"):
            if i > 0 and lines[i - 1].strip():
                formatted_lines.append("")
            formatted_lines.append("• <b>" + html.escape(stripped[3:].strip()) + "</b>")
            if i < len(lines) - 1 and lines[i + 1].strip():
                formatted_lines.append("")

        elif stripped.startswith("##"):
            if i > 0 and lines[i - 1].strip():
                formatted_lines.append("")
            formatted_lines.append("➤ <b>" + html.escape(stripped[2:].strip()) + "</b>")
            if i < len(lines) - 1 and lines[i + 1].strip():
                formatted_lines.append("")

        else:
            formatted_lines.append(line)

    return "\n".join(formatted_lines)


def markdown_to_html(md_text: str) -> str:
    """
    Lightweight Markdown-ish to Telegram-compatible HTML converter.

    Kept for compatibility. The main project also has modules.markdown_to_html,
    so prefer that central converter elsewhere when possible.
    """
    md_text = md_text or ""

    # Preserve fenced code first.
    code_blocks: List[str] = []

    def _store_code_block(match: re.Match) -> str:
        code = match.group(1)
        placeholder = f"@@CODE_BLOCK_{len(code_blocks)}@@"
        code_blocks.append("<pre>" + html.escape(code.strip()) + "</pre>")
        return placeholder

    text = re.sub(r"```(?:\w+)?\n?(.*?)```", _store_code_block, md_text, flags=re.DOTALL)

    # Basic Telegram-safe-ish conversions.
    text = re.sub(r"\$\$(.*?)\$\$", lambda m: "<pre>" + html.escape(m.group(1).strip()) + "</pre>", text, flags=re.DOTALL)
    text = re.sub(r"\\\[(.*?)\\\]", lambda m: "<pre>" + html.escape(m.group(1).strip()) + "</pre>", text, flags=re.DOTALL)

    text = re.sub(r"^####\s+(.*)", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^###\s+(.*)", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+(.*)", r"<b>\1</b>", text, flags=re.MULTILINE)

    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text, flags=re.DOTALL)
    text = re.sub(r"_(.*?)_", r"<i>\1</i>", text, flags=re.DOTALL)

    text = re.sub(r"`([^`\n]+?)`", lambda m: "<code>" + html.escape(m.group(1)) + "</code>", text)

    def _link_repl(match: re.Match) -> str:
        label = html.escape(match.group(1))
        url = html.escape(match.group(2), quote=True)
        return f'<a href="{url}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", _link_repl, text)

    for idx, block in enumerate(code_blocks):
        text = text.replace(f"@@CODE_BLOCK_{idx}@@", block)

    return text


def sanitize_urls(text: str) -> str:
    """
    Turn <https://example.com> into https://example.com.
    """
    text = text or ""
    url_pattern = re.compile(r"<(https?://[^\s<>]+)>")
    return re.sub(url_pattern, r"\1", text)


def split_message(text: str, max_length: int = MAX_TELEGRAM_MESSAGE_LENGTH) -> List[str]:
    """
    Split long Telegram messages into chunks.

    Telegram max is commonly treated as 4096 chars; this project uses 4000
    as a safer practical ceiling.
    """
    text = text or ""
    if not text.strip():
        return []

    paragraphs = text.split("\n")
    chunks: List[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        candidate = current_chunk + paragraph + "\n"
        if len(candidate) <= max_length:
            current_chunk = candidate
            continue

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        current_chunk = paragraph + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    final_chunks: List[str] = []

    for chunk in chunks:
        while len(chunk) > max_length:
            split_point = chunk.rfind("\n", 0, max_length)
            if split_point == -1:
                split_point = chunk.rfind(". ", 0, max_length)
            if split_point == -1:
                split_point = max_length

            piece = chunk[:split_point].strip()
            if piece:
                final_chunks.append(piece)

            chunk = chunk[split_point:].strip()

        if chunk.strip():
            final_chunks.append(chunk.strip())

    logging.info("Total number of chunks created: %d", len(final_chunks))
    return final_chunks


async def send_split_messages(context: Any, chat_id: Any, text: str) -> None:
    """
    Send a long message in Telegram-safe chunks.
    """
    chunks = split_message(text)
    logging.info("Total number of chunks to be sent: %d", len(chunks))

    for chunk in chunks:
        if not chunk.strip():
            logging.warning("send_split_messages attempted to send an empty chunk. Skipping.")
            continue

        logging.info("Sending chunk with length: %d", len(chunk))
        await context.bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode="HTML",
        )
        logging.info("Sent chunk with length: %d", len(chunk))

    logging.info("send_split_messages completed.")


async def handle_long_response(context: Any, chat_id: Any, long_response_text: str) -> None:
    """
    Compatibility wrapper for older code paths.
    """
    if not (long_response_text or "").strip():
        logging.warning("handle_long_response received an empty message. Skipping.")
        return

    logging.info("Handling long response with text length: %d", len(long_response_text))
    await send_split_messages(context, chat_id, long_response_text)


# ---------------------------------------------------------------------------
# Optional language detection over OpenAI API
# ---------------------------------------------------------------------------

def _extract_openai_chat_content(response_data: Dict[str, Any]) -> str:
    choices = response_data.get("choices") or []
    if not choices:
        return ""

    message = (choices[0] or {}).get("message") or {}
    content = message.get("content") or ""
    return str(content).strip()


async def detect_language(bot: Any, text: str) -> str:
    """
    Detect language using the current OpenAI model.

    This function is optional/legacy helper code, but now uses the same safer
    payload rules as v0.77.1:
    - no temperature for non-gpt-4* models
    - max_completion_tokens for non-gpt-4* models
    """
    text = text or ""
    if not text.strip():
        return "en"

    api_key = _get_openai_api_key_from_bot(bot)
    if not api_key:
        logging.error("OpenAI API key is missing; detect_language defaulting to English.")
        return "en"

    finnish_hint = (
        "Finnish often starts with words like: kuka, mikä, mitä, missä, "
        "milloin, miksi, minkä, minkälainen, kenen, kenelle, keneltä, "
        "kenestä, keiden."
    )

    prompt = (
        "Detect the language of the following text.\n\n"
        f"{text}\n\n"
        "Respond with only one ISO-style language code, for example:\n"
        "- en for English\n"
        "- fi for Finnish\n"
        "- sv for Swedish\n"
        "- ja for Japanese\n\n"
        f"HINT: {finnish_hint}"
    )

    model = (getattr(bot, "model", None) or DEFAULT_OPENAI_MODEL).strip()

    if not model:
        logging.error("No OpenAI model configured for detect_language; defaulting to English.")
        return "en"

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a language detection assistant. Return only the language code.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        openai_token_limit_key(model): 10,
    }

    if openai_model_supports_temperature(model):
        payload["temperature"] = 0

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
            )

        response.raise_for_status()
        response_data = response.json()

        detected_language = _extract_openai_chat_content(response_data).lower().strip()
        detected_language = re.sub(r"[^a-z-]", "", detected_language)

        if not detected_language:
            logging.warning("detect_language got empty OpenAI response; defaulting to English.")
            return "en"

        # Normalize common model verbosity just in case.
        if detected_language.startswith("finnish"):
            detected_language = "fi"
        elif detected_language.startswith("english"):
            detected_language = "en"
        elif detected_language.startswith("swedish"):
            detected_language = "sv"
        elif detected_language.startswith("japanese"):
            detected_language = "ja"

        logging.info("Detected language: %s", detected_language)
        return detected_language[:8]

    except httpx.RequestError as exc:
        logging.error("RequestError while calling OpenAI API in detect_language: %s", exc)
    except httpx.HTTPStatusError as exc:
        logging.error(
            "HTTPStatusError while calling OpenAI API in detect_language: %s - %s",
            exc.response.status_code,
            exc.response.text[:1000],
        )
    except Exception as exc:
        logging.exception("Unexpected error while calling OpenAI API in detect_language: %s", exc)

    return "en"

