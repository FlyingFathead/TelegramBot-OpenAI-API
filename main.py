# Simple OpenAI API-utilizing Telegram Bot
#
# by FlyingFathead ~*~ https://github.com/FlyingFathead
# ghostcode: ChaosWhisperer
# https://github.com/FlyingFathead/TelegramBot-OpenAI-API
#
# version of this program
version_number = "0.40"

# experimental modules
import requests

# main modules
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

# tg-bot specific stuff
from bot_token import get_bot_token
from api_key import get_api_key
import bot_commands
import utils
from modules import count_tokens, read_total_token_usage, write_total_token_usage
from modules import markdown_to_html, check_global_rate_limit
from modules import log_message, rotate_log_file

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

        # Attempt to get bot & API tokens
        try:
            self.telegram_bot_token = get_bot_token()
            openai.api_key = get_api_key()
        except FileNotFoundError as e:
            self.logger.error(f"Required configuration not found: {e}")
            sys.exit(1)

        # Load configuration first
        self.load_config()

        # Initialize logging
        self.initialize_logging()

        # Initialize chat logging if enabled
        self.initialize_chat_logging()

        self.token_usage_file = 'token_usage.json'
        self.total_token_usage = self.read_total_token_usage()
        self.max_tokens_config = self.config.getint('GlobalMaxTokenUsagePerDay', 100000)

        self.global_request_count = 0
        self.rate_limit_reset_time = datetime.datetime.now()
        self.max_global_requests_per_minute = self.config.getint('MaxGlobalRequestsPerMinute', 60)

    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.config = config['DEFAULT']
        self.model = self.config.get('Model', 'gpt-3.5-turbo')
        self.temperature = self.config.getfloat('Temperature', 0.7)
        self.timeout = self.config.getfloat('Timeout', 30.0)        
        self.max_tokens = self.config.getint('MaxTokens', 4096)
        self.max_retries = self.config.getint('MaxRetries', 3)
        self.retry_delay = self.config.getint('RetryDelay', 25)
        self.system_instructions = self.config.get('SystemInstructions', 'You are an OpenAI API-based chatbot on Telegram.')
        self.start_command_response = self.config.get('StartCommandResponse', 'Hello! I am a chatbot powered by GPT-3.5. Start chatting with me!')

        self.bot_owner_id = self.config.get('BotOwnerID', '0')
        self.is_bot_disabled = self.config.getboolean('IsBotDisabled', False)
        self.bot_disabled_msg = self.config.get('BotDisabledMsg', 'The bot is currently disabled.')

        self.enable_whisper = self.config.getboolean('EnableWhisper', True)
        self.max_voice_message_length = self.config.getint('MaxDurationMinutes', 5)

        self.data_directory = self.config.get('DataDirectory', 'data')  # Default to 'data' if not set
        self.max_storage_mb = self.config.getint('MaxStorageMB', 100) # Default to 100 MB if not set

        self.logfile_enabled = self.config.getboolean('LogFileEnabled', True)
        self.logfile_file = self.config.get('LogFile', 'bot.log')
        self.chat_logging_enabled = self.config.getboolean('ChatLoggingEnabled', False)
        self.chat_log_max_size = self.config.getint('ChatLogMaxSizeMB', 10) * 1024 * 1024  # Convert MB to bytes
        self.chat_log_file = self.config.get('ChatLogFile', 'chat.log')

        # Session management settings
        self.session_timeout_minutes = self.config.getint('SessionTimeoutMinutes', 60)  # Default to 1 minute if not set
        self.max_retained_messages = self.config.getint('MaxRetainedMessages', 2)     # Default to 0 (clear all) if not set

    def initialize_logging(self):
        self.logger = logging.getLogger('TelegramBotLogger')
        self.logger.setLevel(logging.INFO)
        if self.logfile_enabled:
            file_handler = RotatingFileHandler(self.logfile_file, maxBytes=1048576, backupCount=5)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)
        stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(stream_handler)

    def initialize_chat_logging(self):
        if self.chat_logging_enabled:
            self.chat_logger = logging.getLogger('ChatLogger')
            chat_handler = RotatingFileHandler(self.chat_log_file, maxBytes=self.chat_log_max_size, backupCount=5)
            chat_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
            self.chat_logger.addHandler(chat_handler)
            self.chat_logger.setLevel(logging.INFO)

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

    # logging functionality
    def log_message(self, message_type, user_id, message):
        log_message(self.chat_log_file, self.chat_log_max_size, message_type, user_id, message, self.chat_logging_enabled)

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

