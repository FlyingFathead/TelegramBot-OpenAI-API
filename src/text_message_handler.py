# text_message_handler.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import re
import html
import configparser
import os
import sys
import httpx
import requests
import logging
import datetime
import time
import json
import asyncio
import openai

import utils
from utils import holiday_replacements
import holidays
import pytz
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from telegram import constants
from telegram.constants import ChatAction
from telegram.error import TimedOut

# time & date handling
from timedate_handler import (
    get_ordinal_suffix,
    get_english_timestamp_str,
    get_finnish_timestamp_str
)

# reminder handling
from reminder_handler import handle_add_reminder, handle_delete_reminder, handle_edit_reminder, handle_view_reminders

# tg-bot specific stuff
from modules import markdown_to_html

# the tg-bot's API function calls
from config_paths import CONFIG_PATH
from config_paths import (
    ELASTICSEARCH_ENABLED, ELASTICSEARCH_HOST, ELASTICSEARCH_PORT,
    ELASTICSEARCH_SCHEME, ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD
)
from custom_functions import custom_functions, observe_chat
from api_get_duckduckgo_search import get_duckduckgo_search
from api_get_openrouteservice import get_route, get_directions_from_addresses, format_and_translate_directions
from api_get_openweathermap import get_weather, format_and_translate_weather, format_weather_response
from api_get_maptiler import get_coordinates_from_address, get_static_map_image
from api_get_global_time import get_global_time
from api_get_stock_prices_yfinance import get_stock_price, search_stock_symbol
from api_get_website_dump import get_website_dump
from calc_module import calculate_expression

# handlers for the custom function calls
from api_perplexity_search import query_perplexity
# from perplexity_handler import handle_query_perplexity
# from api_perplexity_search import query_perplexity, translate_response, translate_response_chunked, smart_chunk, split_message
# from api_perplexity_search import query_perplexity, smart_chunk, split_message

# url processing
from url_handler import process_url_message

# Get the 'ChatLogger' defined in main.py
logger = logging.getLogger('ChatLogger')

# Load the configuration file
config = configparser.ConfigParser()
config.read(CONFIG_PATH)
# automatic model picker
config_auto = configparser.ConfigParser()
config_auto.read(CONFIG_PATH)

# Read the holiday notification flag
enable_holiday_notification = config.getboolean('HolidaySettings', 'EnableHolidayNotification', fallback=False)

# RAG via elasticsearch
# from elasticsearch_handler import search_es_for_context
# from elasticsearch_functions import action_token_functions
# Access the Elasticsearch enabled flag
elasticsearch_enabled = config.getboolean('Elasticsearch', 'ElasticsearchEnabled', fallback=False)
ELASTICSEARCH_ENABLED = elasticsearch_enabled

if elasticsearch_enabled:
    try:
        from elasticsearch_handler import search_es_for_context
        from elasticsearch_functions import action_token_functions
        logging.info("Elasticsearch modules imported successfully.")
    except ImportError:
        logging.error("Elasticsearch is enabled in config.ini but the 'elasticsearch' module is not installed.")
        elasticsearch_enabled = False
else:
    search_es_for_context = None
    action_token_functions = {}
    logging.info("Elasticsearch is disabled in config.ini.")

# additional check for message length
MAX_TELEGRAM_MESSAGE_LENGTH = 4000

# Add extra wait time if we're in the middle of i.e. a translation process
extra_wait_time = 30  # Additional seconds to wait when in translation mode

# --- NEW: Import SQLite utilities ---
try:
    # Assuming db_utils.py is in the same src/ directory
    from db_utils import _get_daily_usage_sync, _update_daily_usage_sync, DB_PATH, DB_INITIALIZED_SUCCESSFULLY
except ImportError:
    logging.critical("Failed to import from db_utils.py! SQLite usage tracking will be disabled.")
    _get_daily_usage_sync = None
    _update_daily_usage_sync = None
    DB_PATH = None
    DB_INITIALIZED_SUCCESSFULLY = False
# --- End Import ---

# get today's usage regarding OpenAI API's responses (for auto-switching)
def get_today_usage():
    """
    Return (premium_used, mini_used) for today if DB is ready,
    or None if DB not ready or usage could not be retrieved.
    """
    if not DB_INITIALIZED_SUCCESSFULLY or not DB_PATH:
        return None  # Not ready
    usage_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    daily_usage = _get_daily_usage_sync(DB_PATH, usage_date)
    return daily_usage  # daily_usage is (premium_tokens, mini_tokens) or None

# model picker auto-switch
def pick_model_auto_switch(bot):
    if not config_auto.has_section('ModelAutoSwitch'):
        logging.info("Auto-switch is not configured. Using default model: %s", bot.model)
        return True

    if not config_auto['ModelAutoSwitch'].getboolean('Enabled', fallback=False):
        logging.info("ModelAutoSwitch.Enabled = False => skipping auto-switch, using %s", bot.model)
        return True

    premium_model = config_auto['ModelAutoSwitch'].get('PremiumModel', 'gpt-4')
    fallback_model = config_auto['ModelAutoSwitch'].get('FallbackModel', 'gpt-3.5-turbo')
    premium_limit = config_auto['ModelAutoSwitch'].getint('PremiumTokenLimit', 500000)
    fallback_limit = config_auto['ModelAutoSwitch'].getint('MiniTokenLimit', 10000000)
    fallback_action = config_auto['ModelAutoSwitch'].get('FallbackLimitAction', 'Deny')

    if not DB_INITIALIZED_SUCCESSFULLY or not DB_PATH:
        logging.warning("DB not initialized or path missing — can't auto-switch, fallback to default model.")
        return True

    usage_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    daily_usage = _get_daily_usage_sync(DB_PATH, usage_date)
    if not daily_usage:
        daily_premium_tokens, daily_fallback_tokens = (0, 0)
    else:
        daily_premium_tokens, daily_fallback_tokens = daily_usage

    # --> NOW WE CAN SAFELY LOG THE USAGE & LIMITS <--
    logging.info(f"Daily premium tokens = {daily_premium_tokens}, daily fallback tokens = {daily_fallback_tokens}")
    logging.info(f"Premium limit = {premium_limit}, Fallback limit = {fallback_limit}, fallback_action = {fallback_action}")

    # Decide if we can still use the premium model
    if daily_premium_tokens < premium_limit:
        bot.model = premium_model
        logging.info("Using premium model: %s, daily usage = %d", bot.model, daily_premium_tokens)
        return True
    else:
        # Premium limit exceeded => check fallback usage
        if daily_fallback_tokens < fallback_limit:
            bot.model = fallback_model
            logging.info("Premium limit reached; using fallback model: %s, fallback usage = %d", 
                         bot.model, daily_fallback_tokens)
            return True
        else:
            # Fallback usage also exceeded => check action
            if fallback_action.lower() == 'deny':
                logging.warning("Fallback limit also reached => Deny further usage.")
                return False
            elif fallback_action.lower() == 'warn':
                logging.warning("Fallback limit reached but ignoring => 'Warn' => proceed with fallback anyway.")
                bot.model = fallback_model
                return True
            else:
                logging.info("Fallback limit reached => 'Proceed' => continuing anyway with fallback.")
                bot.model = fallback_model
                return True

