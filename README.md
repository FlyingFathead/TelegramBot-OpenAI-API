# TelegramBot-OpenAI-API

## 🤖 _Powered by ChatKeke_ 🚀

- **A simple-to-use, quick-to-deploy Python-based Telegram bot for OpenAI API & Perplexity API**
- **🎙 Transcribed Telegram voice messages via OpenAI speech-to-text models (Whisper and others)**
  - Supports configurable STT models such as `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, and legacy `whisper-1`
- **☁️ Real-time weather info, weather alerts, and geolocation data via [OpenWeatherMap](https://openweathermap.org/), [WeatherAPI](https://www.weatherapi.com/) and U.S. NWS ([weather.gov](https://weather.gov))**
- **🗺 Geolocation and map lookups via MapTiler API**
  - (with weather forecasts around the world in all OpenAI API supported languages)
- **🧭 Navigation instructions via Openrouteservice API**  
- **🔔 Timed reminders & notifications system**
  - Users can schedule alerts that trigger at specific times. Configurable per-user limits and optional listing of past reminders
- **📊 Daily token usage tracking & rate limiting for API usage / cost management**
- **🔍 Perplexity API models alongside OpenAI models**
  - Useful for fact-checking and supplementing OpenAI's cutoff dates
- **📚 Built-in Elasticsearch RAG steps**  
  - Increase knowledge rate with your own documents
  - Generate extra insights with the Q&A pair creator
- **📅 Holiday notifications via Python's `holidays` module**
  - Localized to supported countries, or add your own special reminders
- **📈 Fetching stock prices via Alpha Vantage API & Yahoo! Finance**
  - Real-time access to financial & stock market data
- **📰 RSS feeds from all available sources**
  - Fetch news and more via RSS
- **🦆 DuckDuckGo searches as context-augmented function calls**  
  - New! **Sub-agentic browsing** for enhanced, precise searches!
- **🌐 Web browsing (page dumps w/ links) as context-augmented function calls**
  - With optional domain/IP allow/disallow lists for safety
- **🧮 Calculator function call module for precise calculations**
  - No more fumbling with AI arithmetic hallucinations!
- **🔄 Automated "premium vs. fallback" model switching**
  - Seamlessly switches between your “premium” and “mini” model when daily token limits are reached, letting you reduce costs without manually reconfiguring
- **🐳 Dockerized for safety and ease of deplyoment**
  - For those who love their Dockers, ready to roll within minutes!

## General minimum requirements:

- **Telegram API bot token** 
  - use the [`@BotFather`](https://t.me/BotFather) bot on Telegram to set up your bot and get a Telegram Bot API token for it
- **OpenAI API token**
  - Get one from from: https://platform.openai.com/

---

# 🐧 Installing without Docker on Linux

## Prerequisites
- Tested & working on Python `3.10.12` to `3.12.2`
- Install required Python packages with `pip install -r requirements.txt` (tested and working with the versions listed in [requirements.txt](./requirements.txt)
- `pydub` usually requires `ffmpeg` to be installed separately. Note that neither `pydub` nor `ffmpeg` are practically not required if you are *not* utilizing the voice message/WhisperAPI functionality, but if you are, suggested install (Debian/Ubuntu Linux): `sudo apt-get install ffmpeg`
- NOTE: DuckDuckGo searches require `lynx` to be installed on your system; it needs to be run as a subprocess. (Install on Debian/Ubuntu Linux with: `sudo apt-get install lynx`)

1. **Clone the repository with:**

  ```bash
  git clone https://github.com/FlyingFathead/TelegramBot-OpenAI-API/ &&
  cd TelegramBot-OpenAI-API/
  ```

2. **Install the required packages:**

  ```bash
  pip install -r requirements.txt
  ```

3. **(Recommended) install the optional packages:**

  - On Ubuntu/Debian tree Linux systems:

  ```bash
  sudo apt-get install -y ffmpeg lynx
  ```

3. **Set up your Telegram bot token:**

  - Either set your Telegram Bot API token as `TELEGRAM_BOT_TOKEN` environment variable, or put it into a text file named `bot_token.txt` inside the `config/` directory (= `config/bot_token.txt`)

4. **Set up your OpenAI API token:**

  - Either as `OPENAI_API_KEY` environment variable or put into a text file named `api_token.txt` inside the main program directory

5. **Other modules:**

  - If you wish to use the OpenWeatherMap API and the MapTiler API for i.e. localized weather data retrieval, set the `OPENWEATHERMAP_API_KEY` and the `MAPTILER_API_KEY` environment variables accordingly. You can get the API keys from [OpenWeather](https://openweathermap.org/) and [MapTiler](https://www.maptiler.com/)
  - Additional weather info (moon phases, weather warnings etc) are fetched from [WeatherAPI](https://weatherapi.com), set the `WEATHERAPI_KEY` environment variable to use it.
  - If you wish to use the Openrouteservice API for driving instructions, set the `OPENROUTESERVICE_API_KEY` environment variable from [Openrouteservice](https://openrouteservice.org/)
  - If you wish to use Perplexity API's supplementary fact-checking with their online models, register at [Perplexity.ai](https://perplexity.ai), buy some API credits and set your Perplexity API key to environment variable: `PERPLEXITY_API_KEY`

6. **Further adjustments:**

  - Adjust your configuration and settings by editing `config/config.ini` to your liking

7. **Run:**

- Run the program with: `python src/main.py`

---

# 🐳 **Installing Dockerized**

### **Prerequisites**
1. **Docker** must be installed on your machine.
   - If not installed, you can download and install it from [Docker's official site](https://www.docker.com/get-started).

2. **Telegram Bot API Key** and **OpenAI API Key**:
   - You will need a valid Telegram Bot API key. You can get one by creating a bot with [BotFather](https://core.telegram.org/bots#botfather).
   - You will also need an OpenAI API key. If you don't have one, you can generate it from the [OpenAI API page](https://beta.openai.com/signup/).

### **Step 1: Clone the Repository**

First, clone the repository from GitHub:

  ```bash
  git clone https://github.com/FlyingFathead/TelegramBot-OpenAI-API.git
  cd TelegramBot-OpenAI-API
  ```

### **Step 2: Run the Setup Script**

This project includes a setup script that will guide you through entering your API keys and generating a `.env` file.

Run the script:

  ```bash
  ./docker_setup.sh
  ```

Follow the instructions provided by the script. It will ask for your OpenAI API key and Telegram Bot API key, validate them, and create a `.env` file with your credentials.

### **Step 3: Build the Docker Image**

Once your `.env` file has been created, you need to build the Docker image.

You can run the featured `docker_deploy.sh` to build the Docker image:

  ```bash
  sudo ./docker_deploy.sh
  ```

Or, you can build it manually:

  ```bash
  sudo docker build -t telegrambot-openai-api .
  ```

This will build the image locally based on the `Dockerfile` in the repository.

### **Step 4: Run the Docker Container**

After the image is successfully built, you can start the bot in a Docker container.

Run the container with the following command:

  ```bash
  sudo docker run --env-file .env --name telegrambot-openai-api -d telegrambot-openai-api
  ```

- The `-d` flag runs the container in detached mode (in the background).
- The `--env-file .env` flag injects your API keys into the container.

### **Step 5: Check the Running Container**

You can check if the container is running by using:

  ```bash
  sudo docker ps
  ```

This will list all running containers. If your bot is running correctly, it should appear in the list.

### **Step 6: Stopping the Container**

If you need to stop the bot, you can do so by running:

  ```bash
  sudo docker stop <container_id>
  ```

Replace `<container_id>` with the actual container ID, which you can obtain from the `docker ps` output.

### **Additional Steps (Optional)**

- **Logs**: If you need to view the bot’s logs to troubleshoot any issues, you can use:

  ```bash
  sudo docker logs <container_id>
  ```

- **Restart the Container**: If you stop the container and want to start it again, you can either run the `docker run` command again or restart the existing container with:

  ```bash
  sudo docker start <container_id>
  ```

### **Updating the Bot**

If the repository receives updates and you want to apply them, follow these steps:

1. Pull the latest changes from GitHub:
   ```bash
   git pull origin main
   ```

2. Rebuild the Docker image:
   ```bash
   sudo docker build -t telegrambot-openai-api .
   ```

3. Stop the currently running container:
   ```bash
   sudo docker stop <container_id>
   ```

4. Start a new container using the updated image:
   ```bash
   sudo docker run --env-file .env --name telegrambot-openai-api -d telegrambot-openai-api
   ```

There is also a `docker_deploy.sh` script included that aims to make the rebuilding and deploying less of a hassle.

You should now have the TelegramBot-OpenAI-API running in a Docker container, fully connected to both Telegram and OpenAI. Enjoy your bot!

If you run into any issues, consult the logs or reach out on the repository's [Issues page](https://github.com/FlyingFathead/TelegramBot-OpenAI-API/issues).

---

# Updating your `config.ini`

- Use the `configmerger.py` to update old configuration files into a newer version's `config.ini`. You can do this by saving a copy of your existing config to i.e. a file named `myconfig.txt` and including in it the lines you want to keep for the newer version. 

- After that, just run i.e. `python src/configmerger.py myconfig.txt` and all your existing config lines will be migrated to the new one. Works in most cases, but remember to be careful and double-check any migration issues with i.e. `diff`!

**(Example) How to merge and update your existing configuration:**

  ```bash
  python3 src/configmerger.py myconfig.txt
  ```

---

# Changelog

- v0.8.3 - GPT-5.6 Luna, backwards-compatible reasoning effort, and compatibility fixes
  - Added optional `ReasoningEffort` in `[DEFAULT]` for OpenAI Chat Completions models.
  - `ReasoningEffort = default` normally preserves existing behaviour by omitting the field and using the selected model's API default.
  - Added a conservative model/value compatibility layer so unsupported older models never receive `reasoning_effort`.
  - Explicitly supports the documented effort ranges for GPT-5.1, GPT-5.2, GPT-5.4, GPT-5.5 and GPT-5.6; original GPT-5 keeps its older `minimal` vocabulary.
  - GPT-5.6 supports `none`, `low`, `medium`, `high`, `xhigh`, and `max` where the selected endpoint/tool combination permits them.
  - GPT-5.6 Luna has a special Chat Completions compatibility rule: when function tools are attached, Keke explicitly uses `reasoning_effort = none`. The `/v1/chat/completions` endpoint rejects Luna function-tool requests with its default/higher reasoning effort; higher reasoning plus tools requires the Responses API.
  - Invalid model/effort combinations are logged and omitted instead of producing a malformed API request.
  - Model auto-switching remains safe when premium/fallback models have different reasoning capabilities.
  - Applied the same guarded setting to the optional DuckDuckGo sub-agent and Perplexity OpenAI language detector.
  - Hardened legacy route/weather formatting calls so newer reasoning models no longer receive the old unconditional `temperature` field.
  - DuckDuckGo HTML searches now use `httpx` for HTTPS transport and feed the downloaded HTML to Lynx locally for text rendering. This avoids observed intermittent Lynx/GnuTLS handshake failures under service execution while preserving the existing Lynx dump/parser behavior; the canonical `https://html.duckduckgo.com/html/` endpoint is used directly.