# ~~~~~~~~~~~~~~~~~~~~~
# voice message handler
# ~~~~~~~~~~~~~~~~~~~~~
    # voice message handling logic    
    async def handle_voice_message(self, update: Update, context: CallbackContext) -> None:
        
        # send a "holiday message" if the bot is on a break
        if self.is_bot_disabled:
            await context.bot.send_message(chat_id=update.message.chat_id, text=self.bot_disabled_msg)
            return

        # print("Voice message received.", flush=True)  # Debug print
        logger.info("Voice message received.")  # Log the message

        if self.enable_whisper:
            await update.message.reply_text("<i>Voice message received. Transcribing...</i>", parse_mode=ParseMode.HTML)

            # Ensure the data directory exists
            if not os.path.exists(self.data_directory):
                os.makedirs(self.data_directory)

            # Retrieve the File object of the voice message
            file = await context.bot.get_file(update.message.voice.file_id)

            # Construct the URL to download the voice message
            file_url = f"{file.file_path}"

            transcription = None  # Initialize transcription

            # Download the file using requests
            async with httpx.AsyncClient() as client:
                response = await client.get(file_url)
                if response.status_code == 200:
                    voice_file_path = os.path.join(self.data_directory, f"{file.file_id}.ogg")
                    with open(voice_file_path, 'wb') as f:
                        f.write(response.content)

                    # Add a message to indicate successful download
                    logger.info(f"Voice message file downloaded successfully as: {voice_file_path}")

                    # Check the duration of the voice message
                    voice_duration = await utils.get_voice_message_duration(voice_file_path)

                    # Compare against the max allowed duration
                    if voice_duration > self.max_voice_message_length:
                        await update.message.reply_text("Your voice message is too long. Please keep it under {} minutes.".format(self.max_voice_message_length))
                        logger.info(f"Voice file rejected for being too long: {voice_file_path}")
                        return

                    # Process the voice message with WhisperAPI
                    transcription = await self.process_voice_message(voice_file_path)

                    # Add a flushing statement to check the transcription
                    logger.info(f"Transcription: {transcription}")

                if transcription:
                    
                    # Remove HTML bold tags for processing
                    transcription_for_model = transcription.replace("<b>", "[Whisper STT Transcribed Voice Message] ").replace("</b>", " [End]")
                    
                    # Store the cleaned transcription in `context.user_data` for further processing
                    context.user_data['transcribed_text'] = transcription_for_model

                    # Log the transcription
                    self.log_message('Transcription', update.message.from_user.id, transcription_for_model)

                    # Send the transcription back to the user as is (with HTML tags for formatting)
                    await update.message.reply_text(transcription, parse_mode=ParseMode.HTML)

                    # Now pass the cleaned transcription to the handle_message method
                    # which will then use it as part of the conversation with the model
                    await self.handle_message(update, context)

                else:
                    # await update.message.reply_text("Voice message transcription failed.")
                    # If transcription fails or is unavailable
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="Voice message transcription failed.")                
        else:
            # If Whisper API is disabled, send a different response or handle accordingly
            await update.message.reply_text("Voice message transcription is currently disabled.")

    # the logic to interact with WhisperAPI here
    async def process_voice_message(self, file_path: str) -> str:
        if self.enable_whisper:
            try:
                # Whisper API ...
                with open(file_path, "rb") as audio_file:
                    
                    # print out some debugging
                    logger.info(f"Audio file being sent to OpenAI: {audio_file}")

                    transcript_response = await openai.AsyncOpenAI().audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-1",
                        response_format="json"
                    )
                    # Accessing the transcription text directly
                    # return transcript_response['text'] if 'text' in transcript_response else 'No transcription available.'
                    # Accessing the transcription text directly

                    logger.info(f"Transcription Response: {transcript_response}")

                    transcription_text = transcript_response.text.strip() if hasattr(transcript_response, 'text') else None

                    if transcription_text:
                        # Add the emojis as Unicode characters to the transcription
                        transcription_with_emoji = "🎤📝\n<b>" + transcription_text + "</b>"

                        return transcription_with_emoji
                    else:
                        return 'No transcription available.'

            except FileNotFoundError as e:
                self.logger.error(f"File not found: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                return 'An unexpected error occurred during transcription.'

# ~~~~~~~~~~~~~~~~~~~~
# text message handler
# ~~~~~~~~~~~~~~~~~~~~
    # text message handling logic
    async def handle_message(self, update: Update, context: CallbackContext) -> None:

        # send a "holiday message" if the bot is on a break
        if self.is_bot_disabled:
            await context.bot.send_message(chat_id=update.message.chat_id, text=self.bot_disabled_msg)
            return

        # Before anything else, check the global rate limit
        if self.check_global_rate_limit():
            await context.bot.send_message(chat_id=update.message.chat_id, text="The bot is currently busy. Please try again in a minute.")
            return
     
        # process a text message
        try:

            # Check if there is a transcribed text available
            if 'transcribed_text' in context.user_data:
                user_message = context.user_data['transcribed_text']
                # Clear the transcribed text after using it
                del context.user_data['transcribed_text']
            else:
                user_message = update.message.text
            
            chat_id = update.message.chat_id
            user_token_count = self.count_tokens(user_message)

            # Debug print to check types
            self.logger.info(f"[Token counting/debug] user_token_count type: {type(user_token_count)}, value: {user_token_count}")
            self.logger.info(f"[Token counting/debug] self.total_token_usage type: {type(self.total_token_usage)}, value: {self.total_token_usage}")

            # Convert max_tokens_config to an integer
            # Attempt to read max_tokens_config as an integer
            try:
                # max_tokens_config = int(self.config.get('GlobalMaxTokenUsagePerDay', '100000'))
                max_tokens_config = self.config.getint('GlobalMaxTokenUsagePerDay', 100000)
                is_no_limit = max_tokens_config == 0
                self.logger.info(f"[Token counting/debug] max_tokens_config type: {type(max_tokens_config)}, value: {max_tokens_config}")
                # Debug: Print the value read from token_usage.json
                self.logger.info(f"[Debug] Total token usage from file: {self.total_token_usage}")

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
            self.logger.info(f"[Debug] is_no_limit: {is_no_limit}, user_token_count: {user_token_count}, max_tokens_config: {max_tokens_config}")

            # get date & time for timestamps
            now_utc = datetime.datetime.utcnow()
            current_time = now_utc
            utc_timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
            day_of_week = now_utc.strftime("%A")
            user_message_with_timestamp = f"[{utc_timestamp}] {user_message}"

            # Add the user's tokens to the total usage
            self.total_token_usage += user_token_count

            # Log the incoming user message
            self.logger.info(f"Received message from {update.message.from_user.username} ({chat_id}): {user_message}")

            # Check if session timeout is enabled and if session is timed out
            if self.session_timeout_minutes > 0:
                timeout_seconds = self.session_timeout_minutes * 60  # Convert minutes to seconds
                if 'last_message_time' in context.chat_data:
                    last_message_time = context.chat_data['last_message_time']
                    elapsed_time = (current_time - last_message_time).total_seconds()

                    if elapsed_time > timeout_seconds:
                        # Log the length of chat history before trimming
                        chat_history_length_before = len(context.chat_data.get('chat_history', []))
                        self.logger.info(f"Chat history length before trimming: {chat_history_length_before}")

                        # Session timeout logic
                        if self.max_retained_messages == 0:
                            # Clear entire history
                            context.chat_data['chat_history'] = []
                            self.logger.info(f"'MaxRetainedMessages' set to 0, cleared the entire chat history due to session timeout.")
                        else:
                            # Keep the last N messages
                            context.chat_data['chat_history'] = context.chat_data['chat_history'][-self.max_retained_messages:]
                            self.logger.info(f"Retained the last {self.max_retained_messages} messages due to session timeout.")

                        # Log the length of chat history after trimming
                        chat_history_length_after = len(context.chat_data.get('chat_history', []))
                        self.logger.info(f"Chat history length after trimming: {chat_history_length_after}")

                        self.logger.info(f"[DebugInfo] Session timed out. Chat history updated.")
            else:
                # Log the skipping of session timeout check
                self.logger.info(f"[DebugInfo] Session timeout check skipped as 'SessionTimeoutMinutes' is set to 0.")            

            # Update the time of the last message
            context.chat_data['last_message_time'] = current_time

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

            # Log the incoming user message
            self.log_message('User', update.message.from_user.id, update.message.text)

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
                        "Authorization": f"Bearer {openai.api_key}"
                    }
                    async with httpx.AsyncClient() as client:
                        response = await client.post("https://api.openai.com/v1/chat/completions",
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

                    # view the output (i.e. for markdown etc formatting debugging)
                    logger.info(f"[Debug] Reply message before escaping: {bot_reply}")

                    escaped_reply = markdown_to_html(bot_reply)
                    logger.info(f"[Debug] Reply message after escaping: {escaped_reply}")

                    # Log the bot's response
                    self.log_message('Bot', self.telegram_bot_token, bot_reply)

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

            # await self.process_text_message(update, context)

        except Exception as e:
            self.logger.error("Unhandled exception:", exc_info=e)
            print(f"Unhandled exception: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text("An unexpected error occurred. Please try again.")

    # Function to handle errors
    def error(self, update: Update, context: CallbackContext) -> None:
        self.logger.warning('Update "%s" caused error "%s"', update, context.error)

    def run(self):
        application = Application.builder().token(self.telegram_bot_token).build()
        application.get_updates_read_timeout = self.timeout
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)) # Text handler
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))  # Voice handler

        # Register command handlers from bot_commands module
        # user commands
        application.add_handler(CommandHandler("about", partial(bot_commands.about_command, version_number=self.version_number)))
        application.add_handler(CommandHandler("help", bot_commands.help_command))
        application.add_handler(CommandHandler("start", partial(bot_commands.start, start_command_response=self.start_command_response)))        
        
        # admin-only commands
        application.add_handler(CommandHandler("admin", partial(bot_commands.admin_command, bot_owner_id=self.bot_owner_id)))
        # application.add_handler(CommandHandler("restart", partial(bot_commands.restart_command, bot_owner_id=self.bot_owner_id)))        
        # application.add_handler(CommandHandler("usage", partial(bot_commands.usage_command, bot_owner_id=self.bot_owner_id, total_token_usage=self.total_token_usage, max_tokens_config=self.max_tokens_config)))
        # application.add_handler(CommandHandler("updateconfig", partial(bot_commands.update_config_command, bot_owner_id=self.bot_owner_id)))        
        application.add_handler(CommandHandler("usage", partial(bot_commands.usage_command, 
                                                        bot_owner_id=self.bot_owner_id, 
                                                        token_usage_file=self.token_usage_file, 
                                                        max_tokens_config=self.max_tokens_config)))
        
        application.add_handler(CommandHandler("viewconfig", partial(bot_commands.view_config_command, bot_owner_id=self.bot_owner_id)))

        application.add_error_handler(self.error)
        application.run_polling()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()