# text message handling logic
async def handle_message(bot, update: Update, context: CallbackContext, logger) -> None:

    # 1) Auto-switch first if applicable
    can_proceed = pick_model_auto_switch(bot)
    if not can_proceed:
        bot.logger.warning("Denied request because daily usage limits are exceeded for both premium & fallback.")        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, we've hit today's usage limit — cannot proceed. ☹️ Please try again tomorrow!"
        )
        return
    else:
        bot.logger.info(f"Proceeding with the request using model '{bot.model}'.")

    # Extract chat_id as soon as possible from the update object
    chat_id = update.effective_chat.id

    # Initialize a flag to indicate whether a response has been sent
    response_sent = False

    # send a "holiday message" if the bot is on a break
    if bot.is_bot_disabled:
        await context.bot.send_message(chat_id=update.message.chat_id, text=bot.bot_disabled_msg)
        return

    # Before anything else, check the global rate limit
    if bot.check_global_rate_limit():
        await context.bot.send_message(chat_id=update.message.chat_id, text="The bot is currently busy. Please try again in a minute.")
        return

    # process a text message
    try:

        # Create an Event to control the typing animation
        stop_typing_event = asyncio.Event()

        # Start the typing animation in a background task
        typing_task = asyncio.create_task(send_typing_animation(context.bot, chat_id, stop_typing_event))

        # Check if there is a transcribed text available
        if 'transcribed_text' in context.user_data:
            user_message = context.user_data['transcribed_text']
            # Clear the transcribed text after using it
            del context.user_data['transcribed_text']
        else:
            user_message = update.message.text
        
        chat_id = update.message.chat_id
        user_token_count = bot.count_tokens(user_message)

        # Debug print to check types
        bot.logger.info(f"[Token counting/debug] user_token_count type: {type(user_token_count)}, value: {user_token_count}")
        bot.logger.info(f"[Token counting/debug] bot.total_token_usage type: {type(bot.total_token_usage)}, value: {bot.total_token_usage}")

        # Convert max_tokens_config to an integer
        # Attempt to read max_tokens_config as an integer
        try:
            # max_tokens_config = int(bot.config.get('GlobalMaxTokenUsagePerDay', '100000'))
            max_tokens_config = bot.config.getint('GlobalMaxTokenUsagePerDay', 100000)
            is_no_limit = max_tokens_config == 0
            bot.logger.info(f"[Token counting/debug] max_tokens_config type: {type(max_tokens_config)}, value: {max_tokens_config}")
            # Debug: Print the value read from token_usage.json
            bot.logger.info(f"[Debug] Total token usage from file: {bot.total_token_usage}")

        except ValueError:
            # Handle the case where the value in config.ini is not a valid integer
            bot.logger.error("Invalid value for GlobalMaxTokenUsagePerDay in the configuration file.")
            await update.message.reply_text("An error occurred while processing your request: couldn't get proper token count. Please try again later.")
            # max_tokens_config = 0  # Assign a default value (0 or any other appropriate default)

        # Safely compare user_token_count and max_tokens_config
        if not is_no_limit and (bot.total_token_usage + user_token_count) > max_tokens_config:
            await update.message.reply_text("The bot has reached its daily token limit. Please try again tomorrow.")
            return

        # Debug: Print before token limit checks
        bot.logger.info(f"[Debug] is_no_limit: {is_no_limit}, user_token_count: {user_token_count}, max_tokens_config: {max_tokens_config}")

        #  ~~~~~~~~~~~~~~~
        #  Make timestamp
        #  ~~~~~~~~~~~~~~~
        now_utc = datetime.datetime.utcnow()

        # We'll keep this for session timeout comparisons
        current_time = now_utc
        day_of_week = now_utc.strftime("%A")
        system_timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

        english_line  = get_english_timestamp_str(now_utc)
        finnish_line  = get_finnish_timestamp_str(now_utc)

        # Combine them however you like, e.g.:
        # 
        #   Monday, April 9th, 2025 | Time (UTC): 12:34:56
        #   maanantai, 9. huhtikuuta 2025, klo 15:34:56 Suomen aikaa
        #
        current_timestamp_str = f"{english_line}\n{finnish_line}"

        # We'll put that into a system message
        timestamp_system_msg = {
            "role": "system",
            "content": current_timestamp_str
        }

        # Add the user's tokens to the total usage (JSON style)
        bot.total_token_usage += user_token_count

        # Log the incoming user message
        bot.logger.info(f"Received message from {update.message.from_user.username} ({chat_id}): {user_message}")

        # Check if session timeout is enabled and if session is timed out
        if bot.session_timeout_minutes > 0:
            timeout_seconds = bot.session_timeout_minutes * 60  # Convert minutes to seconds
            if 'last_message_time' in context.chat_data:
                last_message_time = context.chat_data['last_message_time']
                elapsed_time = (current_time - last_message_time).total_seconds()

                if elapsed_time > timeout_seconds:
                    # Log the length of chat history before trimming
                    chat_history_length_before = len(context.chat_data.get('chat_history', []))
                    bot.logger.info(f"Chat history length before trimming: {chat_history_length_before}")

                    # Session timeout logic
                    if bot.max_retained_messages == 0:
                        # Clear entire history
                        context.chat_data['chat_history'] = []
                        bot.logger.info(f"'MaxRetainedMessages' set to 0, cleared the entire chat history due to session timeout.")
                    else:
                        # Keep the last N messages
                        context.chat_data['chat_history'] = context.chat_data['chat_history'][-bot.max_retained_messages:]
                        bot.logger.info(f"Retained the last {bot.max_retained_messages} messages due to session timeout.")

                    # Log the length of chat history after trimming
                    chat_history_length_after = len(context.chat_data.get('chat_history', []))
                    bot.logger.info(f"Chat history length after trimming: {chat_history_length_after}")

                    bot.logger.info(f"[DebugInfo] Session timed out. Chat history updated.")
        else:
            # Log the skipping of session timeout check
            bot.logger.info(f"[DebugInfo] Session timeout check skipped as 'SessionTimeoutMinutes' is set to 0.")            

        # Update the time of the last message
        context.chat_data['last_message_time'] = current_time

        # Log the current chat history
        bot.logger.debug(f"Current chat history: {context.chat_data.get('chat_history')}")

        # Initialize chat_history as an empty list if it doesn't exist
        chat_history = context.chat_data.get('chat_history', [])

        #  ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #  Insert the new system msg
        #  ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # logger info on the appended system message
        logger.info(f"Inserting timestamp system message: {current_timestamp_str}")

        chat_history.append(timestamp_system_msg)

        # Append the new user message to the chat history
        chat_history.append({"role": "user", "content": user_message})

        # Prepare the conversation history to send to the OpenAI API

        # # // old method that included the timestamp in the original system message
        # system_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        # system_message = {"role": "system", "content": f"System time+date: {system_timestamp}, {day_of_week}): {bot.system_instructions}"}

        system_message = {"role": "system", "content": f"Instructions: {bot.system_instructions}"}

        chat_history_with_system_message = [system_message] + chat_history

        # Trim chat history if it exceeds a specified length or token limit
        bot.trim_chat_history(chat_history, bot.max_tokens)

        # Log the incoming user message
        bot.log_message('User', update.message.from_user.id, update.message.text)

        # Check if holiday notification is enabled
        if enable_holiday_notification:
            # Get the current date and time in Finland's timezone
            now = datetime.datetime.now(pytz.timezone('Europe/Helsinki'))

            # Create a holidays object for Finland
            fi_holidays = holidays.Finland()

            # Add non-official but widely celebrated holidays
            additional_holidays = {
                datetime.date(now.year, 4, 30): "[en] May Day Eve [fi] vappuaatto",                
                datetime.date(now.year, 7, 26): "[fi] ChatKeken syntymäpäivät! Ole iloinen koko päivän ajan! [en] ChatKeke's Birthday! Be cheerful the entire day!",
                datetime.date(now.year, 12, 31): "[en] New Year's Eve [fi] uudenvuodenaatto"
            }

            # Update the holidays object with the additional holidays
            fi_holidays.update(additional_holidays)

            # Check if the current date is a holiday
            if now.date() in fi_holidays:
                holiday_name = fi_holidays.get(now.date())
                finnish_name = holiday_replacements.get(holiday_name, holiday_name)
                holiday_message = f"HUOMIO: Suomessa on tänään juhlapäivä: {finnish_name}. Muista mainita juhlapyhästä käyttäjälle tervehtiessäsi (käytä suomeksi tervehtiessäsi VAIN suomenkielistä juhlapyhän nimeä) ja kysellessä kuulumisia! (esim. hyvää joulua!, hauskaa vappua!, hyvää juhannusta!, iloista uutta vuotta!, jne. \n(In English: Today is a Finnish holiday: {finnish_name}. Include that in your current understanding and mention it, especially if you're talking about anything current.)"
                chat_history_with_system_message.insert(1, {"role": "system", "content": holiday_message})


        # (old) // Show typing animation
        # await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

        # Process any YouTube URLs before the Elasticsearch RAG
        youtube_context_messages = await process_url_message(user_message)
        logger.info(f"YouTube context messages: {youtube_context_messages}")

        # # Process YouTube URLs and append data.
        # for youtube_context in youtube_context_messages:
        #     chat_history_with_system_message.append({
        #         "role": "system", 
        #         "content": youtube_context
        #     })

        for youtube_context in youtube_context_messages:
            chat_history_with_system_message.append({
                "role": "system", 
                "content": youtube_context
            })
            logger.info(f"Added YouTube context: {youtube_context}")

        # ~~~~~~~~~~~~~~~~~
        # Elasticsearch RAG
        # ~~~~~~~~~~~~~~~~~
        # es_context = await search_es_for_context(user_message)

        # Initialize chat_history_with_es_context to default value
        chat_history_with_es_context = chat_history_with_system_message

        # Assuming ELASTICSEARCH_ENABLED is true and we have fetched es_context
        if elasticsearch_enabled and search_es_for_context:
            logger.info(f"Elasticsearch is enabled, searching for context for user message: {user_message}")

            # es_context = await search_es_for_context(user_message)
            es_context = await search_es_for_context(user_message, config)            
            action_triggered = False  # Flag to check if an action was triggered based on tokens

            if es_context and es_context.strip():
                logger.info(f"Elasticsearch found additional context: {es_context}")

                # Iterate through your action tokens and check if any exist in the es_context
                for token, function in action_token_functions.items():
                    if token in es_context:
                        logger.info(f"Action token found: {token}. Executing corresponding function.")

                        # Execute the mapped function
                        chat_history_with_es_context = await function(context, update, chat_history_with_system_message)

                        action_triggered = True
                        break  # Stop checking after the first match to avoid multiple actions

                # If no action token was found, just add the Elasticsearch context to the chat history
                if not action_triggered:
                    chat_history_with_es_context = [{"role": "system", "content": "Elasticsearch RAG data: " + es_context}] + chat_history_with_system_message
            else:
                logger.info("No relevant or non-empty context found via Elasticsearch. Proceeding.")
                chat_history_with_es_context = chat_history_with_system_message
        else:
            chat_history_with_es_context = chat_history_with_system_message

        # ~~~~~~~~~~~
        # API request
        # ~~~~~~~~~~~

        for attempt in range(bot.max_retries):
            try:
                # Prepare the payload for the API request
                payload = {
                    "model": bot.model,
                    #"messages": context.chat_data['chat_history'],
                    # "messages": chat_history_with_system_message,  # Updated to include system message
                    "messages": chat_history_with_es_context,
                    "temperature": bot.temperature,  # Use the TEMPERATURE variable loaded from config.ini
                    "functions": custom_functions,
                    "function_call": 'auto'  # Allows the model to dynamically choose the function                        
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
                                                timeout=bot.timeout)

                    # Check if response status is 401 (Unauthorized)
                    if response.status_code == 401:
                        bot.logger.error("Received 401 Unauthorized: Invalid OpenAI API key. Please set up your API key correctly.")
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="😐",  # First message with just the emoji
                            parse_mode=ParseMode.HTML
                        )
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="Error: Invalid OpenAI API key. Please contact the administrator to resolve this issue.",
                            parse_mode=ParseMode.HTML
                        )
                        return  # Stop further execution in case of 401 error

                    response_json = response.json()
                    bot.logger.info("OpenAI API call succeeded, status code = %d", response.status_code)

                # ~~~~~ read the usage once we have the `response_json` ~~~~~
                if "usage" in response_json:
                    usage_obj = response_json["usage"]
                    # Log everything we got
                    bot.logger.info(f"OpenAI usage field => {usage_obj}")

                    # They typically have 'prompt_tokens', 'completion_tokens', and 'total_tokens'
                    prompt_used = usage_obj.get("prompt_tokens", 0)
                    completion_used = usage_obj.get("completion_tokens", 0)
                    total_used = usage_obj.get("total_tokens", 0)

                    bot.logger.info(f"Used {prompt_used} prompt tokens + {completion_used} completion tokens = {total_used} total tokens in this request.")

                    # Figure out if we're “premium” or “mini”
                    # (If your config has multiple fallback possibilities, do it your own way.
                    #  For simplicity, we just compare the current `bot.model` to the PremiumModel from config.)

                    premium_model_name = config_auto["ModelAutoSwitch"].get("PremiumModel", "gpt-4")
                    if bot.model == premium_model_name:
                        tier = "premium"
                        bot.logger.info(f"We're using the premium model => usage credited to 'premium_tokens'.")
                    else:
                        tier = "mini"
                        bot.logger.info(f"We're using the fallback model => usage credited to 'mini_tokens'.")

                    # Now actually log it to SQLite
                    if DB_INITIALIZED_SUCCESSFULLY and DB_PATH:
                        usage_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
                        bot.logger.info(f"Updating DB with {total_used} tokens on {usage_date} for tier='{tier}'.")
                        _update_daily_usage_sync(DB_PATH, usage_date, tier, total_used)
                    else:
                        bot.logger.warning("DB not initialized => can't store usage info in daily_usage table.")
                else:
                    bot.logger.warning("No 'usage' field found in the API response. Could not update daily usage stats.")

                # Log the API request payload
                bot.logger.info(f"API Request Payload: {payload}")

                # ~~~~~~~~~~~~~~~~~~
                # > function calling
                # ~~~~~~~~~~~~~~~~~~

                # Check for a 'function_call' in the response
                if 'function_call' in response_json['choices'][0]['message']:
                    function_call = response_json['choices'][0]['message']['function_call']
                    function_name = function_call['name']

                    # ~~~~~~~~~~~~~~~~~~~~~~
                    # Calculator Function
                    # ~~~~~~~~~~~~~~~~~~~~~~

                    # calculator module for mathematical equations
                    if function_name == 'calculate_expression':
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        expression = arguments.get('expression', '')

                        if expression:
                            try:
                                # Set a timeout of 5 seconds (adjust as needed)
                                calc_result = await asyncio.wait_for(calculate_expression(expression), timeout=5)
                                
                                if calc_result is None or calc_result.strip() == "":
                                    # Handle the case where the calculation returned None or an empty result
                                    system_message = "Calculator returned None or an empty result. Please ensure the expression is valid."
                                    bot.logger.warning(f"Calculator returned None or empty result for expression: '{expression}'")
                                else:
                                    # Proper result was returned, log and format it
                                    # calc_result = f"`{calc_result}`"  # Wrap the result in backticks for code formatting in Markdown.
                                    calc_result = f"{calc_result}"  # Wrap the result in <code> tags for HTML formatting.
                                    system_message = (
                                        f"[Calculator result, explain to the user in their language if needed. "
                                        "IMPORTANT: Do not translate or simplify the mathematical expressions themselves. "
                                        "NOTE: Telegram doesn't support LaTeX. Use simple HTML formatting, i.e. <code></code> if need be, note that <pre> or <br> are NOT allowed HTML tags. If the user explicitly asks for LaTeX or mentions LaTeX, use LaTeX formatting; "
                                        f"otherwise, use plain text or Unicode with simple HTML.] Result:\n{calc_result}\n\n"
                                        "[NOTE: format your response appropriately, possibly incorporating additional context or user intent, TRANSLATE it to the user's language if needed.]"
                                    ).format(calc_result=calc_result)  # This ensures the result is inserted correctly

                                    bot.logger.info(f"Calculation result: {calc_result}")

                            except asyncio.TimeoutError:
                                # Handle the case where the calculation took too long
                                system_message = "Calculation timed out after 5 seconds. Please try a simpler expression."
                                bot.logger.error(f"TimeoutError: Calculation for expression '{expression}' exceeded the time limit.")
                            except Exception as e:
                                # Handle other exceptions
                                system_message = f"An error occurred while evaluating the expression: {str(e)}"
                                bot.logger.error(f"Error evaluating expression '{expression}': {e}")
                        else:
                            system_message = "Please provide a valid expression for calculation."
                            bot.logger.warning("Received an empty expression for calculation.")

                        # Append the calculation result or the error message as a system message
                        chat_history.append({"role": "system", "content": system_message})
                        context.chat_data['chat_history'] = chat_history

                        # Debugging: Log the updated chat history
                        bot.logger.info(f"Updated chat history with calculator result: {chat_history}")

                        # Make an API request using the updated chat history
                        response_json = await make_api_request(bot, chat_history, bot.timeout)

                        # Extract and handle the content from the API response
                        bot_reply_content = response_json['choices'][0]['message'].get('content', '')
                        bot.logger.info(f"Bot's response content: '{bot_reply_content}'")

                        bot_reply = bot_reply_content.strip() if bot_reply_content else ""

                        # Update usage metrics and logs
                        bot_token_count = bot.count_tokens(bot_reply)
                        bot.total_token_usage += bot_token_count
                        bot.write_total_token_usage(bot.total_token_usage)
                        bot.logger.info(f"Bot's response to {update.message.from_user.username} ({chat_id}): '{bot_reply}'")

                        # Ensure the bot has a substantive response to send
                        if bot_reply:
                            # escaped_reply = markdown_to_html(bot_reply)
                            escaped_reply = bot_reply

                            # Log the bot's response
                            bot.log_message(
                                message_type='Bot',
                                message=bot_reply,
                                source='Calculator Module'
                            )

                            await context.bot.send_message(chat_id=chat_id, text=escaped_reply, parse_mode=ParseMode.HTML)
                        else:
                            # If no content to send, log and add a system message
                            bot.logger.error("Attempted to send an empty message.")
                            system_message = "Calculator returned an empty result or encountered an error, resulting in no response to send."
                            chat_history.append({"role": "system", "content": system_message})
                            context.chat_data['chat_history'] = chat_history

                            # Optionally, you can log this as a fallback
                            bot.logger.info("Added system message indicating an empty result.")

                        # Finalize the function call
                        stop_typing_event.set()
                        context.user_data.pop('active_translation', None)
                        return

                    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                    # weather via openweathermap api
                    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

                    elif function_name == 'get_weather':
                        # Fetch the weather data
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        city_name = arguments.get('city_name', 'DefaultCity')
                        country = arguments.get('country', None)  # Fetch the country parameter, defaulting to None if not provided

                        # Now pass the country parameter to your get_weather function
                        weather_info = await get_weather(city_name, country=country)  # Assuming get_weather is updated to accept country

                        # Add the received weather data as a system message
                        if weather_info:
                            system_message = f"[OpenWeatherMap API request returned data, use according to your own discernment as to what include and what format, by default, use emojis (you're in Telegram)]: {weather_info}"
                        else:
                            system_message = "[OpenWeatherMap API request failed to retrieve data]"

                        # Append the system message to the chat history
                        chat_history.append({"role": "system", "content": system_message})
                        context.chat_data['chat_history'] = chat_history

                        # Prepare the payload for the API request with updated chat history
                        payload = {
                            "model": bot.model,
                            "messages": chat_history,
                            "temperature": bot.temperature,
                            "functions": custom_functions,
                            "function_call": 'auto'  # Allows the model to dynamically choose the function
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
                                                        timeout=bot.timeout)
                            response_json = response.json()

                        # Log the API request payload
                        bot.logger.info(f"API Request Payload: {payload}")

                        # Safely get the content or default to an empty string if not found
                        bot_reply_content = response_json['choices'][0]['message'].get('content', '')

                        # Only call strip if bot_reply_content is not None
                        bot_reply = ""  # Default value if no content is found or an empty response is received
                        if bot_reply_content:
                            bot_reply = bot_reply_content.strip()

                        # Count tokens in the bot's response
                        bot_token_count = bot.count_tokens(bot_reply)

                        # Add the bot's tokens to the total usage
                        bot.total_token_usage += bot_token_count

                        # Update the total token usage file
                        bot.write_total_token_usage(bot.total_token_usage)

                        # Log the bot's response
                        bot.logger.info(f"Bot's response to {update.message.from_user.username} ({chat_id}): {bot_reply}")

                        # Append the bot's response to the chat history
                        chat_history.append({"role": "assistant", "content": bot_reply})

                        # Update the chat history in context with the new messages
                        context.chat_data['chat_history'] = chat_history

                        # View the output (i.e. for markdown etc formatting debugging)
                        logger.info(f"[Debug] Reply message before escaping: {bot_reply}")

                        # escaped_reply = markdown_to_html(bot_reply)

                        try:
                            escaped_reply = markdown_to_html(bot_reply)
                        except Exception as e:
                            bot.logger.error(f"markdown_to_html failed: {e}")
                            escaped_reply = html.escape(bot_reply)  # Safe fallback

                        # escaped_reply = bot_reply
                        logger.info(f"[Debug] Reply message after escaping: {escaped_reply}")

                        # Log the bot's response
                        bot.log_message(
                            message_type='Bot',
                            message=bot_reply,
                            source='Weather API'
                        )

                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=escaped_reply,
                            parse_mode=ParseMode.HTML
                        )

                        stop_typing_event.set()
                        context.user_data.pop('active_translation', None)

                        return  # Exit the loop after handling the custom function

                    # ~~~~~~~~~~~~~~~~~
                    # DuckDuckGo Search
                    # ~~~~~~~~~~~~~~~~~

                    elif function_name == 'get_duckduckgo_search':
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        search_query = arguments.get('search_query', '')

                        if search_query:
                            search_results = await get_duckduckgo_search(search_query, user_message)
                            if search_results:
                                system_message = f"[DuckDuckGo Search Results]: {search_results}\n\n[NOTE: format your response as Telegram-compatible HTML with links. Translate your response to the user's language if necessary (= if the user talked to you in Finnish, respond in Finnish).][Use SIMPLE, Telegram-compliant HTML: Use these HTML tags if needed: <b> for bold, <i> for italics, <u> for underline, <s> for strikethrough, <code> for inline code, <pre> for preformatted blocks, and <a href=...> for hyperlinks.. Do NOT use <pre>, <br>, <ul>, <li> or Markdown in your response!]"
                            else:
                                system_message = "No results found for your query."
                        else:
                            system_message = "Please provide a search query."

                        # Append the search results or the relevant message as a system message
                        chat_history.append({"role": "system", "content": system_message})
                        context.chat_data['chat_history'] = chat_history

                        # Debugging: Log the updated chat history
                        bot.logger.info(f"Updated chat history: {chat_history}")

                        # Make an API request using the updated chat history
                        response_json = await make_api_request(bot, chat_history, bot.timeout)

                        # Extract and handle the content from the API response
                        bot_reply_content = response_json['choices'][0]['message'].get('content', '')
                        bot.logger.info(f"Bot's response content: '{bot_reply_content}'")

                        bot_reply = bot_reply_content.strip() if bot_reply_content else ""

                        # Update usage metrics and logs
                        bot_token_count = bot.count_tokens(bot_reply)
                        bot.total_token_usage += bot_token_count
                        bot.write_total_token_usage(bot.total_token_usage)
                        bot.logger.info(f"Bot's response to {update.message.from_user.username} ({chat_id}): '{bot_reply}'")

                        # Ensure the bot has a substantive response to send
                        if bot_reply:
                            # Function to clean unsupported tags
                            # # // old method
                            # def sanitize_html(content):
                            #     # Remove unsupported HTML tags
                            #     for tag in ['<pre>', '</pre>', '<br>', '<br/>', '</br>', '<div>', '</div>', '<span>', '</span>', '<p>', '</p>']:
                            #         content = content.replace(tag, '')
                            #     # Optionally: Replace line breaks with "\n" to preserve formatting
                            #     content = content.replace('<br>', '\n').replace('<br/>', '\n')
                            #     return content

                            # Convert markdown to HTML
                            # escaped_reply = markdown_to_html(bot_reply)
                            try:
                                escaped_reply = markdown_to_html(bot_reply)
                            except Exception as e:
                                bot.logger.error(f"markdown_to_html failed: {e}")
                                escaped_reply = html.escape(bot_reply)  # Safe fallback

                            # Sanitize the HTML to remove any unsupported tags
                            escaped_reply = sanitize_html(escaped_reply)

                            # Log the bot's response from DuckDuckGo Search
                            bot.log_message(
                                message_type='Bot',
                                message=bot_reply,
                                source='DuckDuckGo Search'
                            )

                            await context.bot.send_message(chat_id=chat_id, text=escaped_reply, parse_mode=ParseMode.HTML)
                        else:
                            bot.logger.error("Attempted to send an empty message.")
                            escaped_reply = "🤔"
                            await context.bot.send_message(chat_id=chat_id, text=escaped_reply, parse_mode=ParseMode.HTML)
                            pass

                        # Finalize the function call
                        stop_typing_event.set()
                        context.user_data.pop('active_translation', None)
                        return

                    # ~~~~~~~~~~~~~~~~~~~~~~~
                    # Website quick peek dump
                    # ~~~~~~~~~~~~~~~~~~~~~~~

                    elif function_name == 'get_website_dump':
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        url = arguments.get('url', '')

                        if url:
                            webpage_content = await get_website_dump(url)
                            if webpage_content:
                                system_message = f"[Webpage Content]: {webpage_content}\n\n[NOTE: format your response as Telegram-compatible HTML with links. Do NOT use <pre> or <br> tags! Translate your response to the user's language if necessary (= if the user talked to you in Finnish, respond in Finnish).]"
                            else:
                                system_message = "No content found for the specified URL."
                        else:
                            system_message = "URL was invalid. Please provide a valid URL."

                        # Append the webpage content or the relevant message as a system message
                        chat_history.append({"role": "system", "content": system_message})
                        context.chat_data['chat_history'] = chat_history

                        # Make an API request using the updated chat history
                        response_json = await make_api_request(bot, chat_history, bot.timeout)

                        # Extract and handle the content from the API response
                        bot_reply_content = response_json['choices'][0]['message'].get('content', '')
                        bot.logger.info(f"Bot's response content: '{bot_reply_content}'")

                        bot_reply = bot_reply_content.strip() if bot_reply_content else ""

                        # Update usage metrics and logs
                        bot_token_count = bot.count_tokens(bot_reply)
                        bot.total_token_usage += bot_token_count
                        bot.write_total_token_usage(bot.total_token_usage)
                        bot.logger.info(f"Bot's response to {update.message.from_user.username} ({chat_id}): '{bot_reply}'")

                        # Ensure the bot has a substantive response to send
                        if bot_reply:
                            # Function to clean unsupported tags
                            # def sanitize_html(content):
                            #     # Remove unsupported HTML tags
                            #     for tag in ['<pre>', '</pre>', '<br>', '<br/>', '</br>', '<div>', '</div>', '<span>', '</span>', '<p>', '</p>']:
                            #         content = content.replace(tag, '')
                            #     # Optionally: Replace line breaks with "\n" to preserve formatting
                            #     content = content.replace('<br>', '\n').replace('<br/>', '\n')
                            #     return content

                            # Convert markdown to HTML
                            # escaped_reply = markdown_to_html(bot_reply)

                            try:
                                escaped_reply = markdown_to_html(bot_reply)
                            except Exception as e:
                                bot.logger.error(f"markdown_to_html failed: {e}")
                                escaped_reply = html.escape(bot_reply)  # Safe fallback

                            # Sanitize the HTML to remove any unsupported tags
                            escaped_reply = sanitize_html(escaped_reply)

                            # Log the bot's response from DuckDuckGo Search
                            bot.log_message(
                                message_type='Bot',
                                message=bot_reply,
                                source='Website Dump'
                            )

                            await context.bot.send_message(chat_id=chat_id, text=escaped_reply, parse_mode=ParseMode.HTML)
                        else:
                            bot.logger.error("Attempted to send an empty message.")
                            escaped_reply = "🤔"
                            await context.bot.send_message(chat_id=chat_id, text=escaped_reply, parse_mode=ParseMode.HTML)
                            pass

                        stop_typing_event.set()
                        context.user_data.pop('active_translation', None)
                        return

                    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                    # Alpha Vantage / Yahoo! Finance API
                    # (depending on your selection)
                    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

                    # Handling the get_stock_price function call
                    elif function_name == 'get_stock_price':
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        symbol = arguments.get('symbol', '')
                        search = arguments.get('search', '')

                        if symbol:
                            stock_data = await get_stock_price(symbol)
                        elif search:
                            symbol_info = await search_stock_symbol(search)
                            if isinstance(symbol_info, dict) and '1. symbol' in symbol_info:
                                symbol = symbol_info['1. symbol']
                                stock_data = await get_stock_price(symbol)
                            else:
                                stock_data = "Could not find a matching stock symbol."
                        else:
                            stock_data = "Please provide either a stock symbol or a search keyword."

                        # Append the stock data as a system message
                        system_message = f"[Stock Data]: {stock_data}"
                        chat_history.append({"role": "system", "content": system_message})
                        context.chat_data['chat_history'] = chat_history

                        # Make the API request using the new function
                        response_json = await make_api_request(bot, chat_history, bot.timeout)

                        # Log the API request payload
                        bot.logger.info(f"API Request Payload: {payload}")

                        # Safely get the content or default to an empty string if not found
                        bot_reply_content = response_json['choices'][0]['message'].get('content', '')

                        # Only call strip if bot_reply_content is not None
                        bot_reply = ""  # Default value if no content is found or an empty response is received
                        if bot_reply_content:
                            bot_reply = bot_reply_content.strip()

                        # Count tokens in the bot's response
                        bot_token_count = bot.count_tokens(bot_reply)

                        # Add the bot's tokens to the total usage
                        bot.total_token_usage += bot_token_count

                        # Update the total token usage file
                        bot.write_total_token_usage(bot.total_token_usage)

                        # Log the bot's response
                        bot.logger.info(f"Bot's response to {update.message.from_user.username} ({chat_id}): {bot_reply}")

                        # Append the bot's response to the chat history
                        chat_history.append({"role": "assistant", "content": bot_reply})

                        # Update the chat history in context with the new messages
                        context.chat_data['chat_history'] = chat_history

                        # View the output (i.e. for markdown etc formatting debugging)
                        logger.info(f"[Debug] Reply message before escaping: {bot_reply}")

                        # escaped_reply = markdown_to_html(bot_reply)
                        try:
                            escaped_reply = markdown_to_html(bot_reply)
                        except Exception as e:
                            bot.logger.error(f"markdown_to_html failed: {e}")
                            escaped_reply = html.escape(bot_reply)  # Safe fallback

                        logger.info(f"[Debug] Reply message after escaping: {escaped_reply}")

                        # Log the bot's response
                        bot.log_message(
                            message_type='Bot',
                            message=bot_reply,
                            source='Alpha Vantage / Yahoo! Finance'
                        )                        

                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=escaped_reply,
                            parse_mode=ParseMode.HTML
                        )

                        stop_typing_event.set()
                        context.user_data.pop('active_translation', None)

                        return  # Exit the loop after handling the custom function

                    # get the map via maptiler
                    elif function_name == 'get_map':
                        # Fetch the map data
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        address = arguments.get('address', 'DefaultLocation')
                        
                        # First, get the coordinates from the address
                        coords_info = await get_coordinates_from_address(address)
                        if isinstance(coords_info, dict):
                            latitude = coords_info['latitude']
                            longitude = coords_info['longitude']
                            
                            # Now, generate the map image with these coordinates
                            map_image_url = await get_static_map_image(latitude, longitude, zoom=12, width=400, height=300)  # Example parameters

                            # Note about the action taken
                            action_note = f"[Generated and sent the map for: {address}]"

                            # Append the note and map URL to the chat history
                            chat_history.append({"role": "assistant", "content": action_note})
                            context.chat_data['chat_history'] = chat_history

                            # Send the map URL as a reply
                            reply_message = f"Here's the map you requested: {map_image_url}"

                            # Log the bot's response
                            bot.log_message(
                                message_type='Bot',
                                message=bot_reply,
                                source='Map Retrieval'
                            )                        

                            await context.bot.send_message(chat_id=chat_id, text=reply_message, parse_mode=ParseMode.HTML)
                            return  # Exit the loop after handling the custom function

                    # get directions to an address
                    elif function_name == 'get_directions_from_addresses':
                        # Extract arguments for direction fetching
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        start_address = arguments.get('start_address')
                        end_address = arguments.get('end_address')
                        profile = arguments.get('profile', 'driving-car')  # Use a default value if not specified
                        
                        logging.info(f"Received directions request: start_address={start_address}, end_address={end_address}, profile={profile}")
                        
                        # Fetch directions based on addresses
                        directions_info = await get_directions_from_addresses(start_address, end_address, profile)
                        
                        if directions_info:
                            logging.info(f"Received directions info: {directions_info}")
                        else:
                            logging.error("Failed to fetch directions info.")
                        
                        # Format and potentially translate the directions info
                        formatted_directions_info = await format_and_translate_directions(bot, user_message, directions_info)
                        
                        if formatted_directions_info:
                            logging.info(f"Formatted directions info for reply: {formatted_directions_info}")
                        else:
                            logging.error("Failed to format directions info for reply.")
                        
                        # Note about the action taken
                        action_note = f"[Fetched and sent the following OpenRouteService directions to the user]: {formatted_directions_info}"
                        
                        # Append the note and formatted directions information to the chat history
                        chat_history.append({"role": "assistant", "content": action_note})
                        context.chat_data['chat_history'] = chat_history
                        
                        logging.info("Appended directions info to chat history and sending reply.")

                        # Log the bot's response
                        bot.log_message(
                            message_type='Bot',
                            message=bot_reply,
                            source='Get Directions'
                        )                      

                        # Send the formatted directions information as a reply                        
                        await context.bot.send_message(chat_id=chat_id, text=formatted_directions_info, parse_mode=ParseMode.HTML)

                        logging.info("Reply sent to user.")
                        
                        return  # Exit the loop after handling the custom function

                    # ~~~~~~~~~~~~~~
                    # Perplexity API
                    # ~~~~~~~~~~~~~~
                    # Handling the Perplexity API call with automatic translation

                    elif function_name == 'query_perplexity':
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        question = arguments.get('question', '')

                        if not question:
                            logging.warning("No question was provided for the Perplexity query.")
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text="No question was provided for the Perplexity query. Please provide a question.",
                                parse_mode=ParseMode.HTML
                            )
                            return True

                        # Make the asynchronous API call to query Perplexity
                        perplexity_response = await query_perplexity(context.bot, chat_id, question)

                        # Log the raw Perplexity API response for debugging
                        logging.info(f"Raw Perplexity API Response: {perplexity_response}")

                        if not perplexity_response:
                            logging.error("Perplexity API returned an invalid or empty response.")
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text="Error processing the Perplexity query. Please try again later.",
                                parse_mode=ParseMode.HTML
                            )
                            return True

                        # Add Perplexity response to chat history as a system message
                        # system_message = f"[Perplexity.ai response. Translate to the user's language if needed and use Telegram-compliant HTML in formatting. DO NOT use Markdown!]: {perplexity_response} [USE TELEGRAM HTML IN THE FORMATTING OF YOUR RESPONSE, NOT MARKDOWN, TRANSLATE TO USER'S LANGUAGE IF NEEDED.]"                        
                        system_message = (
                            f"[Perplexity.ai response]: {perplexity_response} "
                            "[Translate to the user's language if needed. "
                            "Use only Telegram-compatible HTML; keep it simple. CONVERT MARKDOWN TO HTML. NO <br> TAGS!"
                            "Overall, in HTML formatting, DO NOT USE: <ul>, <li>, <br>, <h1>, <h2>, <h3>, <h4>, <h5>, <h6>, <pre> tags. If you want to use a codeblock, use <code>]. Remember to translate to the user's language, i.e. if they're asking in Finnish instead of English, translate into Finnish!"
                        )
                        chat_history.append({"role": "system", "content": system_message})
                        context.chat_data['chat_history'] = chat_history  # Update the chat data with the new history

                        # Log the updated chat history
                        bot.logger.info(f"Updated chat history: {chat_history}")

                        # Make an API request using the updated chat history
                        response_json = await make_api_request(bot, chat_history, bot.timeout)

                        # Extract and handle the content from the API response
                        bot_reply_content = response_json['choices'][0]['message'].get('content', '')
                        bot.logger.info(f"Bot's response content: '{bot_reply_content}'")

                        bot_reply = bot_reply_content.strip() if bot_reply_content else ""
                        bot_reply = strip_disallowed_html_tags(bot_reply)

                        # Update usage metrics and logs
                        bot_token_count = bot.count_tokens(bot_reply)
                        bot.total_token_usage += bot_token_count
                        bot.write_total_token_usage(bot.total_token_usage)
                        bot.logger.info(f"Bot's response to {update.message.from_user.username} ({chat_id}): '{bot_reply}'")

                        # Ensure the bot has a substantive response to send
                        if bot_reply:
                            # escaped_reply = bot_reply
                            # escaped_reply = markdown_to_html(bot_reply)

                            try:
                                escaped_reply = markdown_to_html(bot_reply)
                            except Exception as e:
                                bot.logger.error(f"markdown_to_html failed: {e}")
                                escaped_reply = html.escape(bot_reply)  # Safe fallback

                            # Log the bot's response from Perplexity API
                            bot.log_message(
                                message_type='Bot',
                                message=bot_reply,
                                source='Perplexity API'
                            )

                            await context.bot.send_message(chat_id=chat_id, text=escaped_reply, parse_mode=ParseMode.HTML)
                        else:
                            bot.logger.error("Attempted to send an empty message.")
                            # Optional fallback message or pass
                            escaped_reply = "🤔"
                            await context.bot.send_message(chat_id=chat_id, text=escaped_reply, parse_mode=ParseMode.HTML)
                            pass

                        # Finalize the function call
                        context.user_data.pop('active_translation', None)
                        return True


                    # ~~~~~~~~~~~~~~
                    # User reminders
                    # ~~~~~~~~~~~~~~
                    # If enabled, the function calls to add, view, edit or delete user's set reminders

                    elif function_name == 'manage_reminder':
                        # (A) parse arguments
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        action = arguments.get('action')        # "add", "view", "delete", or "edit"
                        reminder_text = arguments.get('reminder_text', '')
                        due_time_utc = arguments.get('due_time_utc', '')
                        reminder_id = arguments.get('reminder_id', None)

                        # (B) check if reminders are enabled
                        enable_reminders = config.getboolean('Reminders', 'EnableReminders', fallback=False)
                        if not enable_reminders:
                            system_message = "Reminders are disabled in config. Sorry!"
                            chat_history.append({"role": "system", "content": system_message})
                            context.chat_data['chat_history'] = chat_history
                            break  # or return

                        user_id = update.effective_user.id
                        chat_id = update.effective_chat.id

                        # (C) Dispatch based on action
                        if action == 'add':
                            if not due_time_utc:
                                result_msg = "No due_time_utc provided for adding a reminder."
                            elif not reminder_text:
                                result_msg = "No reminder_text provided for adding a reminder."
                            else:
                                result_msg = await handle_add_reminder(
                                    user_id, chat_id, reminder_text, due_time_utc
                                )

                            # If it looks like success, have GPT make a nice user-facing confirmation
                            if "has been set" in result_msg:
                                # The snippet below is the new approach:
                                short_system_msg = (
                                    f"A new reminder was successfully created for <{due_time_utc}> "
                                    f"with text: '{reminder_text}'. "
                                    "Please give the user a concise, friendly confirmation message in the user's own language, "
                                    "mentioning the date/time but NOT quoting the text verbatim unless it's appropriate to do so. Notice also the time zone. "
                                    "i.e. Finland observes Eastern European Time (UTC+2) in winter and Eastern European Summer Time (UTC+3) during daylight savings. "
                                )
                                chat_history.append({"role": "system", "content": short_system_msg})
                            else:
                                # Probably an error or partial success
                                chat_history.append({"role": "system", "content": result_msg})

                        elif action == 'view':
                            raw_result = await handle_view_reminders(user_id)
                            prefix = (
                                "Here are the user's alerts. Use the user's language when replying and Telegram-compliant "
                                "HTML tags (NOTE: do NOT use <br>!!). Use simple HTML tags (NO <br>, use regular newlines instead). Do NOT use Markdown! List the reminders without their database id #'s to the user, "
                                "since the numbers are only for database reference [i.e. to delete/edit, etc]). "
                                "If the user wasn't asking about past reminders, don't list them. KÄYTÄ VASTAUKSESSA HTML:ÄÄ. ÄLÄ KÄYTÄ MARKDOWNIA.\n\n"
                            )
                            final_result = prefix + raw_result

                            # Now store that prefixed message in the chat history
                            chat_history.append({"role": "system", "content": final_result})
                            context.chat_data['chat_history'] = chat_history

                        elif action == 'delete':
                            if not reminder_id:
                                result_msg = "No reminder_id was provided for delete."
                            else:
                                result_msg = await handle_delete_reminder(user_id, reminder_id)
                            chat_history.append({"role": "system", "content": result_msg})

                        elif action == 'edit':
                            from reminder_handler import handle_edit_reminder
                            if not reminder_id:
                                result_msg = "No reminder_id was provided for edit."
                            else:
                                result_msg = await handle_edit_reminder(
                                    user_id, reminder_id, due_time_utc, reminder_text
                                )
                            chat_history.append({"role": "system", "content": result_msg})

                        else:
                            # unknown action
                            result_msg = f"Unknown 'action' for manage_reminder: {action}"
                            chat_history.append({"role": "system", "content": result_msg})

                        # (D) Re-invoke GPT to produce final user-facing text
                        context.chat_data['chat_history'] = chat_history
                        response_json = await make_api_request(bot, chat_history, bot.timeout)

                        final_reply_content = response_json['choices'][0]['message'].get('content', '')
                        final_reply = final_reply_content.strip() if final_reply_content else ""

                        if not final_reply:
                            # Provide a fallback message to avoid sending an empty string
                            final_reply = "🤔"

                        # strip <br> tags JIC
                        final_reply = re.sub(r'<br\s*/?>', '\n', final_reply, flags=re.IGNORECASE)

                        # log & send
                        bot.log_message(
                            message_type='Bot',
                            message=final_reply,
                            source='manage_reminder'
                        )

                        message_parts = split_message(final_reply, max_length=4000)

                        for part in message_parts:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=part,
                                parse_mode=ParseMode.HTML
                            )

                        # await context.bot.send_message(
                        #     chat_id=chat_id,
                        #     text=final_reply,
                        #     parse_mode=ParseMode.HTML
                        # )

                        stop_typing_event.set()
                        return

                # Extract the response and send it back to the user
                # bot_reply = response_json['choices'][0]['message']['content'].strip()

                # Safely get the content or default to an empty string if not found
                bot_reply_content = response_json['choices'][0]['message'].get('content', '')

                # Only call strip if bot_reply_content is not None

                bot_reply = ""  # Default value if no content is found or an empty response is received

                if bot_reply_content:
                    bot_reply = bot_reply_content.strip()
                    # Proceed with using bot_reply for further logic
                else:
                    logging.warn("No response added.")

                # Count tokens in the bot's response
                bot_token_count = bot.count_tokens(bot_reply)

                # Add the bot's tokens to the total usage
                bot.total_token_usage += bot_token_count

                # Update the total token usage file
                bot.write_total_token_usage(bot.total_token_usage)

                # Log the bot's response
                bot.logger.info(f"Bot's response to {update.message.from_user.username} ({chat_id}): {bot_reply}")

                # Append the bot's response to the chat history
                chat_history.append({"role": "assistant", "content": bot_reply})

                # Update the chat history in context with the new messages
                context.chat_data['chat_history'] = chat_history

                # view the output (i.e. for markdown etc formatting debugging)
                logger.info(f"[Debug] Reply message before escaping: {bot_reply}")

                # escaped_reply = markdown_to_html(bot_reply)
                try:
                    escaped_reply = markdown_to_html(bot_reply)
                except Exception as e:
                    bot.logger.error(f"markdown_to_html failed: {e}")
                    escaped_reply = html.escape(bot_reply)  # Safe fallback

                # escaped_reply = bot_reply
                logger.info(f"[Debug] Reply message after escaping: {escaped_reply}")

                # new detailed logging in v0.76
                try:
                    # 1) Attempt to read daily usage from DB:
                    usage_tuple = get_today_usage()  # returns (premium_used, mini_used) or None
                    if usage_tuple:
                        premium_used, mini_used = usage_tuple
                    else:
                        premium_used, mini_used = None, None

                    # 2) read from config.ini for limits & model
                    premium_model = config_auto["ModelAutoSwitch"].get("PremiumModel", "")
                    fallback_model = config_auto["ModelAutoSwitch"].get("FallbackModel", "")
                    premium_limit = config_auto["ModelAutoSwitch"].getint("PremiumTokenLimit", 0)
                    fallback_limit = config_auto["ModelAutoSwitch"].getint("MiniTokenLimit", 0)

                    # 3) figure out if current model is 'premium' or 'mini'
                    if bot.model == premium_model and premium_model:
                        tier_str = "premium"
                        used_so_far = premium_used if premium_used is not None else "N/A"
                        limit_str = premium_limit if premium_limit else "N/A"
                    elif bot.model == fallback_model and fallback_model:
                        tier_str = "mini"
                        used_so_far = mini_used if mini_used is not None else "N/A"
                        limit_str = fallback_limit if fallback_limit else "N/A"
                    else:
                        tier_str = "?"
                        used_so_far = "N/A"
                        limit_str = "N/A"

                    if used_so_far == "N/A" or limit_str == "N/A":
                        usage_str = "N/A"
                    else:
                        usage_str = f"{used_so_far}/{limit_str}"

                    model_info = f"model={bot.model}, tier={tier_str}, usage={usage_str}"

                except Exception as e:
                    bot.logger.warning(f"Could not build model_info: {e}")
                    # Fallback if something went wrong 
                    model_info = "model=N/A, usage=N/A"

                # pass the bot log with more info
                bot.log_message(
                    message_type='Bot',
                    user_id=update.message.from_user.id,
                    message=bot_reply,
                    model_info=model_info
                )

                # # # send the response
                # # await context.bot.send_message(
                # #     chat_id=chat_id,
                # #     text=escaped_reply,
                # #     parse_mode=ParseMode.HTML
                # # )

                escaped_reply = sanitize_html(escaped_reply)

                message_parts = split_message(escaped_reply)

                for part in message_parts:
                    await context.bot.send_message(chat_id=chat_id, text=part, parse_mode=ParseMode.HTML)                

                stop_typing_event.set()
                context.user_data.pop('active_translation', None)

                break  # Break the loop if successful

            except httpx.ReadTimeout:
                # Check if we're currently waiting on a translation to complete.
                if 'active_translation' in context.user_data and context.user_data['active_translation']:
                    logger.info("Handling timeout during active translation.")
                    if attempt < bot.max_retries - 1:
                        adjusted_retry_delay = bot.retry_delay + extra_wait_time
                        logger.info(f"Translation in progress, extending retry delay to {adjusted_retry_delay} seconds. Retrying {attempt + 1} of {bot.max_retries}.")
                        await asyncio.sleep(adjusted_retry_delay)
                    else:
                        logger.error("Max retries reached with active translation. Notifying user of the issue.")
                        # Instead of calling a separate function, directly manage the fallback response here.
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="I'm currently experiencing difficulties due to extended processing times. Let's try something else or you can try your request again later.",
                            parse_mode=ParseMode.HTML
                        )
                        stop_typing_event.set()
                        break  # Important to prevent further retries.
                else:
                    # Handle non-translation related timeouts.
                    if attempt < bot.max_retries - 1:
                        logger.info(f"Read timeout, retrying in {bot.retry_delay} seconds... (Attempt {attempt + 1} of {bot.max_retries})")
                        await asyncio.sleep(bot.retry_delay)
                    else:
                        logger.error("Max retries reached. Unable to proceed.")
                        # Directly manage the fallback response here as well.
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="I'm having trouble processing your request right now due to connectivity issues. Please try again later.",
                            parse_mode=ParseMode.HTML
                        )
                        break  # Ensure no further retries.

            except httpx.TimeoutException as e:
                bot.logger.error(f"HTTP request timed out: {e}")
                await context.bot.send_message(chat_id=chat_id, text="Sorry, the request timed out. Please try again later.")
                # Handle timeout-specific cleanup or logic here                
            except Exception as e:
                bot.logger.error(f"Error during message processing: {e}")
                # Check if the exception is related to parsing entities
                if "Can't parse entities" in str(e):
                    bot.logger.info("Detected an issue with parsing entities. Clearing chat history to prevent loops.")
                    # Clear chat history to prevent a loop
                    context.chat_data['chat_history'] = []
                    # Optionally, you could also send a message to the user to inform them of the issue and the reset
                    await context.bot.send_message(chat_id=chat_id, text="I've encountered an issue and have reset our conversation to prevent errors. Please try your request again.")
                else:
                    # Handle other exceptions normally
                    # await context.bot.send_message(chat_id=chat_id, text="Sorry, there was an error processing your message.")
                    chat_history.append({
                        "role": "system", 
                        "content": "API request threw an error, if everything seems okay, don't worry."
                    })
                    context.chat_data['chat_history'] = chat_history
                    # Do not break; allow the system to attempt to generate a response
                    await generate_response_based_on_updated_context(bot, context, chat_id)                    

                return

        # Trim chat history if it exceeds a specified length or token limit
        bot.trim_chat_history(chat_history, bot.max_tokens)

        # Update the chat history in context with the new messages
        context.chat_data['chat_history'] = chat_history

        # await bot.process_text_message(update, context)

    except Exception as e:
        # Before handling exceptions, check if a response has already been sent
        if not response_sent:
            bot.logger.error("Unhandled exception:", exc_info=e)
            print(f"Unhandled exception: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text("An unexpected error occurred. Please try again.")
            response_sent = True  # Mark response as sent to prevent further attempts

    finally:
        # Ensure the flag is always cleared after the operation
        context.user_data.pop('active_translation', None)

        # Stop the typing animation once processing is done
        if not stop_typing_event.is_set():
            stop_typing_event.set()
        await typing_task

#
# > other
#

async def send_typing_animation(bot, chat_id, stop_event: asyncio.Event):
    """Send typing action until stop_event is set."""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(5)  # Telegram's typing status lasts for a few seconds, so we repeat.
        except TimedOut:
            logging.warning(f"Timeout while sending typing action to chat {chat_id}")
            await asyncio.sleep(5)  # Continue to wait before the next typing action attempt

async def generate_response_based_on_updated_context(bot, context, chat_id):
    # logger.info("Using the `generate_response_based_on_updated_content` function")
    # This function is designed to generate a response leveraging the updated chat history,
    # which includes system messages about the encountered issues, ensuring continuity in user interaction,
    # even when previous attempts to generate responses have faced issues such as connectivity problems or API timeouts.

    try:
        # Use the 'chat_history_with_es_context' or any other relevant updated context
        # that has been prepared earlier in the code flow.
        updated_context = context.chat_data['chat_history']

        # Prepare the API request payload with the updated context.
        payload = {
            "model": bot.model,  # Model configured for the bot
            "messages": updated_context,  # Updated chat history including system messages
            "temperature": bot.temperature,  # Configured response creativity
            "max_tokens": 1024,  # Adjust based on desired response length
            # Additional parameters like 'top_p', 'frequency_penalty', etc., can be included based on requirements.
        }

        # Headers for the API request, including the authorization token.
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bot.openai_api_key}"  # Use the bot's stored OpenAI API key
        }

        # Make the asynchronous API call to generate the response based on the updated context.
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers
            )

        response_data = response.json()

        # Extract the generated response from the response data.
        generated_response = response_data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()

        # Send the generated response back to the user.
        await context.bot.send_message(
            chat_id=chat_id,
            text=generated_response,
            parse_mode=ParseMode.HTML  # Or adjust the parse mode based on the formatting of the response
        )

    except Exception as e:
        # Log the error and provide a fallback message to maintain engagement with the user.
        logging.error(f"Failed to generate a response due to: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="I encountered an issue but I'm still here. How can I assist you further?",
            parse_mode=ParseMode.HTML  # Adjust as necessary
        )