- v0.8.2 - Configurable OpenAI speech-to-text model support for Telegram voice messages
  - Updated Telegram voice message transcription handling for the current OpenAI audio transcription model lineup.
  - Added configurable speech-to-text model selection through `config.ini`:
    - `STTModel = gpt-4o-transcribe`
    - `STTModel = gpt-4o-mini-transcribe`
    - `STTModel = whisper-1`
  - Kept backward compatibility with the old `EnableWhisper` config flag so existing configs do not break.
  - Added `OPENAI_STT_MODEL` environment-variable fallback for overriding the configured STT model in Docker/systemd/shell deployments.
  - Changed the default voice transcription model from legacy `whisper-1` to modern `gpt-4o-transcribe`.
  - Refactored `src/voice_message_handler.py` so the STT model is read from the main `TelegramBot` config object instead of being hardcoded in the voice module.
  - Added lazy OpenAI async client initialization for voice transcription so the client is created only after API key loading.
  - Preserved support for legacy `whisper-1` as a fallback model.
  - Preserved Telegram-visible voice transcription marker:
    - `🎤📝`
  - Improved Telegram HTML safety by escaping transcribed text before wrapping it in HTML formatting.
  - Improved model-facing voice transcription formatting through `context.user_data["transcribed_text"]`.
  - Fixed voice message duration checking so `MaxDurationMinutes` is correctly treated as minutes while Telegram/audio duration values are handled as seconds.
  - Improved voice message logging with detailed metadata:
    - Telegram user ID
    - username
    - first/last name
    - chat ID
    - chat type/title
    - message ID
    - Telegram voice file ID / unique ID
    - voice duration
    - MIME type
    - file size
    - local downloaded file path
    - selected STT model
    - final transcription text
  - Logs detailed voice transcription events into `bot.log`.
  - Logs transcription events into `chat.log` when `ChatLoggingEnabled = True`.
  - Cleaned up `main.py` voice handler registration:
    - removed the old extra-argument voice handler path
    - now routes voice messages through `self.voice_message_handler`
  - Fixed `load_config()` directory creation logging by replacing undefined `logger` references with a local `TelegramBotLogger`.
