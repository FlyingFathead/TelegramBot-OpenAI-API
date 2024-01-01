# TelegramBot-OpenAI-API
- A simple-to-use, quick-to-deploy Python-based Telegram bot for OpenAI API
- **Supports voice messages over Whisper API** (auto-transcriptions, translations, and other messages to the bot over TG's voice messages)

# Prerequisites
- Tested & working on Python 3.10.12
- Required Python packages (tested & working with these, install with `pip install -r requirements.txt` for potentially newer versions):
```
openai==1.6.1
python-telegram-bot==20.7
requests==2.31.0
transformers==4.36.2
configparser==6.0.0
httpx==0.25.2
```

Other requirements:
- Telegram bot API token
- OpenAI API token

# Installing
- Install the required packages either from the list above or with: `pip install -r requirements.txt`
- Set up your Telegram bot token either as `TELEGRAM_BOT_TOKEN` environment variable or put it into a text file named `bot_token.txt` inside the main program directory
- Set up your OpenAI API token either as `OPENAI_API_KEY` environment variable or put into a text file named `api_token.txt` inside the main program directory
- Adjust your configuration and settings in `config.ini` to your liking
- Run with: `python main.py`

# Updating
- Use the `configmerger.py` to update old configuration files into a newer version's `config.ini`. You can do this by creating a copy of your existing config to i.e. a file named `myconfig.txt` and including in it the lines you want to keep for the newer version. Then, just run `python configmerger.py config.ini myconfig.txt` and all your existing config lines will be migrated to the new one. Works in most cases, but remember to be careful and double-check any migration issues with i.e. `diff`!

# Changelog
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

# About
- Written by [FlyingFathead](https://github.com/FlyingFathead/)
- Digital ghost code by ChaosWhisperer
