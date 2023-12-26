# Simple OpenAI API-utilizing Telegram Bot
# Creation Date: Dec 26 2023
version_number = "0.17"

# changelog/history:
# v0.17 - timestamps, realtime date &  clock
# v0.16 - `/help` & `/about`
# v0.15 - chat history context memory (trim with MAX_TOKENS)
# v0.14 - bug fixes
# v0.13 - parsing/regex for url title+address markdowns
# v0.12 - more HTML regex parsing from the API markdown
# v0.11 - Switch to HTML parsing
# v0.10 - MarkdownV2 tryouts
# v0.09 - using MarkdownV2
# v0.08 - markdown for bot's responses
# v0.07 - log incoming and outgoing messages
# v0.06 - system instructions
# v0.05 - retry, max retries, retry delay
# v0.04 - chat history trimming

# by FlyingFathead ~*~ https://github.com/FlyingFathead
# ghostcode: ChaosWhisperer
# https://github.com/FlyingFathead/TelegramBot-OpenAI-API

import datetime
import configparser
import os
import sys
import logging
import openai
import json
import httpx
import asyncio
import re

from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext
# Import the required utility function and enumeration
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

# Load configuration
def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config['DEFAULT']

config = load_config()

# Set parameters from config
MODEL = config.get('Model', 'gpt-3.5-turbo')
MAX_TOKENS = config.getint('MaxTokens', 4096)
SYSTEM_INSTRUCTIONS = config.get('SystemInstructions', 'You are an OpenAI API-based chatbot on Telegram.')
MAX_RETRIES = config.getint('MaxRetries', 3)  # Fallback to 3 if not set
RETRY_DELAY = config.getint('RetryDelay', 10)  # Fallback to 2 if not set

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
logging.basicConfig(format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to handle start command
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hello! I am a chatbot powered by OpenAI API. Start chatting with me!')

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

""" # Define a function to send a typing action
def send_typing_action(update, context):
    context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING) """

# Define a function to update chat history in a file
def update_chat_history(chat_history):
    with open('chat_history.txt', 'a') as file:
        for message in chat_history:
            file.write(message + '\n')

# Define a function to retrieve chat history from a file
def retrieve_chat_history():
    chat_history = []
    try:
        with open('chat_history.txt', 'r') as file:
            chat_history = [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        pass
    return chat_history

# convert markdowns to html
def markdown_to_html(text):
    # Escape HTML special characters
    text = (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

    # Convert markdown code blocks to HTML <pre> tags
    text = re.sub(r'```(.*?)```', r'<pre>\1</pre>', text, flags=re.DOTALL)

    # Convert markdown inline code to HTML <code> tags
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)

    # Convert bold text using markdown syntax to HTML <b> tags
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    # Convert italic text using markdown syntax to HTML <i> tags
    # text = re.sub(r'\b_(.*?)_\b', r'<i>\1</i>', text)
    # Convert italic text using markdown syntax to HTML <i> tags
    # The regex here is looking for a standalone asterisk or underscore that could denote italics
    # It's also making sure that it doesn't capture bold syntax by checking that an asterisk or underscore is not followed or preceded by another asterisk or underscore
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', text)

    # Convert [text](url) to clickable links
    text = re.sub(r'\[(.*?)\]\((https?://\S+)\)', r'<a href="\2">\1</a>', text)

    return text

# escape markdown v2, v0.12 [currently not in use because this is a ... it's a thing]
def escape_markdown_v2(text):
    # Escape MarkdownV2 special characters
    def escape_special_chars(m):
        char = m.group(0)
        # Escape all special characters with a backslash, except for asterisks and underscores
        if char in ('_', '*', '`'):
            # These are used for formatting and shouldn't be escaped.
            return char
        return '\\' + char

    # First, we'll handle the code blocks by temporarily removing them
    code_blocks = re.findall(r'```.*?```', text, re.DOTALL)
    code_placeholders = [f"CODEBLOCK{i}" for i in range(len(code_blocks))]
    for placeholder, block in zip(code_placeholders, code_blocks):
        text = text.replace(block, placeholder)

    # Now we escape the special characters outside of the code blocks
    text = re.sub(r'([[\]()~>#+\-=|{}.!])', escape_special_chars, text)

    # We convert **bold** and *italic* (or _italic_) syntax to Telegram's MarkdownV2 syntax
    # Bold: **text** to *text*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    # Italic: *text* or _text_ to _text_ (if not part of a code block)
    text = re.sub(r'\b_(.+?)_\b', r'_\1_', text)
    text = re.sub(r'\*(.+?)\*', r'_\1_', text)

    # Restore the code blocks
    for placeholder, block in zip(code_placeholders, code_blocks):
        text = text.replace(placeholder, block)

    return text

# message handling logic
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    chat_id = update.message.chat_id

    # get date & time for timestamps
    now_utc = datetime.datetime.utcnow()
    utc_timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    day_of_week = now_utc.strftime("%A")
    user_message_with_timestamp = f"[{utc_timestamp}] {user_message}"

    # Send initial response
    # await context.bot.send_message(chat_id=chat_id, text="I'm processing your request...")

    # ... Simulate typing or generating content ...
    # await asyncio.sleep(2)  # Simulate a 2-second delay

    # Log the incoming user message
    logger.info(f"Received message from {update.message.from_user.username} ({chat_id}): {user_message}")

    # Log the current chat history
    logger.debug(f"Current chat history: {context.chat_data.get('chat_history')}")

    """ # Prepare the conversation history for the current chat
    if 'chat_history' not in context.chat_data:
        context.chat_data['chat_history'] = [] """

    # Initialize chat_history as an empty list if it doesn't exist
    chat_history = context.chat_data.get('chat_history', [])

    # Append the new user message to the chat history
    chat_history.append({"role": "user", "content": user_message_with_timestamp})

    # Prepare the conversation history to send to the OpenAI API
    system_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    system_message = {"role": "system", "content": f"System message ({system_timestamp}, {day_of_week}): {SYSTEM_INSTRUCTIONS}"}
    
    chat_history_with_system_message = [system_message] + chat_history

    # Trim chat history if it exceeds a specified length or token limit
    trim_chat_history(chat_history, MAX_TOKENS)

    for attempt in range(MAX_RETRIES):
        try:
            # Prepare the payload for the API request
            payload = {
                "model": MODEL,
                #"messages": context.chat_data['chat_history'],
                "messages": chat_history_with_system_message,  # Updated to include system message                
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

            # Log the API request payload
            logger.info(f"API Request Payload: {payload}")

            # Extract the response and send it back to the user
            bot_reply = response_json['choices'][0]['message']['content'].strip()

            # Log the bot's response
            logger.info(f"Bot's response to {update.message.from_user.username} ({chat_id}): {bot_reply}")

            # Append the bot's response to the chat history
            chat_history.append({"role": "assistant", "content": bot_reply})

            # Update the chat history in context with the new messages
            context.chat_data['chat_history'] = chat_history

            # HTML markdown, not in use
            # await context.bot.send_message(chat_id=chat_id, text=bot_reply, parse_mode="HTML")

            # Escape the bot's response
            # escaped_reply = escape_markdown_v2(bot_reply)

            # Send the escaped message as a reply
            # await context.bot.send_message(chat_id=chat_id, text=escaped_reply, parse_mode="MarkdownV2")
            
            print("Reply message before escaping:", bot_reply, flush=True)
            # escaped_reply = escape_markdown(bot_reply, version=2)
            # escaped_reply = escape_markdown_v2(bot_reply)
            escaped_reply = markdown_to_html(bot_reply)
            print("Reply message after escaping:", escaped_reply, flush=True)

            await context.bot.send_message(
                chat_id=chat_id,
                text=escaped_reply,
                parse_mode=ParseMode.HTML
            )
                # parse_mode=ParseMode.MARKDOWN_V2

            # bot timestamps (optional)
            # bot_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # bot_reply_with_timestamp = f"{bot_timestamp} - {bot_reply}"

            # reply with markdown v2 escapes
            # escaped_reply = simple_escape_markdown_v2(bot_reply)
            # await context.bot.send_message(chat_id=chat_id, text=escaped_reply, parse_mode="MarkdownV2")
            
            # ... no escape-reply ...
            # await context.bot.send_message(chat_id=chat_id, text=bot_reply, parse_mode="MarkdownV2")
            
            # test
            # await context.bot.send_message(chat_id=chat_id, text="**bold**", parse_mode="MarkdownV2")
            
            break  # Break the loop if successful

        except httpx.ReadTimeout:
            if attempt < MAX_RETRIES - 1: # If not the last attempt
                await asyncio.sleep(RETRY_DELAY) # Wait before retrying
            else:
                logger.error("Max retries reached. Giving up.")
                await context.bot.send_message(chat_id=chat_id, text="Sorry, I'm having trouble connecting. Please try again later.")
                break

        except Exception as e:
            logger.error(f"Error during message processing: {e}")
            await context.bot.send_message(chat_id=chat_id, text="Sorry, there was an error processing your message.")
            break  # Exit on other types of exceptions

    # Trim chat history if it exceeds a specified length or token limit
    trim_chat_history(chat_history, MAX_TOKENS)

    # Update the chat history in context with the new messages
    context.chat_data['chat_history'] = chat_history

# Function to handle the /help command
async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = """
    Welcome to this OpenAI API-powered chatbot! Here are some commands you can use:

    - /start: Start a conversation with the bot.
    - /help: Display this help message.
    - /about: Learn more about this bot.
    
    Just type your message to chat with the bot!
    """
    await update.message.reply_text(help_text)

# Function to handle the /about command
async def about_command(update: Update, context: CallbackContext) -> None:
    about_text = f"""
    This is an OpenAI-powered Telegram chatbot created by FlyingFathead.
    Version: v{version_number}
    For more information, visit: https://github.com/FlyingFathead/TelegramBot-OpenAI-API
    """
    await update.message.reply_text(about_text)

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

    # Register additional command handlers
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()    