- v0.8.1 - Startup status banner cleanup
  - Added Perplexity API enabled/disabled status to the startup banner.
  - Reads Perplexity status from `[Perplexity] -> Enabled` in `config.ini`.
  - Kept startup/config handling simple and centralized in `utils.py`.
- v0.8.0 - OpenAI 5.x-era cleanup + Perplexity/DuckDuckGo compatibility hardening
  - Refactored `src/api_perplexity_search.py` for the current Perplexity/Sonar API workflow.
  - Kept Perplexity on the OpenAI-compatible Chat Completions endpoint by default:
    - `https://api.perplexity.ai/chat/completions`
  - Added configurable Perplexity endpoint support via `[Perplexity] -> Endpoint`.
  - Kept `sonar` as the default Perplexity model.
  - Added safer Perplexity config loading helpers:
    - `_cfg_get()`
    - `_cfg_getint()`
    - `_cfg_getfloat()`
  - Added explicit Perplexity API key validation for `PERPLEXITY_API_KEY`.
  - Added clearer Perplexity error returns for:
    - missing API key
    - empty question
    - bad/non-JSON response
    - HTTP errors
    - exhausted retries
  - Hardened Perplexity retry handling:
    - retryable HTTP status detection
    - timeout handling
    - request-error handling
    - exponential backoff with jitter
  - Added safer Perplexity response parsing through `_extract_perplexity_content()`.
  - Preserved old public Perplexity helper names/signatures so existing imports keep working:
    - `fact_check_with_perplexity()`
    - `query_perplexity()`
    - `smart_chunk()`
    - `rejoin_chunks()`
    - `format_headers_for_telegram()`
    - `markdown_to_html()`
    - `sanitize_urls()`
    - `split_message()`
    - `send_split_messages()`
    - `handle_long_response()`
    - `detect_language()`
  - Updated Perplexity-side `detect_language()` helper for newer OpenAI model payload rules:
    - no `temperature` for non-GPT-4-family models
    - `max_completion_tokens` for newer non-GPT-4-family models
    - `max_tokens` retained for GPT-4-family models
  - Removed stale hardcoded `gpt-4o-mini` fallback from Perplexity language detection.
  - Updated language detection fallback model handling to use the configured default model instead of old dead model names.
  - Refactored `src/api_get_duckduckgo_search.py` for modern OpenAI tool-calling compatibility.
  - Updated DuckDuckGo sub-agent browsing away from legacy-only `functions` / `function_call` handling.
  - Added modern OpenAI `tools` / `tool_choice` payload support for the DuckDuckGo sub-agent.
  - Added backward-compatible parsing for both:
    - modern `tool_calls`
    - legacy `function_call`
  - Added safer DuckDuckGo sub-agent response extraction to avoid brittle direct `choices[0]["message"]["content"]` assumptions.
  - Updated DuckDuckGo sub-agent model payload rules for newer OpenAI models:
    - GPT-4-family models may receive `temperature`
    - newer non-GPT-4-family models omit `temperature`
    - newer non-GPT-4-family models use `max_completion_tokens`
    - GPT-4-family models keep `max_tokens`
  - Updated DuckDuckGo default fallback model from old `gpt-4` assumptions to the newer configured model path / GPT-5.x-era default.
  - Kept DuckDuckGo search behavior compatible with non-agentic mode:
    - raw DuckDuckGo/lynx result fetching still works without invoking the sub-agent
    - duplicate links are filtered
    - DuckDuckGo redirect URLs are decoded back into original URLs
  - Hardened DuckDuckGo agentic browsing fallback behavior:
    - if the sub-agent returns empty output, raw DuckDuckGo results are returned
    - if webpage fetching fails, raw DuckDuckGo results are returned
    - if OpenAI sub-agent calls fail after retries, raw DuckDuckGo results are returned
  - Improved `lynx` webpage dump handling for DuckDuckGo agentic browsing.
  - Preserved configurable content-size limiting for fetched webpages:
    - `[DuckDuckGo] -> EnableContentSizeLimit`
    - `[DuckDuckGo] -> MaxContentSize`
  - Improved Telegram HTML formatting safety in DuckDuckGo search output.
  - Removed more stale pre-5.x OpenAI assumptions from auxiliary helper modules.
  - General cleanup of old compatibility corpse-code around model defaults, token-limit parameters, and function/tool-call parsing.
