# ~~~ read the telegram bot token ~~~
import os
import sys

def get_bot_token():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if bot_token is None:
        try:
            with open('bot_token.txt', 'r') as file:
                bot_token = file.read().strip()
        except FileNotFoundError:
            print("The TELEGRAM_BOT_TOKEN environment variable is not set, and `bot_token.txt` was not found. Please configure the either the `TELEGRAM_BOT_TOKEN` environment variable, OR insert your TG bot token inside a text file in this directory named `bot_token.txt`.")
            sys.exit(1)
    return bot_token