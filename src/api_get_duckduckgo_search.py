# api_get_duckduckgo_search.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
DuckDuckGo search helper module for ChatKeke.

Purpose:
- Fetch web content over HTTPS with httpx and render it through lynx locally.
- Fetch DuckDuckGo HTML search results without relying on Lynx/GnuTLS networking.
- Optionally run a small OpenAI sub-agent over those results.
- Optionally let the sub-agent request one webpage dump via a local
  visit_webpage tool.
- Return text back to text_message_handler.py, where it is appended into
  chat history and then summarized/formatted by the selected OpenAI model.

Important:
- This module does NOT send messages directly to Telegram.
- It returns context text to the caller.
- The OpenAI sub-agent uses modern Chat Completions tools/tool_choice payloads.
- Legacy function_call response parsing is kept as fallback compatibility.
- Temperature is only sent for gpt-4* model names, matching the v0.77.1
  ChatKeke payload rule used elsewhere.
"""

import asyncio
import configparser
import datetime
import json
import logging
import random
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote_plus

import httpx
import openai

from config_paths import CONFIG_PATH
from openai_reasoning_compat import apply_reasoning_effort


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_TOKENS = 2048

DEFAULT_DDG_AGENTIC_BROWSING = False
DEFAULT_DDG_CONTENT_SIZE_LIMIT = False
DEFAULT_DDG_MAX_CONTENT_SIZE = 10000

OPENAI_CHAT_COMPLETIONS_ENDPOINT = "https://api.openai.com/v1/chat/completions"
# Use DuckDuckGo's canonical HTML host directly. Older Lynx/GnuTLS builds can
# successfully connect to both hosts separately yet fail the second TLS handshake
# when duckduckgo.com redirects to html.duckduckgo.com. Going direct avoids that
# unnecessary redirect while keeping the same HTML search endpoint.
DUCKDUCKGO_HTML_ENDPOINT = "https://html.duckduckgo.com/html/"


def _cfg_get(section: str, option: str, fallback: str) -> str:
    try:
        return config.get(section, option, fallback=fallback)
    except Exception as exc:
        logger.warning(
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
        logger.warning(
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
        logger.warning(
            "Invalid float config value for [%s] %s; using fallback %r: %s",
            section,
            option,
            fallback,
            exc,
        )
        return fallback


def _cfg_getboolean(section: str, option: str, fallback: bool) -> bool:
    try:
        return config.getboolean(section, option, fallback=fallback)
    except Exception as exc:
        logger.warning(
            "Invalid boolean config value for [%s] %s; using fallback %r: %s",
            section,
            option,
            fallback,
            exc,
        )
        return fallback


model_name = _cfg_get("DEFAULT", "Model", DEFAULT_MODEL).strip()
temperature = _cfg_getfloat("DEFAULT", "Temperature", DEFAULT_TEMPERATURE)
reasoning_effort = _cfg_get("DEFAULT", "ReasoningEffort", "default").strip().lower()
timeout = max(1, _cfg_getint("DEFAULT", "Timeout", DEFAULT_TIMEOUT))
max_tokens = max(1, _cfg_getint("DEFAULT", "MaxTokens", DEFAULT_MAX_TOKENS))

enable_agentic_browsing = _cfg_getboolean(
    "DuckDuckGo",
    "EnableAgenticBrowsing",
    DEFAULT_DDG_AGENTIC_BROWSING,
)

enable_content_size_limit = _cfg_getboolean(
    "DuckDuckGo",
    "EnableContentSizeLimit",
    DEFAULT_DDG_CONTENT_SIZE_LIMIT,
)

max_content_size = max(
    100,
    _cfg_getint("DuckDuckGo", "MaxContentSize", DEFAULT_DDG_MAX_CONTENT_SIZE),
)


# ---------------------------------------------------------------------------
# OpenAI compatibility helpers
# ---------------------------------------------------------------------------

def model_supports_temperature(model: str) -> bool:
    """
    Local ChatKeke rule:
    - gpt-4* models get temperature.
    - newer non-GPT-4/reasoning-ish model families do not.
    """
    model = (model or "").strip().lower()
    return model.startswith("gpt-4")


def token_limit_key_for_model(model: str) -> str:
    """
    Local ChatKeke rule:
    - gpt-4* => max_tokens
    - newer non-GPT-4 model families => max_completion_tokens
    """
    if model_supports_temperature(model):
        return "max_tokens"
    return "max_completion_tokens"


def build_openai_tools(function_specs: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Convert legacy function specs:

        {"name": "...", "description": "...", "parameters": {...}}

    into modern Chat Completions tools format:

        {"type": "function", "function": {...}}

    If an item is already in tools format, keep it.
    """
    tools: List[Dict[str, Any]] = []

    for item in function_specs or []:
        if isinstance(item, dict) and item.get("type") == "function" and "function" in item:
            tools.append(item)
        else:
            tools.append(
                {
                    "type": "function",
                    "function": item,
                }
            )

    return tools


