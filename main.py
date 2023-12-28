# Simple OpenAI API-utilizing Telegram Bot // v0.23
#
# by FlyingFathead ~*~ https://github.com/FlyingFathead
# ghostcode: ChaosWhisperer
# https://github.com/FlyingFathead/TelegramBot-OpenAI-API

# main modules
import datetime
import configparser
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import openai
import json
import httpx
import asyncio
import re

# for token counting
from transformers import GPT2Tokenizer

# for telegram
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from functools import partial

# tg-bot specific stuff
from bot_token import get_bot_token
from api_key import get_api_key
import utils

# version of this program
version_number = "0.25"

# Call the startup message function
utils.print_startup_message(version_number)

# Enable logging
logging.basicConfig(format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the tokenizer globally
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

class TelegramBot:
    # version of this program
    version_number = version_number

    def __init__(self):
        # get our bot & api tokens
        try:
            self.telegram_bot_token = get_bot_token()
            openai.api_key = get_api_key()
        except FileNotFoundError as e:
            self.logger.error(f"Required configuration not found: {e}")
            sys.exit(1)

        self.config = self.load_config()
        self.model = self.config.get('Model', 'gpt-3.5-turbo')
        self.max_tokens = self.config.getint('MaxTokens', 4096)
        self.system_instructions = self.config.get('SystemInstructions', 'You are an OpenAI API-based chatbot on Telegram.')
        self.max_retries = self.config.getint('MaxRetries', 3)
        self.retry_delay = self.config.getint('RetryDelay', 25)
        self.temperature = self.config.getfloat('Temperature', 0.7)
        self.timeout = self.config.getfloat('Timeout', 30.0)
        self.logfile_enabled = self.config.getboolean('LogFileEnabled', True)
        self.logfile_file = self.config.get('LogFile', 'bot.log')
        self.max_tokens_config = self.config.getint('GlobalMaxTokenUsagePerDay', 100000)

        self.logger = logging.getLogger('TelegramBotLogger')
        self.logger.setLevel(logging.INFO)  # Set to DEBUG if you want to capture all messages

        self.token_usage_file = 'token_usage.json'
        self.total_token_usage = self.read_total_token_usage()

        # Configure logging
        if self.logfile_enabled:
            file_handler = RotatingFileHandler(self.logfile_file, maxBytes=1048576, backupCount=5)
            file_handler.setLevel(logging.INFO)  # Or set to DEBUG

            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.propagate = True  # True/False = Start/Stop propagation to the root logger

            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.ERROR)  # Set this to the desired log level for console output
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        return config['DEFAULT']

    # count token usage
    def count_tokens(self, text):
        return len(tokenizer.encode(text))

    # read and write token usage
    def read_total_token_usage(self):
        try:
            with open(self.token_usage_file, 'r') as file:
                data = json.load(file)
                if data['date'] == datetime.datetime.utcnow().strftime('%Y-%m-%d'):
                    return int(data['usage'])  # Convert to int
                else:
                    return 0
        except (FileNotFoundError, json.JSONDecodeError):
            return 0

    def write_total_token_usage(self, usage):
        data = {
            'date': datetime.datetime.utcnow().strftime('%Y-%m-%d'),
            'usage': usage
        }
        with open(self.token_usage_file, 'w') as file:
            json.dump(data, file)

    # Function to handle start command
    async def start(self, update: Update, context: CallbackContext) -> None:
        await update.message.reply_text('Hello! I am a chatbot powered by GPT-3.5. Start chatting with me!')

    # trim the chat history to meet up with max token limits
    def trim_chat_history(self, chat_history, max_total_tokens):
        total_tokens = sum(len(message['content'].split()) for message in chat_history)
        while total_tokens > max_total_tokens and len(chat_history) > 1:
            removed_message = chat_history.pop(0)
            total_tokens -= len(removed_message['content'].split())

    # max token estimates
    def estimate_max_tokens(self, input_text, max_allowed_tokens):
        # Rough estimation of the input tokens
        input_tokens = len(input_text.split())
        max_tokens = max_allowed_tokens - input_tokens
        # Ensure max_tokens is positive and within a reasonable range
        return max(1, min(max_tokens, max_allowed_tokens))

    # Define a function to update chat history in a file
    def update_chat_history(self, chat_history):
        with open('chat_history.txt', 'a') as file:
            for message in chat_history:
                file.write(message + '\n')

    # Define a function to retrieve chat history from a file
    def retrieve_chat_history(self):
        chat_history = []
        try:
            with open('chat_history.txt', 'r') as file:
                chat_history = [line.strip() for line in file.readlines()]
        except FileNotFoundError:
            pass
        return chat_history

    # split long messages
    def split_large_messages(self, message, max_length=4096):
        return [message[i:i+max_length] for i in range(0, len(message), max_length)]

    # convert markdowns to html
    def markdown_to_html(self, text):
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
        # The regex here is looking for a standalone asterisk or underscore that could denote italics
        # It's also making sure that it doesn't capture bold syntax by checking that an asterisk or underscore is not followed or preceded by another asterisk or underscore
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
        text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', text)

        # Convert [text](url) to clickable links
        text = re.sub(r'\[(.*?)\]\((https?://\S+)\)', r'<a href="\2">\1</a>', text)

        return text

    # message handling logic
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        try:

            user_message = update.message.text
            chat_id = update.message.chat_id
            user_token_count = self.count_tokens(user_message)

            # Debug print to check types
            print(f"[Token counting/debug] user_token_count type: {type(user_token_count)}, value: {user_token_count}", flush=True)
            print(f"[Token counting/debug] self.total_token_usage type: {type(self.total_token_usage)}, value: {self.total_token_usage}", flush=True)

            # Convert max_tokens_config to an integer
            # Attempt to read max_tokens_config as an integer
            try:
                # max_tokens_config = int(self.config.get('GlobalMaxTokenUsagePerDay', '100000'))
                max_tokens_config = self.config.getint('GlobalMaxTokenUsagePerDay', 100000)
                is_no_limit = max_tokens_config == 0
                print(f"[Token counting/debug] max_tokens_config type: {type(max_tokens_config)}, value: {max_tokens_config}", flush=True)
                # Debug: Print the value read from token_usage.json
                print(f"[Debug] Total token usage from file: {self.total_token_usage}", flush=True)

            except ValueError:
                # Handle the case where the value in config.ini is not a valid integer
                self.logger.error("Invalid value for GlobalMaxTokenUsagePerDay in the configuration file.")
                await update.message.reply_text("An error occurred while processing your request: couldn't get proper token count. Please try again later.")
                # max_tokens_config = 0  # Assign a default value (0 or any other appropriate default)

            # Safely compare user_token_count and max_tokens_config
            if not is_no_limit and (self.total_token_usage + user_token_count) > max_tokens_config:
                await update.message.reply_text("The bot has reached its daily token limit. Please try again tomorrow.")
                return

            # Debug: Print before token limit checks
            print(f"[Debug] is_no_limit: {is_no_limit}, user_token_count: {user_token_count}, max_tokens_config: {max_tokens_config}", flush=True)

            # get date & time for timestamps
            now_utc = datetime.datetime.utcnow()
            utc_timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
            day_of_week = now_utc.strftime("%A")
            user_message_with_timestamp = f"[{utc_timestamp}] {user_message}"

            # Add the user's tokens to the total usage
            self.total_token_usage += user_token_count

            # Log the incoming user message
            self.logger.info(f"Received message from {update.message.from_user.username} ({chat_id}): {user_message}")

            # Log the current chat history
            self.logger.debug(f"Current chat history: {context.chat_data.get('chat_history')}")

            # Initialize chat_history as an empty list if it doesn't exist
            chat_history = context.chat_data.get('chat_history', [])

            # Append the new user message to the chat history
            chat_history.append({"role": "user", "content": user_message_with_timestamp})

            # Prepare the conversation history to send to the OpenAI API
            system_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            system_message = {"role": "system", "content": f"System time+date: {system_timestamp}, {day_of_week}): {self.system_instructions}"}

            chat_history_with_system_message = [system_message] + chat_history

            # Trim chat history if it exceeds a specified length or token limit
            self.trim_chat_history(chat_history, self.max_tokens)

            for attempt in range(self.max_retries):
                try:
                    # Prepare the payload for the API request
                    payload = {
                        "model": self.model,
                        #"messages": context.chat_data['chat_history'],
                        "messages": chat_history_with_system_message,  # Updated to include system message                
                        "temperature": self.temperature  # Use the TEMPERATURE variable loaded from config.ini
                    }

                    # Make the API request
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
                    }
                    response = httpx.post("https://api.openai.com/v1/chat/completions", 
                                        data=json.dumps(payload), 
                                        headers=headers,
                                        timeout=self.timeout)
                    response_json = response.json()

                    # Log the API request payload
                    self.logger.info(f"API Request Payload: {payload}")

                    # Extract the response and send it back to the user
                    bot_reply = response_json['choices'][0]['message']['content'].strip()

                    # Count tokens in the bot's response
                    bot_token_count = self.count_tokens(bot_reply)

                    # Add the bot's tokens to the total usage
                    self.total_token_usage += bot_token_count

                    # Update the total token usage file
                    self.write_total_token_usage(self.total_token_usage)

                    # Log the bot's response
                    self.logger.info(f"Bot's response to {update.message.from_user.username} ({chat_id}): {bot_reply}")

                    # Append the bot's response to the chat history
                    chat_history.append({"role": "assistant", "content": bot_reply})

                    # Update the chat history in context with the new messages
                    context.chat_data['chat_history'] = chat_history

                    print("Reply message before escaping:", bot_reply, flush=True)
                    # escaped_reply = escape_markdown(bot_reply, version=2)
                    # escaped_reply = escape_markdown_v2(bot_reply)
                    escaped_reply = self.markdown_to_html(bot_reply)
                    print("Reply message after escaping:", escaped_reply, flush=True)

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=escaped_reply,
                        parse_mode=ParseMode.HTML
                    )

                    break  # Break the loop if successful

                except httpx.ReadTimeout:
                    if attempt < self.max_retries - 1: # If not the last attempt
                        await asyncio.sleep(self.retry_delay) # Wait before retrying
                    else:
                        self.logger.error("Max retries reached. Giving up.")
                        await context.bot.send_message(chat_id=chat_id, text="Sorry, I'm having trouble connecting. Please try again later.")
                        break

                except httpx.TimeoutException as e:
                    self.logger.error(f"HTTP request timed out: {e}")
                    await context.bot.send_message(chat_id=chat_id, text="Sorry, the request timed out. Please try again later.")
                    # Handle timeout-specific cleanup or logic here
                except Exception as e:
                    self.logger.error(f"Error during message processing: {e}")
                    await context.bot.send_message(chat_id=chat_id, text="Sorry, there was an error processing your message.")
                    return

            # Trim chat history if it exceeds a specified length or token limit
            self.trim_chat_history(chat_history, self.max_tokens)

            # Update the chat history in context with the new messages
            context.chat_data['chat_history'] = chat_history

        except Exception as e:
            self.logger.error("Unhandled exception:", exc_info=e)
            print(f"Unhandled exception: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text("An unexpected error occurred. Please try again.")

    # Function to handle the /help command
    async def help_command(self, update: Update, context: CallbackContext) -> None:
        help_text = """
        Welcome to this OpenAI API-powered chatbot! Here are some commands you can use:

        - /start: Start a conversation with the bot.
        - /help: Display this help message.
        - /about: Learn more about this bot.
        
        Just type your message to chat with the bot!
        """
        await update.message.reply_text(help_text)

    # Function to handle the /about command
    async def about_command(self, update: Update, context: CallbackContext) -> None:
        about_text = f"""
        This is an OpenAI-powered Telegram chatbot created by FlyingFathead.
        Version: v{self.version_number}
        For more information, visit: https://github.com/FlyingFathead/TelegramBot-OpenAI-API
        """
        await update.message.reply_text(about_text)

    # Function to handle errors
    def error(self, update: Update, context: CallbackContext) -> None:
        self.logger.warning('Update "%s" caused error "%s"', update, context.error)

    def run(self):
        application = Application.builder().token(self.telegram_bot_token).build()
        application.get_updates_read_timeout = self.timeout
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Register additional command handlers
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("about", self.about_command))

        application.add_error_handler(self.error)
        application.run_polling()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()