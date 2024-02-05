# text_message_handler.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import os
import sys
import httpx
import logging
import datetime
import json
import asyncio
import openai

import utils

from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

# tg-bot specific stuff
from modules import markdown_to_html

# the tg-bot's API function calls
from custom_functions import custom_functions, observe_chat
from api_get_openweathermap import get_weather, format_and_translate_weather

# text message handling logic
async def handle_message(bot, update: Update, context: CallbackContext, logger) -> None:

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

        # get date & time for timestamps
        now_utc = datetime.datetime.utcnow()
        current_time = now_utc
        utc_timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        day_of_week = now_utc.strftime("%A")
        user_message_with_timestamp = f"[{utc_timestamp}] {user_message}"

        # Add the user's tokens to the total usage
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

        # Append the new user message to the chat history
        chat_history.append({"role": "user", "content": user_message_with_timestamp})

        # Prepare the conversation history to send to the OpenAI API
        system_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        system_message = {"role": "system", "content": f"System time+date: {system_timestamp}, {day_of_week}): {bot.system_instructions}"}

        chat_history_with_system_message = [system_message] + chat_history

        # Trim chat history if it exceeds a specified length or token limit
        bot.trim_chat_history(chat_history, bot.max_tokens)

        # Log the incoming user message
        bot.log_message('User', update.message.from_user.id, update.message.text)

        for attempt in range(bot.max_retries):
            try:
                # Prepare the payload for the API request
                payload = {
                    "model": bot.model,
                    #"messages": context.chat_data['chat_history'],
                    "messages": chat_history_with_system_message,  # Updated to include system message                
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
                    response_json = response.json()

                # Log the API request payload
                bot.logger.info(f"API Request Payload: {payload}")

                #
                # > function calling
                #

                # Check for a 'function_call' in the response
                if 'function_call' in response_json['choices'][0]['message']:
                    function_call = response_json['choices'][0]['message']['function_call']
                    function_name = function_call['name']

                    if function_name == 'get_weather':
                        # Fetch the weather data
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        city_name = arguments.get('city_name', 'DefaultCity')
                        forecast_type = arguments.get('forecast_type', 'current')
                        weather_info = await get_weather(city_name, forecast_type)

                        # Send the weather information as a reply
                        # await context.bot.send_message(chat_id=chat_id, text=weather_info)

                        # Format and potentially translate the weather info
                        formatted_weather_info = await format_and_translate_weather(bot, user_message, weather_info)

                        # Note about the action taken
                        action_note = f"[Fetched and sent the following OpenWeatherAPI weather data to the user]: {formatted_weather_info}"

                        # Append the note and formatted weather information to the chat history
                        chat_history.append({"role": "assistant", "content": action_note})
                        context.chat_data['chat_history'] = chat_history

                        # Send the formatted weather information as a reply
                        # await context.bot.send_message(chat_id=chat_id, text=formatted_weather_info)
                        await context.bot.send_message(chat_id=chat_id, text=formatted_weather_info, parse_mode=ParseMode.HTML)
                        return  # Exit the loop after handling the custom function

                # Extract the response and send it back to the user
                bot_reply = response_json['choices'][0]['message']['content'].strip()

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

                escaped_reply = markdown_to_html(bot_reply)
                logger.info(f"[Debug] Reply message after escaping: {escaped_reply}")

                # Log the bot's response
                bot.log_message('Bot', bot.telegram_bot_token, bot_reply)

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=escaped_reply,
                    parse_mode=ParseMode.HTML
                )

                break  # Break the loop if successful

            except httpx.ReadTimeout:
                if attempt < bot.max_retries - 1: # If not the last attempt
                    await asyncio.sleep(bot.retry_delay) # Wait before retrying
                else:
                    bot.logger.error("Max retries reached. Giving up.")
                    await context.bot.send_message(chat_id=chat_id, text="Sorry, I'm having trouble connecting. Please try again later.")
                    break

            except httpx.TimeoutException as e:
                bot.logger.error(f"HTTP request timed out: {e}")
                await context.bot.send_message(chat_id=chat_id, text="Sorry, the request timed out. Please try again later.")
                # Handle timeout-specific cleanup or logic here
            except Exception as e:
                bot.logger.error(f"Error during message processing: {e}")
                await context.bot.send_message(chat_id=chat_id, text="Sorry, there was an error processing your message.")
                return

        # Trim chat history if it exceeds a specified length or token limit
        bot.trim_chat_history(chat_history, bot.max_tokens)

        # Update the chat history in context with the new messages
        context.chat_data['chat_history'] = chat_history

        # await bot.process_text_message(update, context)

    except Exception as e:
        bot.logger.error("Unhandled exception:", exc_info=e)
        print(f"Unhandled exception: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text("An unexpected error occurred. Please try again.")