def build_subagent_payload(
    *,
    messages: List[Dict[str, str]],
    functions: Optional[List[Dict[str, Any]]] = None,
    include_tools: bool = True,
) -> Dict[str, Any]:
    """
    Build a Chat Completions payload for the DuckDuckGo sub-agent.

    Uses:
    - tools/tool_choice for function calling
    - no temperature for non-gpt-4* models
    - max_completion_tokens for non-gpt-4* models
    """
    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        token_limit_key_for_model(model_name): max_tokens,
    }

    if model_supports_temperature(model_name):
        payload["temperature"] = temperature
    else:
        logger.info(
            "Sub-agent model %s is not gpt-4*; omitting temperature.",
            model_name,
        )

    if include_tools:
        tools = build_openai_tools(functions)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

    apply_reasoning_effort(
        payload,
        model_name,
        reasoning_effort,
        has_function_tools=bool(payload.get("tools")),
        logger=logger,
    )

    return payload


def extract_subagent_tool_call_or_none(response_json: Dict[str, Any]) -> Optional[Dict[str, Optional[str]]]:
    """
    Supports both:
    - modern Chat Completions tool_calls
    - old legacy function_call fallback

    Returns:
        {"name": str, "arguments": str, "tool_call_id": str|None}
    or None.
    """
    choices = response_json.get("choices") or []
    if not choices:
        return None

    message_obj = choices[0].get("message") or {}

    # Modern tools/tool_calls path.
    tool_calls = message_obj.get("tool_calls") or []
    if tool_calls:
        first_tool_call = tool_calls[0] or {}
        if first_tool_call.get("type") == "function":
            fn = first_tool_call.get("function") or {}
            return {
                "name": fn.get("name"),
                "arguments": fn.get("arguments") or "{}",
                "tool_call_id": first_tool_call.get("id"),
            }

    # Legacy functions/function_call path.
    legacy_function_call = message_obj.get("function_call")
    if legacy_function_call:
        return {
            "name": legacy_function_call.get("name"),
            "arguments": legacy_function_call.get("arguments") or "{}",
            "tool_call_id": None,
        }

    return None


def extract_subagent_reply(response_json: Dict[str, Any]) -> str:
    """
    Extract assistant message content from Chat Completions response.
    """
    choices = response_json.get("choices") or []
    if not choices:
        return ""

    message_obj = choices[0].get("message") or {}
    content = message_obj.get("content") or ""

    return str(content).strip()


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def print_horizontal_line(length: int = 50, character: str = "-") -> None:
    line = character * length
    logger.info(line)


def _get_first_linkish_token(line: str) -> Optional[str]:
    """
    Old ChatKeke-compatible URL dedupe helper.
    Finds first http/https-looking token in a line.
    """
    if "http" not in line:
        return None

    try:
        return "http" + line.split("http", 1)[1].split(" ", 1)[0]
    except Exception:
        return None