# api requests with retry
async def make_api_request_with_retry(bot, chat_history, retries=3, timeout=30):
    attempt = 0
    while attempt < retries:
        try:
            response_json = await make_api_request(bot, chat_history, timeout)
            # Check if the response content is empty or None
            bot_reply_content = response_json['choices'][0]['message'].get('content', '')
            if bot_reply_content and bot_reply_content.strip():
                return response_json
            else:
                bot.logger.warning(f"Attempt {attempt + 1}: Blank response received, retrying...")
                attempt += 1
                await asyncio.sleep(2)  # Optional: Add a slight delay between retries

        except Exception as e:
            bot.logger.error(f"Attempt {attempt + 1}: Error during API request - {str(e)}")
            attempt += 1
            await asyncio.sleep(2)  # Optional: Add a slight delay between retries

    bot.logger.error("All retry attempts failed, returning last attempt's response (if any).")
    return response_json  # Return the last response even if blank

# API request function module
async def make_api_request(bot, chat_history, timeout=30):
    # Prepare the payload for the API request with updated chat history
    payload = {
        "model": bot.model,
        "messages": chat_history,
        "temperature": bot.temperature,
        "functions": custom_functions,
        "function_call": 'auto'  # Allows the model to dynamically choose the function
    }

    # Make the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai.api_key}"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("https://api.openai.com/v1/chat/completions",
                                         data=json.dumps(payload),
                                         headers=headers,
                                         timeout=timeout)

            # Check for 401 Unauthorized error
            if response.status_code == 401:
                bot.logger.error("Received 401 Unauthorized: Invalid OpenAI API key. Please check your OpenAI API key validity!")
                raise Exception("Unauthorized - Invalid OpenAI API key. Please check your environment variables or API key configuration.")
            
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx, 5xx)
            response_json = response.json()
            return response_json

        except httpx.HTTPStatusError as e:
            bot.logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise e  # Optionally re-raise the exception or handle it gracefully

        except Exception as e:
            bot.logger.error(f"An error occurred while making the API request: {str(e)}")
            raise e

