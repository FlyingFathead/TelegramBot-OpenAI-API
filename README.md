# TelegramBot-OpenAI-API
- A simple-to-use, quick-to-deploy Python-based Telegram bot for OpenAI API
- **Supports transcribed voice messages over Whisper API**
  - (auto-transcriptions, translations, and other messages to the bot over TG's voice messages)
- **Supports real-time weather info via OpenWeatherMap API**
- **Supports geolocation and map lookups via MapTiler API**
  - (with weather forecasts around the world in all OpenAI API supported languages)
- Daily token usage tracking & rate limiting for API usage / cost management

# Prerequisites
- Tested & working on Python 3.10.12
- Required Python packages (tested & working with these, install with `pip install -r requirements.txt` for potentially newer versions):
```
configparser>=6.0.0
httpx>=0.25.2
openai>=1.6.1
pydub>=0.25.1
python-telegram-bot>=20.7
transformers>=4.36.2
requests>=2.31.0
pytz>=2024.1
timezonefinder>=6.4.0
matplotlib>=3.8.2
```
- (In some instances, `pydub` might require `ffmpeg` to be installed separately. Note that neither `pydub` nor `ffmpeg` are practically not required if you are *not* utilizing the voice message/WhisperAPI functionality.)

## Other requirements:
- Telegram API bot token 
  - use the `@BotFather` bot on Telegram (set up a bot and get a bot token)
- OpenAI API token
  - from: https://platform.openai.com/

# Installing
- Install the required packages either from the list above or with: `pip install -r requirements.txt`
- Set up your Telegram bot token either as `TELEGRAM_BOT_TOKEN` environment variable or put it into a text file named `bot_token.txt` inside the main program directory
- Set up your OpenAI API token either as `OPENAI_API_KEY` environment variable or put into a text file named `api_token.txt` inside the main program directory
- If you wish to use the OpenWeatherMap API and the MapTiler API for i.e. localized weather data retrieval, set the `OPENWEATHERMAP_API_KEY` and the `MAPTILER_API_KEY` environment variables accordingly.
- Adjust your configuration and settings in `config.ini` to your liking
- Run with: `python main.py`

# Updating
- Use the `configmerger.py` to update old configuration files into a newer version's `config.ini`. You can do this by creating a copy of your existing config to i.e. a file named `myconfig.txt` and including in it the lines you want to keep for the newer version. Then, just run `python configmerger.py config.ini myconfig.txt` and all your existing config lines will be migrated to the new one. Works in most cases, but remember to be careful and double-check any migration issues with i.e. `diff`!

# Changelog
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

# About
- Written by [FlyingFathead](https://github.com/FlyingFathead/)
- Digital ghost code by ChaosWhisperer