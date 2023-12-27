# ~~~ read the telegram bot token ~~~

import os

def get_bot_token():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if bot_token is None:
        try:
            with open('bot_token.txt', 'r') as file:
                bot_token = file.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError("The TELEGRAM_BOT_TOKEN environment variable is not set, and bot_token.txt was not found.")
    return bot_token