# split long messages
def split_message(message, max_length=4000):
    """
    Split a long message into multiple smaller messages.
    Args:
        message (str): The message to split.
        max_length (int): Maximum length of each part.
    Returns:
        list: A list containing message parts.
    """
    # List to store split messages
    message_parts = []

    # While there is still text to split
    while len(message) > max_length:
        # Split at the nearest period or line break before the max_length
        split_index = message.rfind('\n', 0, max_length)
        if split_index == -1:
            split_index = message.rfind('. ', 0, max_length)
            if split_index == -1:
                split_index = max_length  # Split at max length if no better point is found
        # Add the message part
        message_parts.append(message[:split_index].strip())
        # Update the remaining message
        message = message[split_index:].strip()

    # Add the last part
    if message:
        message_parts.append(message)

    return message_parts

# sanitize html
def sanitize_html(content):
    soup = BeautifulSoup(content, 'html.parser')

    # # Replace <br> with newline (or just delete them if you prefer)
    # for br in soup.find_all("br"):
    #     br.replace_with("\n")

    # Remove unsupported tags
    for tag in soup.find_all():
        if tag.name not in ['b', 'i', 'u', 's', 'a', 'code', 'pre']:
            tag.unwrap()

    # Fix improperly nested tags
    content = str(soup)
    return content

