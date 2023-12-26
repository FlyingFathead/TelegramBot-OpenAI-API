# Simple OpenAI API-utilizing Telegram Bot
# v0.04
# Dec 26 2023
#
# changelog/history:
# v0.04 - chat history trimming
#
# by FlyingFathead ~*~ https://github.com/FlyingFathead
# https://github.com/FlyingFathead/TelegramBot-OpenAI-API

import configparser
import os
import sys
import logging
import openai
import json
import httpx

from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext

# from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Load configuration
def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config['DEFAULT']

config = load_config()

# Set parameters from config
MODEL = config.get('Model', 'gpt-3.5-turbo')
MAX_TOKENS = config.getint('MaxTokens', 4096)
SYSTEM_MESSAGE = config.get('SystemMessage', '')

# ~~~ read the telegram bot token ~~~
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if TELEGRAM_BOT_TOKEN is None:
    try:
        with open('bot_token.txt', 'r') as file:
            TELEGRAM_BOT_TOKEN = file.read().strip()
    except FileNotFoundError:
        print("Error: The TELEGRAM_BOT_TOKEN environment variable is not set, and bot_token.txt was not found.")
        sys.exit(1)

if TELEGRAM_BOT_TOKEN is None:
    print("Error: Failed to obtain Telegram bot token. Please set the TELEGRAM_BOT_TOKEN environment variable or create a file named `bot_token.txt` with your Telegram bot token in it.")
    sys.exit(1)
# ~~~

# ~~~ read the openai api key ~~~
# API key reading
# First, try to get the API key from an environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# If the environment variable is not set, try to read the key from a file
if openai.api_key is None:
    try:
        with open('api_token.txt', 'r') as file:
            openai.api_key = file.read().strip()
    except FileNotFoundError:
        print("Error: The OPENAI_API_KEY environment variable is not set, and api_token.txt was not found. Please set the environment variable or create this file with your OpenAI API key.")
        sys.exit(1)

# If the key is still None at this point, neither method was successful
if openai.api_key is None:
    print("Error: Failed to obtain OpenAI API key. Please set the OPENAI_API_KEY environment variable or create a file named `api_token.txt` with your OpenAI API key in it.")
    sys.exit(1)
# ~~~

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to handle start command
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hello! I am a chatbot powered by GPT-3.5. Start chatting with me!')

# trim the chat history to meet up with max token limits
def trim_chat_history(chat_history, max_total_tokens):
    total_tokens = sum(len(message['content'].split()) for message in chat_history)
    while total_tokens > max_total_tokens and len(chat_history) > 1:
        removed_message = chat_history.pop(0)
        total_tokens -= len(removed_message['content'].split())

# max token estimates
def estimate_max_tokens(input_text, max_allowed_tokens):
    # Rough estimation of the input tokens
    input_tokens = len(input_text.split())
    max_tokens = max_allowed_tokens - input_tokens
    # Ensure max_tokens is positive and within a reasonable range
    return max(1, min(max_tokens, max_allowed_tokens))

# message handling logic
# Function to handle messages
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    chat_id = update.message.chat_id

    # Prepare the conversation history for the current chat
    if 'chat_history' not in context.chat_data:
        context.chat_data['chat_history'] = []

    # Trim the chat history if necessary
    trim_chat_history(context.chat_data['chat_history'], MAX_TOKENS)

    # Append the new user message to the chat history
    context.chat_data['chat_history'].append({"role": "user", "content": user_message})

    try:
        # Prepare the payload for the API request
        payload = {
            "model": MODEL,
            "messages": context.chat_data['chat_history'],
            "temperature": 0.7
        }

        # Make the API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
        }
        response = httpx.post("https://api.openai.com/v1/chat/completions", 
                              data=json.dumps(payload), 
                              headers=headers)
        response_json = response.json()

        # Extract the response
        bot_reply = response_json['choices'][0]['message']['content'].strip()

        # Send the response back to the user
        await context.bot.send_message(chat_id=chat_id, text=bot_reply)

    except Exception as e:
        logger.error(f"Error during message processing: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Sorry, there was an error processing your message.")

# Function to handle start command
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hello! I am a chatbot powered by GPT-3.5. Start chatting with me!')

# Function to handle errors
def error(update: Update, context: CallbackContext) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)

# Main function to start the bot
def main() -> None:
    # Create an Application instance
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()