# ~~~ read the telegram bot token ~~~
import os
import sys

# set `prefer_env` to `True` if you wish to prioritize the environment variable over the configuration text file (determines load order)
def get_bot_token(prefer_env=True):
    if prefer_env:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if bot_token is not None:
            return bot_token

    try:
        with open('bot_token.txt', 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        if not prefer_env:
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if bot_token is not None:
                return bot_token

        print("The TELEGRAM_BOT_TOKEN environment variable is not set, and `bot_token.txt` was not found.")
        sys.exit(1)