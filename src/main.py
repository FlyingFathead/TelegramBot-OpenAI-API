# Multi-API Telegram Bot (Powered by ChatKeke)
#
# by FlyingFathead ~*~ https://github.com/FlyingFathead
# ghostcode: ChaosWhisperer
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# https://github.com/FlyingFathead/TelegramBot-OpenAI-API
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# version of this program
version_number = "0.75055"

# Add the project root directory to Python's path
import sys
from pathlib import Path
# Adding the project root to the Python path to resolve imports from root level
sys.path.append(str(Path(__file__).resolve().parents[1]))

# experimental modules
import requests

# main modules
import threading
import datetime
import configparser
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from functools import partial

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

# tg-bot modules
from config_paths import (
    CONFIG_PATH, TOKEN_FILE_PATH, API_TOKEN_PATH,
    LOG_FILE_PATH, CHAT_LOG_FILE_PATH, TOKEN_USAGE_FILE_PATH, CHAT_LOG_MAX_SIZE
)
# Elasticsearch checks
from config_paths import (
    ELASTICSEARCH_ENABLED, ELASTICSEARCH_HOST, ELASTICSEARCH_PORT,
    ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD
)

from bot_token import get_bot_token
from api_key import get_api_key
import bot_commands
import utils
from modules import count_tokens, read_total_token_usage, write_total_token_usage
from modules import reset_token_usage_at_midnight
from modules import markdown_to_html, check_global_rate_limit
from modules import log_message, rotate_log_file
from text_message_handler import handle_message
from voice_message_handler import handle_voice_message
from token_usage_visualization import generate_usage_chart

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

        # Load configuration first
        self.load_config()

        # Initialize logging
        self.initialize_logging()

        # Initialize chat logging if enabled
        self.initialize_chat_logging()

        # Assign self.logger after initializing logging
        self.logger = logging.getLogger('TelegramBotLogger')

        # Set chat_log_file to CHAT_LOG_FILE_PATH
        from config_paths import CHAT_LOG_FILE_PATH
        self.chat_log_file = CHAT_LOG_FILE_PATH

        # Attempt to get bot & API tokens
        try:
            self.telegram_bot_token = get_bot_token()
            self.openai_api_key = get_api_key()  # Store the API key as an attribute
            openai.api_key = self.openai_api_key
        except FileNotFoundError as e:
            self.logger.error(f"Required configuration not found: {e}")
            sys.exit(1)

        # Explicitly set the initial token usage to 0
        self.total_token_usage = 0
        self.token_usage_file = TOKEN_USAGE_FILE_PATH

        # Log the initial token count
        self.logger.info(f"Initial token usage set to: {self.total_token_usage}")

        self.total_token_usage = self.read_total_token_usage()

        # Log the token count after reading from the file
        self.logger.info(f"Token usage after reading from file: {self.total_token_usage}")

        self.max_tokens_config = self.config.getint('GlobalMaxTokenUsagePerDay', 100000)

        self.global_request_count = 0
        self.rate_limit_reset_time = datetime.datetime.now()
        self.max_global_requests_per_minute = self.config.getint('MaxGlobalRequestsPerMinute', 60)

    def load_config(self):
        config = configparser.ConfigParser()
        # config.read('config.ini')
        config.read(CONFIG_PATH)  # Use CONFIG_PATH instead of hardcoded 'config.ini'        
        self.config = config['DEFAULT']
        self.model = self.config.get('Model', 'gpt-4o-mini')
        self.temperature = self.config.getfloat('Temperature', 0.7)
        self.timeout = self.config.getfloat('Timeout', 30.0)        
        self.max_tokens = self.config.getint('MaxTokens', 4096)
        self.max_retries = self.config.getint('MaxRetries', 3)
        self.retry_delay = self.config.getint('RetryDelay', 25)
        default_system_msg = self.config.get('SystemInstructions', 'You are an OpenAI API-based chatbot on Telegram.')
        self.system_instructions = f"[Bot's current model: {self.model}] {default_system_msg}"

        self.start_command_response = self.config.get('StartCommandResponse', 'Hello! I am a chatbot powered by GPT-4o. Start chatting with me!')

        self.bot_owner_id = self.config.get('BotOwnerID', '0')
        self.is_bot_disabled = self.config.getboolean('IsBotDisabled', False)
        self.bot_disabled_msg = self.config.get('BotDisabledMsg', 'The bot is currently disabled.')

        self.enable_whisper = self.config.getboolean('EnableWhisper', True)
        self.max_voice_message_length = self.config.getint('MaxDurationMinutes', 5)

        self.data_directory = self.config.get('DataDirectory', 'data')  # Default to 'data' if not set        
        self.max_storage_mb = self.config.getint('MaxStorageMB', 100) # Default to 100 MB if not set

        # set directories
        # Get the project root
        project_root = Path(__file__).resolve().parents[1]

        # Combine project root with the relative data directory from config
        self.data_directory = str(project_root / self.config.get('DataDirectory', 'data'))

        # Ensure the data directory exists or handle creation failure
        try:
            if not os.path.exists(self.data_directory):
                os.makedirs(self.data_directory, exist_ok=True)
                self.logger.info(f"Created data directory at {self.data_directory}")
        except OSError as e:
            self.logger.error(f"Failed to create data directory {self.data_directory}: {e} -- Some commands might be disabled due to this.")

        # set the logs directory
        self.logs_directory = str(project_root / self.config.get('LogsDirectory', 'logs'))
        
        # Ensure the logs directory exists or handle creation failure
        try:
            if not os.path.exists(self.logs_directory):
                os.makedirs(self.logs_directory, exist_ok=True)
                self.logger.info(f"Created logs directory at {self.logs_directory}")
        except OSError as e:
            self.logger.error(f"Failed to create logs directory {self.logs_directory}: {e} -- Some commands might be disabled due to this.")

        self.logfile_enabled = self.config.getboolean('LogFileEnabled', True)
        self.logfile_file = self.config.get('LogFile', 'bot.log')
        self.chat_logging_enabled = self.config.getboolean('ChatLoggingEnabled', False)
        self.chat_log_max_size = self.config.getint('ChatLogMaxSizeMB', 10) * 1024 * 1024  # Convert MB to bytes

        self.max_history_days = self.config.getint('MaxHistoryDays', 30)
        self.chat_log_file = self.config.get('ChatLogFile', 'chat.log')

        # Session management settings
        self.session_timeout_minutes = self.config.getint('SessionTimeoutMinutes', 60)  # Default to 1 minute if not set
        self.max_retained_messages = self.config.getint('MaxRetainedMessages', 2)     # Default to 0 (clear all) if not set

        # User commands
        self.reset_command_enabled = self.config.getboolean('ResetCommandEnabled', False)
        self.admin_only_reset = self.config.getboolean('AdminOnlyReset', True)

    def initialize_logging(self):
        # TelegramBotLogger
        telegram_logger = logging.getLogger('TelegramBotLogger')
        telegram_logger.setLevel(logging.INFO)
        if self.logfile_enabled:
            file_handler = RotatingFileHandler(
                LOG_FILE_PATH, maxBytes=1048576, backupCount=5  # Adjust maxBytes as needed
            )
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            telegram_logger.addHandler(file_handler)
        
        # StreamHandler for console output
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)
        stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        telegram_logger.addHandler(stream_handler)

    def initialize_chat_logging(self):
        if self.chat_logging_enabled:
            chat_logger = logging.getLogger('ChatLogger')
            chat_logger.setLevel(logging.INFO)
            chat_handler = RotatingFileHandler(
                CHAT_LOG_FILE_PATH, maxBytes=CHAT_LOG_MAX_SIZE, backupCount=5
            )
            chat_formatter = logging.Formatter('%(asctime)s - %(message)s')
            chat_handler.setFormatter(chat_formatter)
            chat_logger.addHandler(chat_handler)

    # Check and update the global rate limit.
    def check_global_rate_limit(self):
        result, self.global_request_count, self.rate_limit_reset_time = check_global_rate_limit(
            self.max_global_requests_per_minute, 
            self.global_request_count, 
            self.rate_limit_reset_time
        )
        return result

    # count token usage
    def count_tokens(self, text):
        return count_tokens(text, tokenizer)
    
    # read and write token usage
    # detect date changes and reset token counter accordingly
    def read_total_token_usage(self):
        return read_total_token_usage(self.token_usage_file)

    # write latest token count data
    def write_total_token_usage(self, usage):
        write_total_token_usage(self.token_usage_file, usage)

    # Reset the in-memory token usage counter.
    def reset_total_token_usage(self):
        self.total_token_usage = 0
        logging.info("In-memory token usage counter reset.")

    # time the daily token usage resets
    async def schedule_daily_reset(self):
        while True:
            now = datetime.datetime.utcnow()
            # Calculate time until just after midnight UTC
            tomorrow = now + datetime.timedelta(days=1)
            midnight = datetime.datetime(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day, hour=0, minute=0, second=1)
            wait_seconds = (midnight - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            # reset_token_usage_at_midnight(self.token_usage_file)
            # Pass the reset_total_token_usage method as a callback
            reset_token_usage_at_midnight(self.token_usage_file, self.reset_total_token_usage)            
            self.logger.info("Daily token usage counter reset.")

    # running an asyncio loop for this
    def run_asyncio_loop(self):
        asyncio.run(self.schedule_daily_reset())

    # logging functionality
    def log_message(self, message_type, user_id=None, message='', source=None):
        """
        Wrapper for the modules.log_message function to include source.

        Args:
            message_type (str): Type of the message ('User' or 'Bot').
            user_id (int, optional): ID of the user sending the message. Defaults to None.
            message (str, optional): The message content. Defaults to ''.
            source (str, optional): Source of the message (e.g., 'Calculator Module'). Defaults to None.
        """
        log_message(
            message_type=message_type,
            user_id=user_id,
            message=message,
            chat_logging_enabled=self.chat_logging_enabled,
            source=source
        )

    # trim the chat history to meet up with max token limits
    def trim_chat_history(self, chat_history, max_total_tokens):
        total_tokens = sum(self.count_tokens(message['content']) for message in chat_history)

        # Continue removing messages until the total token count is within the limit
        while total_tokens > max_total_tokens and len(chat_history) > 1:
            # Remove the oldest message
            removed_message = chat_history.pop(0)

            # Recalculate the total token count after removal
            total_tokens = sum(self.count_tokens(message['content']) for message in chat_history)

    # max token estimates
    def estimate_max_tokens(self, input_text, max_allowed_tokens):
        # Rough estimation of the input tokens
        input_tokens = len(input_text.split())
        max_tokens = max_allowed_tokens - input_tokens
        # Ensure max_tokens is positive and within a reasonable range
        return max(1, min(max_tokens, max_allowed_tokens))

    # split long messages
    def split_large_messages(self, message, max_length=4096):
        return [message[i:i+max_length] for i in range(0, len(message), max_length)]

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# voice message handler - see: voice_message_handler.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # voice message handling logic    
    async def voice_message_handler(self, update: Update, context: CallbackContext) -> None:
        await handle_voice_message(self, update, context, self.data_directory, self.enable_whisper, self.max_voice_message_length, logger)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# text message handler - see: text_message_handler.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        await handle_message(self, update, context, self.logger)

# ~~~~~~~~~~~~~~~~~~~~
    # Function to handle errors
    def error(self, update: Update, context: CallbackContext) -> None:
        self.logger.warning('Update "%s" caused error "%s"', update, context.error)

    def run(self):
        application = Application.builder().token(self.telegram_bot_token).build()
        application.get_updates_read_timeout = self.timeout

        # Store bot_instance in bot_data for access in handlers
        application.bot_data['bot_instance'] = self
        self.logger.info("Stored bot_instance in context.bot_data")

        # Text handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Voice handler
        application.add_handler(MessageHandler(filters.VOICE, partial(handle_voice_message, self)))
        
        # Register command handlers from bot_commands module
        # user commands
        application.add_handler(CommandHandler("about", partial(bot_commands.about_command, version_number=self.version_number)))
        # /help
        application.add_handler(CommandHandler("help", partial(bot_commands.help_command, 
                                                       reset_enabled=self.reset_command_enabled, 
                                                       admin_only_reset=self.admin_only_reset)))
        application.add_handler(CommandHandler("start", partial(bot_commands.start, start_command_response=self.start_command_response)))        
        
        # admin-only commands
        application.add_handler(CommandHandler("admin", partial(bot_commands.admin_command, bot_owner_id=self.bot_owner_id)))
        # application.add_handler(CommandHandler("restart", partial(bot_commands.restart_command, bot_owner_id=self.bot_owner_id)))        
        # application.add_handler(CommandHandler("usage", partial(bot_commands.usage_command, bot_owner_id=self.bot_owner_id, total_token_usage=self.total_token_usage, max_tokens_config=self.max_tokens_config)))
        # application.add_handler(CommandHandler("updateconfig", partial(bot_commands.update_config_command, bot_owner_id=self.bot_owner_id)))        
        # application.add_handler(CommandHandler("usagechart", partial(bot_commands.usage_chart_command, bot_instance=self, token_usage_file='token_usage.json')))
        # application.add_handler(CommandHandler("usage", partial(bot_commands.usage_command, bot_instance=self)))

        application.add_handler(CommandHandler("usagechart", bot_commands.usage_chart_command))
        application.add_handler(CommandHandler("usage", bot_commands.usage_command))

        # Register the /reset command
        application.add_handler(CommandHandler("reset", partial(bot_commands.reset_command, 
                                                        bot_owner_id=self.bot_owner_id, 
                                                        reset_enabled=self.reset_command_enabled, 
                                                        admin_only_reset=self.admin_only_reset)))
        application.add_handler(CommandHandler("viewconfig", partial(bot_commands.view_config_command, bot_owner_id=self.bot_owner_id)))

        # Register new admin commands to set or reset the system message
        application.add_handler(CommandHandler("setsystemmessage", partial(bot_commands.set_system_message_command, bot_instance=self)))
        application.add_handler(CommandHandler("resetsystemmessage", partial(bot_commands.reset_system_message_command, bot_instance=self)))

        application.add_handler(CommandHandler("resetdailytokens", partial(bot_commands.reset_daily_tokens_command, bot_instance=self)))        

        application.add_error_handler(self.error)

        # Start the asyncio loop for schedule_daily_reset in a separate thread
        threading.Thread(target=self.run_asyncio_loop, daemon=True).start()

        # Start the polling loop
        application.run_polling()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()