def _dedupe_lines_with_links(text: str) -> str:
    """
    Remove duplicate URL lines while preserving non-URL lines.
    """
    seen_links = set()
    unique_lines: List[str] = []

    for line in (text or "").split("\n"):
        link = _get_first_linkish_token(line)
        if link:
            if link not in seen_links:
                seen_links.add(link)
                unique_lines.append(line)
        else:
            unique_lines.append(line)

    return "\n".join(unique_lines)


async def _run_lynx_dump(url: str) -> str:
    """
    Fetch a URL with httpx, then render the returned HTML through Lynx locally.

    Lynx is intentionally not allowed to perform the HTTPS request itself. Some
    older Lynx/GnuTLS builds intermittently fail TLS handshakes when Keke runs as
    a service even though the same URL works from an interactive shell. httpx is
    already used by Keke and provides the network transport; Lynx only converts
    the downloaded HTML into the existing text-dump format.

    Raises RuntimeError on HTTP or Lynx rendering failure.
    """
    headers = {
        "User-Agent": "Lynx/2.9.0 ChatKeke/0.8.3",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=max(1, timeout),
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"HTTP fetch failed for {url}: {exc}") from exc

    # Preserve correct resolution of relative links when Lynx parses HTML from
    # stdin rather than fetching the original URL itself. A document-level BASE
    # element is sufficient for Lynx to emit absolute references in --dump.
    final_url = str(response.url)
    base_tag = f'<base href="{final_url}">\n'.encode("utf-8")
    html_bytes = base_tag + response.content

    process = await asyncio.create_subprocess_exec(
        "lynx",
        "-dump",
        "-force_html",
        "-stdin",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate(input=html_bytes)

    if process.returncode != 0:
        error_message = stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error_message or f"lynx exited with code {process.returncode}")

    return stdout.decode("utf-8", errors="replace")


def _build_duckduckgo_search_url(search_terms: str) -> str:
    formatted_query = quote(search_terms or "")
    return f"{DUCKDUCKGO_HTML_ENDPOINT}?q={formatted_query}"


async def _fetch_duckduckgo_results(search_terms: str) -> str:
    """
    Fetch, parse, dedupe, and format DuckDuckGo search results.
    """
    search_url = _build_duckduckgo_search_url(search_terms)

    response_text = await _run_lynx_dump(search_url)
    cleaned_text = parse_duckduckgo(response_text)
    unique_text = _dedupe_lines_with_links(cleaned_text)

    logger.info(unique_text)

    return format_for_telegram_html(unique_text)


# ---------------------------------------------------------------------------
# Main DuckDuckGo search function
# ---------------------------------------------------------------------------

async def get_duckduckgo_search(search_terms, user_message):
    """
    Main public entry point used by text_message_handler.py.

    Returns text only.
    It does not send messages to Telegram directly.
    """
    try:
        search_terms = (search_terms or "").strip()
        user_message = user_message or ""

        if not search_terms:
            logger.warning("get_duckduckgo_search called with empty search_terms.")
            return "Error: empty DuckDuckGo search query."

        # Basic non-agentic path.
        if not enable_agentic_browsing:
            logger.info(
                "Agentic browsing is disabled. Returning basic DuckDuckGo results without sub-agent processing."
            )

            try:
                return await _fetch_duckduckgo_results(search_terms)
            except Exception as exc:
                logger.error("DuckDuckGo/lynx search failed: %s", exc)
                return f"Error: {str(exc)}"

        # Agentic path.
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print_horizontal_line()
        logger.info("[%s] Agentic browsing-enabled DuckDuckGo searching: %s", timestamp, search_terms)
        print_horizontal_line()

        try:
            unique_text = await _fetch_duckduckgo_results(search_terms)
        except Exception as exc:
            logger.error("DuckDuckGo/lynx search failed: %s", exc)
            return f"Error: {str(exc)}"

        print_horizontal_line()

        # Call the OpenAI sub-agent to process the results or request one webpage.
        sub_agent_result = await sub_agent_openai_call(
            user_message=user_message,
            search_terms=search_terms,
            search_results=unique_text,
            retries=3,
            timeout=timeout,
        )

        # Failsafe: if sub-agent result is empty, return DuckDuckGo results instead.
        if not (sub_agent_result or "").strip():
            logger.warning("Sub-agent returned empty. Falling back to DuckDuckGo results.")
            return format_for_telegram_html(unique_text)

        return sub_agent_result

    except Exception as exc:
        logger.exception("Error in get_duckduckgo_search: %s", exc)
        return f"Error: {str(exc)}"


