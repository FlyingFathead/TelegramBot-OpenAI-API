# Web search and news retrieval

The primary Chat Completions model can call `search_web({"query": "..."})`. The Python handler selects providers from `config/config.ini`. Each receives the query supplied in that call. The handler returns provider-labelled evidence in one tool result. The primary model can then call `get_website_dump` to read selected URLs through Lynx before answering. Each webpage result is returned in its own tool message alongside the existing local context and search evidence. Only the primary model receives the chat history when writing the Telegram reply. OpenAI's hosted search uses the existing project key and a separate request to `POST /v1/responses`. Each invocation requests one hosted web search.

## Install the ZIP update on Linux

Save `ChatKeke-web-search-installer.zip` in `~/NeuralNetwork/` beside the checkout. From any directory run:

```bash
cd ~/NeuralNetwork &&
unzip -o ChatKeke-web-search-installer.zip &&
bash ./ChatKeke-web-search-installer/update.sh
```

The updater works with the 3 November source snapshot or the previous web search package. It backs up the affected files beside the checkout, adds missing INI keys while preserving existing values, and prints the active providers. Restart the bot with your usual command after a successful update.

## Enable all three providers

Set these values in the existing sections and restart the bot with your usual service command.

```ini
[WebSearch]
OpenAIEnabled = True
UseOpenAIWebSearch = True
OpenAIModel = gpt-6-luna
FallbackToOpenAI = True
TimeoutSeconds = 30
MaxWebToolCalls = 4
NewsMaxAgeDays = 7

[DuckDuckGo]
Enabled = True

[Perplexity]
Enabled = True
```

Perplexity also needs the existing `PERPLEXITY_API_KEY` environment variable. DuckDuckGo runs `lynx -dump -width=200` against the search URL directly. The separate `get_website_dump` tool uses the same direct Lynx fetch. Every model-requested web search starts all enabled providers concurrently and gives the primary model their results together, with provider labels and source links. DuckDuckGo and initial OpenAI web search default to enabled. Perplexity retains its existing enabled setting. Earlier `DefaultProvider` entries are ignored. Only the standalone diagnostic command can select an individual provider.

| UseOpenAIWebSearch | FallbackToOpenAI | OpenAI hosted search behavior with the master switch enabled |
| --- | --- | --- |
| True | True | Starts with ordinary searches. Also available after RSS and website failures. |
| True | False | Starts with ordinary searches. RSS and website lookups use their direct sources. |
| False | True | Runs only when retrieval fails and a multi-search still has time remaining. |
| False | False | Skipped on both paths. |

`OpenAIEnabled = False` disables hosted OpenAI search on every path. The primary Chat Completions model continues answering as usual. To change a setting, edit the existing `[WebSearch]` section and restart the bot.

`MaxWebToolCalls` counts the initial search or page call and any follow-up web tool calls made by the primary model, up to four by default. Each search still combines all enabled providers under one shared deadline. The model can read several pages and keeps the source URLs from earlier results. Failed page reads return an explicit failure to the model so it can use the remaining evidence. Direct Lynx browsing uses `get_website_dump` independently of the optional `[DuckDuckGo] EnableAgenticBrowsing` setting.

A multi-search starts the selected providers concurrently. One wall-clock deadline covers HTTP requests, retries and DuckDuckGo's optional browsing step. At the deadline the handler cancels unfinished local tasks and returns completed results. A failed lookup can use OpenAI at most once. A blocked website dump respects the existing domain restriction policy.

## Telegram reply formatting

Replies following web tool calls use the normal Markdown-to-HTML conversion before citation links are added. The model is instructed to use Telegram HTML and retain citation markers such as `[D1]`, `[O11]` and `[W2]`. Bold, italics and code are rendered by the bot even when the model uses Markdown. Citation replacement operates on text outside code and existing links. Long replies close and reopen formatting tags at message boundaries; source URLs and HTML entities are not cut in half. Source titles are escaped as text if the reply omits citation markers.