- v0.77.1 - OpenAI newer model (5.x series) / tools compatibility update
  - Added support for modern OpenAI Chat Completions tool calling via `tools` / `tool_choice` / `tool_calls`.
  - Added backward-compatible parsing for both modern `tool_calls` and legacy `function_call` responses.
  - Added `build_openai_tools()` to convert the existing legacy ChatKeke `custom_functions` format into OpenAI's modern tools format.
  - Added `extract_function_call_or_none()` so function-call detection no longer depends only on the old `message["function_call"]` field.
  - Updated payload building so function calling can work with newer model families, including GPT-5.x-style models.
  - Restricted `temperature` to GPT-4-family models only, avoiding API errors from newer reasoning-style models that reject sampling parameters.
  - Uses `max_completion_tokens` for newer non-GPT-4 models while keeping `max_tokens` for GPT-4-family models.
  - Hardened OpenAI response parsing to avoid confusing `KeyError: 'choices'` failures when the API returns an error body.
  - Added safer handling for missing or empty `choices` responses.
  - Updated function-call follow-up calls so tool results are appended into chat context and the final user-facing answer is generated with `include_functions=False`, reducing accidental recursive tool calls.
  - Updated affected function branches:
    - `calculate_expression`
    - `get_weather`
    - `get_duckduckgo_search`
    - `get_website_dump`
    - `get_stock_price`
    - `query_perplexity`
    - `manage_reminder`