# ---------------------------------------------------------------------------
# OpenAI sub-agent call handler
# ---------------------------------------------------------------------------

async def sub_agent_openai_call(user_message, search_terms, search_results, retries=3, timeout=30):
    """
    Small OpenAI sub-agent for agentic DuckDuckGo browsing.

    Important:
    - This does not send anything to Telegram.
    - It returns context text to the caller.
    - If the model calls visit_webpage, this function executes the local fetch
      and returns the fetched page content as context.
    """
    user_message = user_message or ""
    search_terms = search_terms or ""
    search_results = search_results or ""

    if not (openai.api_key or "").strip():
        logger.error("OpenAI API key is missing for DuckDuckGo sub-agent.")
        return format_for_telegram_html(search_results)

    timeout = max(1, int(timeout or DEFAULT_TIMEOUT))
    retries = max(1, int(retries or 1))

    # Prepare the system message for the sub-agent.
    system_message = {
        "role": "system",
        "content": (
            f"The user's input was:\n{user_message}\n\n"
            f"The search term used was:\n{search_terms}\n\n"
            f"DuckDuckGo search results are:\n{search_results}\n\n"
            "You are a small search-analysis sub-agent inside ChatKeke. "
            "Your output will be appended into the main chat context; it is not sent directly to the user. "
            "Extract the most relevant context from the DuckDuckGo results. "
            "You may call the visit_webpage tool if one result must be opened for further details. "
            "Use visit_webpage especially when the user asked for a specific page, document, article, or link contents. "
            "Do not invent facts not present in the search results or fetched page content. "
            "Answer in the user's original language: Finnish if the user wrote Finnish, English if English, etc. "
            "Use Telegram-compatible HTML only if formatting is needed. "
            "Do NOT use <ul>, <li>, <pre>, <br>, <h1>, <h2>, <h3>, Markdown tables, or Markdown links."
        ),
    }

    # Define available local tools.
    functions = [
        {
            "name": "visit_webpage",
            "description": "Fetch the text contents of a webpage for further analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full http or https URL of the webpage to visit.",
                    }
                },
                "required": ["url"],
            },
        }
    ]

    payload = build_subagent_payload(
        messages=[system_message],
        functions=functions,
        include_tools=True,
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai.api_key}",
    }

    for attempt in range(retries):
        try:
            logger.info(
                "Sub-agent attempt %d/%d: sending OpenAI Chat Completions request.",
                attempt + 1,
                retries,
            )

            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                response = await client.post(
                    OPENAI_CHAT_COMPLETIONS_ENDPOINT,
                    json=payload,
                    headers=headers,
                )

            raw_response_text = response.text

            if response.status_code >= 400:
                logger.error(
                    "Sub-agent OpenAI API error %s: %s",
                    response.status_code,
                    raw_response_text[:4000],
                )

                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < retries - 1:
                        await asyncio.sleep(_subagent_backoff_delay(attempt))
                        continue

                return format_for_telegram_html(search_results)

            try:
                response_json = response.json()
            except Exception as exc:
                logger.error(
                    "Sub-agent OpenAI returned non-JSON response: %s; parse error: %s",
                    raw_response_text[:4000],
                    exc,
                )
                return format_for_telegram_html(search_results)

            if "error" in response_json:
                logger.error("Sub-agent OpenAI API error object: %s", response_json["error"])
                return format_for_telegram_html(search_results)

            if not response_json.get("choices"):
                logger.error("Sub-agent OpenAI response missing/empty choices: %s", response_json)
                return format_for_telegram_html(search_results)

            logger.info("Sub-agent API request completed.")

            # Modern tool_calls or legacy function_call fallback.
            function_call = extract_subagent_tool_call_or_none(response_json)

            if function_call:
                function_name = function_call.get("name")
                logger.info("Sub-agent requested function/tool call: %s", function_name)

                if function_name == "visit_webpage":
                    arguments_raw = function_call.get("arguments") or "{}"

                    try:
                        arguments = json.loads(arguments_raw)
                    except json.JSONDecodeError as exc:
                        logger.error(
                            "Sub-agent returned invalid JSON arguments for visit_webpage: %r; error: %s",
                            arguments_raw,
                            exc,
                        )
                        return format_for_telegram_html(search_results)

                    url = (arguments.get("url") or "").strip()
                    logger.info("Function/tool visit_webpage called with url: %s", url)

                    if not url:
                        logger.error("No valid URL provided by sub-agent. Returning DuckDuckGo results.")
                        return format_for_telegram_html(search_results)

                    if not _is_probably_http_url(url):
                        logger.error(
                            "Sub-agent requested non-http(s) URL %r. Returning DuckDuckGo results.",
                            url,
                        )
                        return format_for_telegram_html(search_results)

                    try:
                        logger.info("Attempting to fetch content from URL: %s", url)
                        page_content = await fetch_link_content(url)

                        if "Error:" in page_content:
                            logger.error(
                                "Fetching content failed from %s. Returning DuckDuckGo search results.",
                                url,
                            )
                            return format_for_telegram_html(search_results)

                        logger.info(
                            "Fetched content from %s, content length: %d characters",
                            url,
                            len(page_content),
                        )

                        # Return fetched context to text_message_handler.py.
                        # The main model will produce the final user-facing answer.
                        return (
                            f"[DuckDuckGo sub-agent fetched webpage content]\n"
                            f"URL: {url}\n\n"
                            f"{page_content}"
                        )

                    except Exception as exc:
                        logger.exception(
                            "Failed to fetch content from %s: %s. Returning DuckDuckGo results.",
                            url,
                            exc,
                        )
                        return format_for_telegram_html(search_results)

                logger.error(
                    "Sub-agent requested unknown function/tool %r. Returning DuckDuckGo results.",
                    function_name,
                )
                return format_for_telegram_html(search_results)

            # No tool call: return the sub-agent's processed search context.
            agent_reply = extract_subagent_reply(response_json)
            logger.info("Sub-agent reply: %s", agent_reply)

            if not agent_reply:
                logger.error("Sub-agent response content was empty. Returning DuckDuckGo results.")
                return format_for_telegram_html(search_results)

            return format_for_telegram_html(agent_reply)

        except httpx.TimeoutException as exc:
            logger.error(
                "Sub-agent OpenAI timeout on attempt %d/%d: %s",
                attempt + 1,
                retries,
                exc,
            )
        except httpx.RequestError as exc:
            logger.error(
                "Sub-agent OpenAI request error on attempt %d/%d: %s",
                attempt + 1,
                retries,
                exc,
            )
        except Exception as exc:
            logger.exception(
                "Sub-agent attempt %d/%d failed: %s",
                attempt + 1,
                retries,
                exc,
            )

        if attempt < retries - 1:
            await asyncio.sleep(_subagent_backoff_delay(attempt))

    logger.error("All %d sub-agent retry attempts failed. Returning DuckDuckGo search results.", retries)
    return format_for_telegram_html(search_results)


