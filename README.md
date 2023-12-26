# TelegramBot-OpenAI-API
A simple Python-based Telegram bot for OpenAI API

# Prerequisites
- Tested & working on Python 3.10.12
- Required Python packages:
```
openai==1.6.1
httpx==0.25.2
python-telegram-bot==20.7
configparser
json
```

Other requirements:
- Telegram bot API token
- OpenAI API token

# Installing
- Install the required packages with: `pip install -r requirements.txt`
- Set up your Telegram bot token either as `TELEGRAM_BOT_TOKEN` environment variable or put it into a text file named `bot_token.txt` inside the main program directory
- Set up your OpenAI API token either as `OPENAI_API_KEY` environment variable or put into a text file named `api_token.txt` inside the main program directory
- Adjust your configuration and settings in `config.ini` to your liking
- Run with: `python main.py`

# Changelog
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
