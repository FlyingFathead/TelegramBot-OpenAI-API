# test to see if your TG bot token is available in the environment

import os
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)

def get_bot_token():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logging.error("Failed to retrieve TELEGRAM_BOT_TOKEN from environment.")
        return None
    return bot_token

if __name__ == "__main__":
    token = get_bot_token()
    if token:
        logging.info(f"Successfully retrieved bot token: {token[:4]}... (masked for security)")
    else:
        logging.critical("No bot token found. Exiting.")
        exit(1)