def _subagent_backoff_delay(attempt: int) -> float:
    """
    Short exponential-ish backoff for the DuckDuckGo sub-agent.
    """
    return min(10.0, (2 ** attempt) + random.uniform(0, 1))


def _is_probably_http_url(url: str) -> bool:
    url = (url or "").strip().lower()
    return url.startswith("http://") or url.startswith("https://")


# ---------------------------------------------------------------------------
# Fetch content from a link using lynx
# ---------------------------------------------------------------------------

async def fetch_link_content(link):
    """
    Fetch text content from a webpage using lynx --dump.

    Returns formatted text on success or an Error: string on failure.
    """
    link = (link or "").strip()

    if not link:
        logger.error("No valid link provided to fetch content from.")
        return "Error: No valid link provided."

    if not _is_probably_http_url(link):
        logger.error("Refusing to fetch non-http(s) link: %r", link)
        return "Error: Refusing to fetch non-http(s) link."

    logger.info("Starting to fetch content from link: %s", link)

    try:
        logger.info("Running lynx dump command for link: %s", link)
        page_content = await _run_lynx_dump(link)

        logger.info("Lynx dump output received. Content length: %d characters", len(page_content))

        if enable_content_size_limit and len(page_content) > max_content_size:
            logger.info("Limiting page content to %d characters.", max_content_size)
            page_content = page_content[:max_content_size] + "\n\n[Content truncated due to size limit.]"

        formatted_content = format_for_telegram_html(page_content)
        logger.info(
            "Formatted content ready for return, final content length: %d characters",
            len(formatted_content),
        )

        return formatted_content

    except Exception as exc:
        logger.error("Exception occurred during fetch_link_content: %s", exc)
        return f"Error: Failed to fetch content from {link}. Returning DuckDuckGo results instead."