Version 0.8.10 fixes a branch that discarded the converted reply whenever web sources were present, leaving Markdown emphasis visible while citation links worked. This is a rendering correction; provider selection, direct Lynx fetching, tool availability and search deadlines retain their v0.8.9 behavior.

## Elasticsearch news actions

All 85 publisher/category action names continue to match existing Elasticsearch entries. A trigger first tries its configured RSS endpoint. A missing feed, HTTP error, unexpected content type, empty feed, or absence of recent usable articles immediately starts a publisher-scoped search when `FallbackToOpenAI` and `OpenAIEnabled` are enabled. OpenAI runs alongside enabled DuckDuckGo and Perplexity providers. Results are filtered to the specified publisher and dates. The search is limited to the publisher's domains and requests the trigger's particular section, language or region. It requires dated article citations. If that search is disabled, unavailable or yields no usable items, the action tries the corresponding publisher section page. If all routes fail, the primary model receives an explicit retrieval failure.

`NewsMaxAgeDays` defaults to seven. The effective window is the smaller of this value and the action's existing age limit. Dated entries retain their original timestamps. Yle's live most-read list can establish a ranking without supplying article publication dates. In that case the page result identifies the date as unavailable. The action caps direct results at 20 and bounds titles and descriptions. OpenAI-supplied publication dates are checked against the window but are reported by the search provider.

## Live audit on 3 November 2026

GET requests covered all 85 original feed URLs and the section pages chosen for the new configuration. The parser accepted recent entries from 79 feeds and 82 pages at the seven-day setting. These counts describe the responses seen during the audit. Redirects and content change over time.

| Trigger | Original feed observation | Section page observation |
| --- | --- | --- |
| `get_is_horoskoopit` | HTTP 404 | Me Naiset horoscope section yielded dated entries |
| `get_is_esports` | HTTP 404 | IS esports section yielded dated entries |
| `get_hs_talous` | Newest item dated 8 October 2026 | HS Visio yielded current business headlines |
| `get_cnn_us_news` | Legacy HTTP URL served April 2023 items. HTTPS returned 503 during a separate smoke test | CNN U.S. yielded current article links |
| `get_yle_karjalakse` | Newest item dated 23 October 2026 | Section also outside the seven-day window |
| `get_yle_nakokulmat` | Newest item dated 11 November 2025 | Section also outside the seven-day window |
| `get_hs_elama` | Feed yielded recent items | No qualifying page items |

## Smoke tests

Run these in the bot's virtual environment from the repository root. The first command is offline. The retrieval commands use the configured services and can incur provider charges.

```bash
python -m pytest -q
python scripts/check_retrieval.py news get_yle_kainuu
python scripts/check_retrieval.py news get_is_esports
python scripts/check_retrieval.py search --provider openai 'Ylen päivän pääuutiset'
python scripts/check_retrieval.py search --provider combined 'Ylen päivän pääuutiset'
```

With three configured, reachable providers, the combined check prints three labelled results. The OpenAI result includes source titles and URLs. To check Telegram delivery on a staging bot, ask it to search for current news and open one of the numbered references. For Elasticsearch, use an existing question whose indexed answer contains `<[get_is_esports]>`. The provider field in the standalone news check identifies which route succeeded.

The OpenAI API contract and supported models are documented in the [web search guide](https://developers.openai.com/api/docs/guides/tools-web-search), [Responses reference](https://developers.openai.com/api/reference/resources/responses/methods/create) and [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna).

The earlier HTTPX-based DuckDuckGo fetch served challenge pages. The deployment-host test supplied for v0.8.9 returned search results with direct Lynx. The adapter rejects dumps containing no external result links. Regression tests use a representative Lynx dump and mocked subprocess and provider responses. Publisher retrieval was tested live. OpenAI and Perplexity responses were tested with fixtures and HTTP mocks. No provider credentials or Telegram token were included in the snapshot.