# further; strip disallowed html tags
def strip_disallowed_html_tags(text):
    """
    Replace disallowed HTML tags with safe equivalents or remove them entirely.
    Telegram's HTML parser is extremely limited.
    """
    # Replace <br> with newline
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)

    # Replace <li> with bullet point and newline
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<li>', '• ', text, flags=re.IGNORECASE)

    # Remove <ul>, </ul>, <ol>, </ol>
    text = re.sub(r'</?(ul|ol)>', '', text, flags=re.IGNORECASE)

    return text

## more

# # // (old request type)
# async def make_api_request(bot, chat_history, timeout=30):
#     # Prepare the payload for the API request with updated chat history
#     payload = {
#         "model": bot.model,
#         "messages": chat_history,
#         "temperature": bot.temperature,
#         "functions": custom_functions,
#         "function_call": 'auto'  # Allows the model to dynamically choose the function
#     }

#     # Make the API request
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {openai.api_key}"
#     }
#     async with httpx.AsyncClient() as client:
#         response = await client.post("https://api.openai.com/v1/chat/completions",
#                                     data=json.dumps(payload),
#                                     headers=headers,
#                                     timeout=timeout)
#         response_json = response.json()
#     return response_json

# # retry function
# async def retry_async(function, retries=3, delay=2, *args, **kwargs):
#     """
#     Retries a function up to a specified number of times with a delay between retries.
    
#     Args:
#         function: The async function to retry.
#         retries: Number of retry attempts.
#         delay: Delay between retries in seconds.
#         *args: Positional arguments for the function.
#         **kwargs: Keyword arguments for the function.

#     Returns:
#         The result of the function if successful, or None if all retries fail.
#     """
#     for attempt in range(retries):
#         try:
#             result = await function(*args, **kwargs)
#             if result:
#                 return result
#         except Exception as e:
#             logging.warning(f"Attempt {attempt + 1} failed: {e}")
#         time.sleep(delay)
#     logging.error(f"All {retries} retries failed for function {function.__name__}.")
#     return None

# (old version) /// typing message animation as an async module, if needed for longer wait times
# async def send_typing_animation(bot, chat_id, duration=30):
#     # Send typing action every few seconds.
#     end_time = asyncio.get_running_loop().time() + duration
#     while True:
#         await bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
#         await asyncio.sleep(5)  # Send typing action every 5 seconds
#         if asyncio.get_running_loop().time() >= end_time:
#             break