- v0.7616 - Changed default Perplexity API model to `sonar` as per new model changes in the Perplexity API
- v0.7615 - Parsing improvements
  - Improved text formatting & escaping in complex markdown vs. html cases
- v0.7614 - Better stock market data fetching from Yahoo Finance 
  - Changes made to `src/api_get_stock_prices_yfinance.py`
  - => More accurate ticker symbol searches, fallbacks, multi-day data etc.
- v0.7613 - Improved timestamps on multiple timezones
  - Added a separate module to `src/timedate_handler.py` to assist the model
  - => Datetime stamps now in separate system messages
  - => More TZ-aware dates and times
- v0.7611 - Parsing hotfix for notifications
- v0.761 - **Timed notifications / user reminders**
  - Brand-new feature: users can set timed reminders (alerts) by requesting reminders that the bot stores in an SQLite database. A separate poller picks them up as soon as they are due, and the bot automatically notifies the user on set times.
  - The custom function calling view action can also list your recently passed or deleted reminders (configurable in `[Reminders]` -> `ShowPastRemindersCount`).
  - The bot ensures a max limit of pending reminders per user (set with `MaxAlertsPerUser`; set to 0 for unlimited alerts).
- v0.76 - **Premium mode auto-switching** + usage DB synergy
  - Added daily usage-based auto-switch logic between “premium” vs. “mini” models (see `[ModelAutoSwitch]` in `config.ini`).
  - Once you exceed the `PremiumTokenLimit`, the bot seamlessly switches to the fallback model.
  - If that fallback also goes past `MiniTokenLimit`, the bot can either deny usage or proceed, according to `FallbackLimitAction`.
  - New param `model_info` for logging function calls, so the “Bot” lines in your chat log can show which model/tier is used (i.e. `model=gpt-4, tier=premium, usage=12345/500000`).
  - Some small bugfixes for the SQLite usage DB, ensuring we properly update `premium_tokens` or `mini_tokens` after each request based on the `usage` field in OpenAI’s response.
