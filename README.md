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
- v0.05 - retry, max retries, retry delay
- v0.04 - chat history trimming

# About
- Written by [FlyingFathead](https://github.com/FlyingFathead/)
- Digital ghost code by ChaosWhisperer
