# Multi-API Telegram Bot (Powered by ChatKeke)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# by FlyingFathead ~*~ https://github.com/FlyingFathead
# ghostcode: ChaosWhisperer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# https://github.com/FlyingFathead/TelegramBot-OpenAI-API
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# version of this program
version_number = "0.7613"

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

# import reminder poller status
from reminder_poller import reminder_poller

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

import db_utils
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

# force our basic logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True,  # <--- THIS forcibly removes existing handlers
)

def setup_logging(chat_logging_enabled: bool):
    """
    Set up all logging (console & file handlers, chat logger, etc.) exactly once.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid double-adding a StreamHandler if it’s already there
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        console_formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Add a rotating file handler for the "main" bot log if desired
    # (If you don't want a file log, remove this block.)
    file_formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=1_048_576,  # e.g. ~1MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Optionally set up a separate "ChatLogger" if chat_logging_enabled is True
    if chat_logging_enabled:
        chat_logger = logging.getLogger('ChatLogger')
        chat_logger.setLevel(logging.INFO)
        chat_logger.propagate = False  # We do not want double logs in root if we’re writing to separate files

        # Clear existing handlers to avoid duplicates on restarts
        if chat_logger.hasHandlers():
            chat_logger.handlers.clear()

        chat_file_handler = RotatingFileHandler(
            CHAT_LOG_FILE_PATH,
            maxBytes=CHAT_LOG_MAX_SIZE,
            backupCount=5
        )
        # You can keep a simpler format if you want:
        chat_file_formatter = logging.Formatter('%(asctime)s - %(message)s')
        chat_file_handler.setFormatter(chat_file_formatter)
        chat_logger.addHandler(chat_file_handler)

        # If you also want the chat logs to appear in console, attach the same console_handler or a new one:
        # (comment out if you only want them in the file)
        chat_console_handler = logging.StreamHandler(sys.stdout)
        chat_console_handler.setLevel(logging.INFO)
        chat_console_handler.setFormatter(file_formatter)  # reuse the same format
        chat_logger.addHandler(chat_console_handler)

# Initialize the tokenizer globally
tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

class TelegramBot:
    # version of this program
    version_number = version_number

    def __init__(self):

        # Load configuration first (defines self._parser and self.config)
        self.load_config()

        # Initialize logging
        # self.initialize_logging()

        # Initialize chat logging if enabled
        # self.initialize_chat_logging()

        # REMOVED the calls to self.initialize_logging() or self.initialize_chat_logging()
        # Because we do that in main() before constructing TelegramBot.

        self.logger = logging.getLogger('TelegramBotLogger')
        self.logger.info("Initializing TelegramBot...")

        # The rest is mostly unchanged:
        self.reminders_enabled = self._parser.getboolean('Reminders', 'EnableReminders', fallback=False)
        self.logger.info(f"Reminders Enabled according to config: {self.reminders_enabled}")

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

        # Now load it from file
        self.total_token_usage = self.read_total_token_usage()
        self.logger.info(f"Token usage after reading from file: {self.total_token_usage}")

        self.max_tokens_config = self.config.getint('GlobalMaxTokenUsagePerDay', 100000)

        self.global_request_count = 0
        self.rate_limit_reset_time = datetime.datetime.now()
        self.max_global_requests_per_minute = self.config.getint('MaxGlobalRequestsPerMinute', 60)

    def load_config(self):
        # Read entire config
        self._parser = configparser.ConfigParser()
        self._parser.read(CONFIG_PATH)

        # Grab the [DEFAULT] section for core config
        self.config = self._parser['DEFAULT']

        # Basic defaults
        self.model = self.config.get('Model', 'gpt-4o-mini')
        self.temperature = self.config.getfloat('Temperature', 0.7)
        self.timeout = self.config.getfloat('Timeout', 30.0)
        self.max_tokens = self.config.getint('MaxTokens', 4096)
        self.max_retries = self.config.getint('MaxRetries', 3)
        self.retry_delay = self.config.getint('RetryDelay', 25)

        default_system_msg = self.config.get(
            'SystemInstructions',
            'You are an OpenAI API-based chatbot on Telegram.'
        )

        # # // skip current model info
        # self.system_instructions = f"[Bot's current model: {self.model}] {default_system_msg}"
        self.system_instructions = f"[Instructions] {default_system_msg}"

        self.start_command_response = self.config.get(
            'StartCommandResponse',
            'Hello! I am a chatbot powered by GPT-4o. Start chatting with me!'
        )

        self.bot_owner_id = self.config.get('BotOwnerID', '0')
        self.is_bot_disabled = self.config.getboolean('IsBotDisabled', False)
        self.bot_disabled_msg = self.config.get('BotDisabledMsg', 'The bot is currently disabled.')

        self.enable_whisper = self.config.getboolean('EnableWhisper', True)
        self.max_voice_message_length = self.config.getint('MaxDurationMinutes', 5)

        self.data_directory = self.config.get('DataDirectory', 'data')
        self.max_storage_mb = self.config.getint('MaxStorageMB', 100)

        # Example of reading more from [Reminders], if present
        self.max_alerts_per_user = self._parser.getint('Reminders', 'MaxAlertsPerUser', fallback=30)
        self.polling_interval = self._parser.getint('Reminders', 'PollingIntervalSeconds', fallback=5)

        # Build paths
        project_root = Path(__file__).resolve().parents[1]
        self.data_directory = str(project_root / self.config.get('DataDirectory', 'data'))

        # Create data directory if needed
        try:
            if not os.path.exists(self.data_directory):
                os.makedirs(self.data_directory, exist_ok=True)
                logger.info(f"Created data directory at {self.data_directory}")
        except OSError as e:
            logger.error(
                f"Failed to create data directory {self.data_directory}: {e} "
                "-- Some commands might be disabled due to this."
            )

        self.logs_directory = str(project_root / self.config.get('LogsDirectory', 'logs'))
        try:
            if not os.path.exists(self.logs_directory):
                os.makedirs(self.logs_directory, exist_ok=True)
                logger.info(f"Created logs directory at {self.logs_directory}")
        except OSError as e:
            logger.error(
                f"Failed to create logs directory {self.logs_directory}: {e} "
                "-- Some commands might be disabled due to this."
            )

        self.logfile_enabled = self.config.getboolean('LogFileEnabled', True)
        self.logfile_file = self.config.get('LogFile', 'bot.log')
        self.chat_logging_enabled = self.config.getboolean('ChatLoggingEnabled', False)
        self.chat_log_max_size = self.config.getint('ChatLogMaxSizeMB', 10) * 1024 * 1024

        self.max_history_days = self.config.getint('MaxHistoryDays', 30)
        self.chat_log_file = self.config.get('ChatLogFile', 'chat.log')

        # Session management
        self.session_timeout_minutes = self.config.getint('SessionTimeoutMinutes', 60)
        self.max_retained_messages = self.config.getint('MaxRetainedMessages', 2)

        # User commands
        self.reset_command_enabled = self.config.getboolean('ResetCommandEnabled', False)
        self.admin_only_reset = self.config.getboolean('AdminOnlyReset', True)

    def initialize_logging(self):
        # TelegramBotLogger
        telegram_logger = logging.getLogger('TelegramBotLogger')
        telegram_logger.setLevel(logging.INFO)
        telegram_logger.propagate = True # True to enable propagation, False to disable it

        # Clear existing handlers if any exist (safety measure)
        if telegram_logger.hasHandlers():
            telegram_logger.handlers.clear()

        # Common format with timestamps
        formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')

        if self.logfile_enabled:
            file_handler = RotatingFileHandler(
                LOG_FILE_PATH,
                maxBytes=1048576,
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            telegram_logger.addHandler(file_handler)

        # Console output with timestamps, at INFO level so we see everything
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        telegram_logger.addHandler(stream_handler)

        self.logger = telegram_logger # Assign self.logger here now

    def initialize_chat_logging(self):
            if self.chat_logging_enabled:
                chat_logger = logging.getLogger('ChatLogger')
                chat_logger.setLevel(logging.INFO)
                chat_logger.propagate = True # set True to keep, False to disable

                # Clear existing handlers if any exist (safety measure)
                if chat_logger.hasHandlers():
                    chat_logger.handlers.clear()

                # File Handler for ChatLogger (can keep its specific format)
                chat_file_handler = RotatingFileHandler(
                    CHAT_LOG_FILE_PATH,
                    maxBytes=CHAT_LOG_MAX_SIZE,
                    backupCount=5
                )
                chat_file_formatter = logging.Formatter('%(asctime)s - %(message)s') # Format for chat.log
                chat_file_handler.setFormatter(chat_file_formatter)
                chat_logger.addHandler(chat_file_handler)

                # --- ADD Console Handler for ChatLogger ---
                # Use the SAME formatter as the main logger's console output for consistency
                console_formatter = logging.Formatter('[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
                chat_console_handler = logging.StreamHandler(sys.stdout) # Use stdout
                chat_console_handler.setLevel(logging.INFO) # Log INFO level to console
                chat_console_handler.setFormatter(console_formatter) # Apply the consistent format
                chat_logger.addHandler(chat_console_handler)

    def check_global_rate_limit(self):
        result, self.global_request_count, self.rate_limit_reset_time = check_global_rate_limit(
            self.max_global_requests_per_minute,
            self.global_request_count,
            self.rate_limit_reset_time
        )
        return result

    def count_tokens(self, text):
        return count_tokens(text, tokenizer)

    def read_total_token_usage(self):
        return read_total_token_usage(self.token_usage_file)

    def write_total_token_usage(self, usage):
        write_total_token_usage(self.token_usage_file, usage)

    def reset_total_token_usage(self):
        self.total_token_usage = 0
        logging.info("In-memory token usage counter reset.")

    async def schedule_daily_reset(self):
        while True:
            now = datetime.datetime.utcnow()
            tomorrow = now + datetime.timedelta(days=1)
            midnight = datetime.datetime(
                year=tomorrow.year,
                month=tomorrow.month,
                day=tomorrow.day,
                hour=0, minute=0, second=1
            )
            wait_seconds = (midnight - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            reset_token_usage_at_midnight(self.token_usage_file, self.reset_total_token_usage)
            self.logger.info("Daily token usage counter reset.")

    def run_asyncio_loop(self):
        asyncio.run(self.schedule_daily_reset())

    def log_message(self, message_type, user_id=None, message='', source=None, model_info=None):
        log_message(
            message_type=message_type,
            user_id=user_id,
            message=message,
            chat_logging_enabled=self.chat_logging_enabled,
            source=source,
            model_info=model_info
        )

    def trim_chat_history(self, chat_history, max_total_tokens):
        total_tokens = sum(self.count_tokens(msg['content']) for msg in chat_history)
        while total_tokens > max_total_tokens and len(chat_history) > 1:
            removed_message = chat_history.pop(0)
            total_tokens = sum(self.count_tokens(msg['content']) for msg in chat_history)

    def estimate_max_tokens(self, input_text, max_allowed_tokens):
        input_tokens = len(input_text.split())
        max_tokens = max_allowed_tokens - input_tokens
        return max(1, min(max_tokens, max_allowed_tokens))

    def split_large_messages(self, message, max_length=4096):
        return [message[i:i+max_length] for i in range(0, len(message), max_length)]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # voice message handler - see: voice_message_handler.py
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    async def voice_message_handler(self, update: Update, context: CallbackContext) -> None:
        await handle_voice_message(
            self,
            update,
            context,
            self.data_directory,
            self.enable_whisper,
            self.max_voice_message_length,
            logger
        )

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
        application.add_handler(
            CommandHandler(
                ["about", "info"],          # <--- list of commands
                partial(bot_commands.about_command, version_number=self.version_number)
            )
        )
        
        application.add_handler(
            CommandHandler(
                "help",
                partial(
                    bot_commands.help_command,
                    reset_enabled=self.reset_command_enabled,
                    admin_only_reset=self.admin_only_reset
                )
            )
        )
        application.add_handler(
            CommandHandler(
                "start",
                partial(bot_commands.start, start_command_response=self.start_command_response)
            )
        )

        # admin-only commands
        application.add_handler(
            CommandHandler(
                "admin",
                partial(bot_commands.admin_command, bot_owner_id=self.bot_owner_id)
            )
        )
        # Uncomment as needed:
        # application.add_handler(CommandHandler("restart", partial(bot_commands.restart_command, bot_owner_id=self.bot_owner_id)))
        # application.add_handler(CommandHandler("usage", partial(bot_commands.usage_command, bot_owner_id=self.bot_owner_id, total_token_usage=self.total_token_usage, max_tokens_config=self.max_tokens_config)))
        # application.add_handler(CommandHandler("updateconfig", partial(bot_commands.update_config_command, bot_owner_id=self.bot_owner_id)))
        # application.add_handler(CommandHandler("usagechart", partial(bot_commands.usage_chart_command, bot_instance=self, token_usage_file='token_usage.json')))
        # application.add_handler(CommandHandler("usage", partial(bot_commands.usage_command, bot_instance=self)))

        application.add_handler(CommandHandler("usagechart", bot_commands.usage_chart_command))
        application.add_handler(CommandHandler("usage", bot_commands.usage_command))

        application.add_handler(
            CommandHandler(
                "reset",
                partial(
                    bot_commands.reset_command,
                    bot_owner_id=self.bot_owner_id,
                    reset_enabled=self.reset_command_enabled,
                    admin_only_reset=self.admin_only_reset
                )
            )
        )
        application.add_handler(
            CommandHandler(
                "viewconfig",
                partial(bot_commands.view_config_command, bot_owner_id=self.bot_owner_id)
            )
        )

        application.add_handler(
            CommandHandler(
                "setsystemmessage",
                partial(bot_commands.set_system_message_command, bot_instance=self)
            )
        )
        application.add_handler(
            CommandHandler(
                "resetsystemmessage",
                partial(bot_commands.reset_system_message_command, bot_instance=self)
            )
        )
        application.add_handler(
            CommandHandler(
                "resetdailytokens",
                partial(bot_commands.reset_daily_tokens_command, bot_instance=self)
            )
        )

        application.add_error_handler(self.error)

        # Start daily token usage reset in a background thread
        threading.Thread(target=self.run_asyncio_loop, daemon=True).start()

        # Get the asyncio event loop
        loop = asyncio.get_event_loop()

        # Force DB init
        if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
            db_utils._create_tables_if_not_exist(db_utils.REMINDERS_DB_PATH)

        # If reminders are enabled in config, launch reminder poller
        if self.reminders_enabled:
            loop.create_task(reminder_poller(application))
            self.logger.info("Reminder poller task scheduled.")
        else:
            self.logger.info("Reminders are disabled in config, poller not started.")

        application.run_polling()

def main():
    # 1) Read config
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    chat_logging_enabled = config['DEFAULT'].getboolean('ChatLoggingEnabled', False)

    # 2) Actually call our logging setup
    setup_logging(chat_logging_enabled=chat_logging_enabled)

    # 3) Print startup banner
    utils.print_startup_message(version_number)

    # 4) Now create & run the bot
    bot = TelegramBot()
    bot.run()

if __name__ == '__main__':
    main()