- 0.75056 - switched to newer Perplexity API models due to new models / old model depreciation
  - see [Perplexity API guide for supported models](https://docs.perplexity.ai/guides/model-cards)
- v0.75055 - fixes to the html sanitizer (for Telegram's API; better handling of malformed html), using BeautifulSoup4+lxml for parsing now
- v0.75054 - small fixes and more error catching in `calc_module.py`
- v0.75053 - only include eligible territories in U.S. NWS queries
  - list of queried / eligible territories can be set in `config.ini` under the `NWS` section
- v0.75052 - include the details from U.S. National Weather Service on alerts
- v0.75051 - updated `config.ini` for configuring NWS weather forecasts & alerts
  - suggested method is to supplement via NWS the additional weather data you need
  - leaving U.S. NWS's weather alerts on in `config.ini` is highly recommended, even if you have other fetching methods enabled (i.e. OpenWeatherMap), rather be safe than sorry
- v0.7505 - U.S. NWS (National Weather Service, [weather.gov](https://weather.gov)) added as a weather data source
  - for additional information; **especially weather alerts**
  - all data will be combined from OpenWeatherMap and U.S. NWS sources by default
- v0.7504 - fixed usage logs and charts directory mapping
- v0.7503 - improved message formatting & error catching
- v0.7502 - added `docker_setup.sh` for easier Docker-based deployment
- v0.7501 - `Dockerfile` and better error catching when receiving `401 Unauthorized`
- v0.75 **Major refactoring** _(5. Oct 2024)_ 👀💦🌀
  - entire project has been tidied up and a lot of bugs fixed while at it
  - `python src/main.py` to start the bot from here on out
  - massive list of new features, such as:
    - improved logging
    - checking for Elasticsearch on startup; multi-step exception catching
    - Elasticsearch verbosity added for clarity
    - Elasticsearch can now be configured via `config.ini`
    - enhanced logging (chat + bot data into separate unified logging)
    - chatlogs now have a `source` for them whenever called via function calls, so that any external data pulls are now logged more clearly
    - overall this update makes the bot very much more easily deployable
- v0.7431 - potential handling of API keys as textfiles moved under `config/` by default
- v0.743 - config loading changes & streamlining
  - tidying up; all configurations are now under `config/`
  - imported the new logic for bot token reading from my [`whisper-transcriber-telegram-bot`](https://github.com/FlyingFathead/whisper-transcriber-telegram-bot/)
  - `bot_token.py` changed and updated accordingly
  - `config_paths.py` now has the project-wide configuration for configuration file paths (`config.ini`, etc...)
  - move any existing `bot_token.txt` (if used) to `config/`
  - use `configmerger.py` to update with your custom configs
  - (more WIP on project restructuring front)
- v0.742 - Finnish name day RAG step fetch
- v0.741 - changed to most current Perplexity API model (`llama-3.1-sonar-small-128k-online`) due to deprecations and updates in their models
- v0.74 - sub-agentic browsing with DuckDuckGo search engine searches is here! 
  - Enabled from `config.ini` via `EnableAgenticBrowsing = True`
  - It allows the AI helper to follow links for further info and return relevant results
  - Additional bugfixes to edge cases and their output parsing
- v0.7373 - small fixes to `api_get_duckduckgo_search.py`; agentic link following WIP
- v0.7372 - Further parsing logic changes (`markdown_to_html` in `modules.py`)
- v0.7371 - Improved parsing for markdown/html
- v0.737 - Changes to Perplexity API inclusion (main model now includes it in the context for better applicability and coherence.)
- v0.736 - Calculator module `calc_module.py` added for precision in calculation requests. 
- v0.735 - Lynx website browsing with allow/disallow lists for domains allowed/disallowed to be viewed
- v0.734 - Now hosting over 100 RSS feeds by default (when RAG triggered)
  - DuckDuckGo searches added as a function call
- v0.733 - RSS parsing logic streamlined into RAG context
- v0.7321 - RSS parsing improvements
- v0.732 - added ElasticSearch RAG function calls to RSS feeds 
  - (for i.e. news sources etc, see `rss_parser.py`)
- v0.73101 - modularized Perplexity API calls further into a separate handler
  - (see: `perplexity_handler.py`)
- v0.731 - added Yahoo! Finance as an API function call for stock price searches (requires the `yfinance` pip package)
- v0.730 - added Alpha Vantage API function calling to fetch stock prices in real time (requires Alpha Vantage API key)
- v0.729 - switched to `gpt-4o-mini` in default configurations instead of `gpt-3.5-turbo` (newer, cheaper, better)
- v0.728 - more edge case handling when fetching multi-API weather data
- v0.727 - fixed WeatherAPI & weather fetching edge case API glitches (returning odd values, etc)
- v0.726 - switched to OpenAI API from `langdetect` when using i.e. Perplexity API for information queries
  - (`detect_language` function in `api_perplexity_search.py`)
  - this is for better accuracy in multilingual environments 
  - => less responses in wrong language when a translation path is needed for the end-user
  - much more accurate than `langdetect` and can be further leveraged with model selection
- v0.7251 - small robustness improvements & fixes to the `api_key.py` module
- v0.725 - additional Perplexity API call + translation adjustments
- v0.724 - splitting logic for lengthier Perplexity API responses
- v0.723 - added jitter, modified retry logic in Perplexity API+translation requests
- v0.7201 - added Perplexity API model configuration to `config.ini`
- v0.72 - improved error catching + messaging with Perplexity's API
- v0.71 - holiday mentions via Python's `holidays` module (can be extended)
- v0.708 - improved astronomy data combining via WeatherAPI
- v0.707 - code cleanup + enhancements to Perplexity API handling
- v0.706 - further weather fetching options; additional country-based data fetching
- v0.705 - improved weather data combining; small tweaks
- v0.703 - Language translations and tweaks to WeatherAPI data fetching
- v0.70 - WeatherAPI support added, to enable, get an API key from weatherapi.com
- v0.61 - improved handling of weather and time/data data globally
- v0.60 - url info pre-parsing and additional info fetching for media sources, i.e. with `yt-dlp`
- v0.59 - custom function calling via Elasticsearch RAG (if enabled)
- v0.58.4 - more parsing & formatting fixes
- v0.58.3 - parsing, formatting & chunking adjustments
- v0.58.2 - improved formatting in pplx API calls
- v0.58.1 - improved markdown parsing in translated Perplexity API calls
- v0.58 - chunking, parsing and other small fixes
- v0.57.5 - changes made to Perplexity API handling; new sonar-online models
- v0.57.1 - improved fallbacks on external API calls like Perplexity API
- v0.57 - improved error catching & failsafe fallbacks
- v0.56 - **Added Elasticsearch support for RAG** - use the `ElasticsearchEnabled` flag in new `config.ini` (set to `True` or `False` to enable or disable)
- v0.55.4 - API call tracking, extra wait times if needed for external API calls
- v0.55.3 - reply activity, better chunking logic
- v0.55 - better reply animation handling
- v0.52 - more accurate weather data globally via the OpenWeatherMap API & Maptiler API
- v0.51 - "smart" chunking of external requests to mitigate timeout-related issues
- v0.50.3 - `langdetect` & handling fixes
- v0.50.2 - typing animation on replies, adjustments on processing logic
- v0.50.1 - `langdetect` on auto-assessing translation requirements
- v0.50 - Custom function call: Perplexity API fact-checking
- v0.49.1 - Modularity adjustments
- v0.48 - Openrouteservice API implementation
- v0.47 - more token counting & polling logic fixes
- v0.46.2 - fixes to token count & polling logic
- v0.46 - rewrote the polling logic on daily token count resets
- v0.45 - `/usagechart` feature added for utilization charts (requires `matplotlib`)
- v0.44 - API function calling, OpenWeatherMap API weather searches and MapTiler API geolookup
- v0.43.2 - Fixed a small bug in daily token caps
- v0.43.1 - Better error catching
- v0.43 - New admin commands: `/setsystemmessage <message>` (valid until bot restart) and `/resetsystemmessage` (reset from `config.ini`)
- v0.42 - `/reset` command added for bot reset. Set `ResetCommandEnabled` and `AdminOnlyReset` flags in `config.ini` accordingly.
- v0.41 - modularized text message handling to `text_message_handler.py` and voice message handling to `voice_message_handler.py`
- v0.40 - session timeout management for compacting chat history (see `config.ini` => `SessionTimeoutMinutes`, `MaxRetainedMessages`)
- v0.39.5 - small fixes to OpenAI API payload implementation
- v0.39.4 - modularized `log_message` & `rotate_log_file` (log file handling) => `modules.py`
- v0.39.3 - modularized `check_global_rate_limit` => `modules.py`
- v0.39.2 - text style parsing and WhisperAPI STT pre-processing for the model improved
- v0.39 - better parsing for codeblocks, html and other markups, modularized more; see `modules.py`
- v0.38 - keep better record of daily token usage, streamlined (**note**: you will need to clear out your existing `token_usage.json`, the file structure has changed from the previous version)
- v0.37 - better enforcing of voice msg limits
- v0.36 - bot command fixes and adjustments
- v0.35 - modularized bot commands to `bot_commands.py`, fixed `configmerger.py` version
- v0.34 - added `configmerger.py` to ease updating the bot (merge old configuration flags with new versions)
- v0.33 - more performance fixes and added+unified async functionalities 
- v0.32 - Daily token counter reset polling & small bugfixes
- v0.31 - Context memory token counter adjusted & fixed to be more precise
- v0.30 - Whisper API interaction fine adjustments & small fixes
- v0.29 - **WhisperAPI transcriptions via voice messages added** 
- WhisperAPI voice messages use the same OpenAI API token as the regular text chat version
  - see the `config.ini` to turn the option on or off
  - WIP for additional transcription features
- v0.28 - customizable `/start` greeting in `config.ini`
- v0.27 - added `/usage` command to track token usage (for bot owner only, 0 to disable in `config.ini`)
- v0.26 - added separate chat logging and a global limiter functionality for requests/min (see `config.ini`)
- v0.25 - daily token usage limit functionality
  - added a functionality to set daily token usage limits (for bot cost control), see `config.ini`
  - modularized extra utils (startup msg etc) into `utils.py`
- v0.24 - bug fixes & rate limit pre-alpha
- v0.23 - option to log to file added, see new logging options in `config.ini`
- v0.22 - `escape_markdown` moved into a separate `.py` file, it was unused anyway
- v0.21 - Comprehensive Refactoring and Introduction of Object-Oriented Design
  - Implemented object-oriented programming principles by encapsulating bot functionality within the TelegramBot class.
  - Refined code structure for improved readability, maintainability, and scalability.
- v0.20 - modularization, step 1 (key & token reading: `api_key.py`, `bot_token.py`)
- v0.19 - timeout error fixes, retry handling; `Timeout` value added to `config.ini`
- v0.18 - model temperature can now be set in `config.ini`
- v0.17 - time & date stamping for better temporal awareness
- v0.16 - `/help` & `/about`
- v0.15 - chat history context memory (trim with MAX_TOKENS)
- v0.14 - bug fixes
- v0.13 - parsing/regex for url title+address markdowns
- v0.12 - more HTML regex parsing from the API markdown
- v0.11 - switched to HTML parsing
- v0.10 - MarkdownV2 tryouts (code blocks + bold is _mostly_ working)
- v0.09 - using MarkdownV2
- v0.08 - markdown for bot's responses
- v0.07 - log incoming and outgoing messages
- v0.06 - API system message fixed
- v0.05 - retry, max retries, retry delay
- v0.04 - chat history trimming

# Contribute
- All contributions appreciated! Feel free to also post any bugs and other issues on the repo's "Issues" page.
- **Don't forget to star it if you like it. :-)**

# About
- Written by [FlyingFathead](https://github.com/FlyingFathead/)
- Digital ghost code by ChaosWhisperer