# ---------------------------------------------------------------------------
# Clean DuckDuckGo search results
# ---------------------------------------------------------------------------

def parse_duckduckgo(text):
    """
    Clean DuckDuckGo lynx dump output:
    - decode DuckDuckGo redirect URLs
    - remove empty lines
    - exclude duckduckgo.com redirect/helper links
    - compact lines into: Title - URL
    """
    text = text or ""

    url_pattern = r"(http[s]?://[^\s]+)"
    cleaned_text = text

    # Replace DuckDuckGo obfuscated redirect links with original links.
    duckduckgo_pattern = r"(https://duckduckgo\.com/l/\?uddg=[^\s]+)"
    matches = re.findall(duckduckgo_pattern, text)

    for match in matches:
        try:
            cleaned_url = match.split("&rut=", 1)[0]
            original_url = unquote_plus(cleaned_url.split("uddg=", 1)[1])
            cleaned_text = cleaned_text.replace(match, original_url)
        except Exception as exc:
            logger.warning("Failed to decode DuckDuckGo redirect URL %r: %s", match, exc)

    # Remove empty lines and unnecessary spaces.
    lines = cleaned_text.split("\n")
    cleaned_lines = [line.strip() for line in lines if line.strip()]

    concise_lines: List[str] = []

    for line in cleaned_lines:
        url_match = re.search(url_pattern, line)

        if url_match:
            url = url_match.group(0)

            # Exclude DuckDuckGo helper/redirect URLs.
            if "duckduckgo.com" in url:
                continue

            title = line.replace(url, "").strip()
            concise_line = f"{title} - {url}" if title else url
            concise_lines.append(concise_line)
        else:
            concise_lines.append(line)

    return "\n".join(concise_lines)


# ---------------------------------------------------------------------------
# Format for Telegram HTML
# ---------------------------------------------------------------------------

def format_for_telegram_html(text):
    """
    Formats text to be Telegram-ish compliant.

    This intentionally keeps the old project behavior:
    - remove <br> tags
    - escape bare ampersands
    - preserve existing simple HTML tags such as <a>, <b>, <i>, etc.
    - collapse excessive newlines

    Note:
    In the current text_message_handler.py flow, this module usually returns
    context text that is appended into chat history, not sent directly to the user.
    """
    text = str(text or "")

    # Remove <br> tags completely.
    text = re.sub(r"<br\s*/?>", "", text, flags=re.IGNORECASE)

    # Escape bare ampersands but do not double-escape existing entities.
    def escape_non_html_entities(match):
        char = match.group(0)
        if char == "&":
            return "&amp;"
        return char

    text = re.sub(r"[&](?!#?\w+;)", escape_non_html_entities, text)

    # Remove extra newlines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()