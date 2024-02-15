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
from telegram import constants

# tg-bot specific stuff
from modules import markdown_to_html

# the tg-bot's API function calls
from custom_functions import custom_functions, observe_chat
from api_get_openrouteservice import get_route, get_directions_from_addresses, format_and_translate_directions
from api_get_openweathermap import get_weather, format_and_translate_weather
from api_get_maptiler import get_coordinates_from_address, get_static_map_image
from api_perplexity_search import query_perplexity, translate_response, translate_response_chunked, smart_chunk

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

        # Show typing animation
        await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

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

                    # get the weather via openweathermap api
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
                        
                        # Send the formatted directions information as a reply
                        await context.bot.send_message(chat_id=chat_id, text=formatted_directions_info, parse_mode=ParseMode.HTML)
                        logging.info("Reply sent to user.")
                        
                        return  # Exit the loop after handling the custom function
       
                    # Handling the Perplexity API call with automatic translation
                    elif function_name == 'query_perplexity':
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        question = arguments.get('question', '')

                        if question:
                            logging.info(f"Querying Perplexity with question: {question}")

                            # Make the asynchronous API call to query Perplexity
                            perplexity_response = await query_perplexity(question)

                            # Log the raw Perplexity API response for debugging
                            logging.info(f"Raw Perplexity API Response: {perplexity_response}")

                            if perplexity_response:  # Ensure there's a response
                                # Assuming perplexity_response is the raw string response
                                bot_reply_content = perplexity_response.strip()

                                await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

                                # Translate or process the response as necessary
                                bot_reply_formatted = await translate_response_chunked(bot, user_message, perplexity_response, context, update)

                                if bot_reply_formatted and not bot_reply_formatted.startswith("Error"):  # Check for a valid, non-error response

                                    # Append the bot's reply to the chat history before sending it
                                    chat_history.append({"role": "assistant", "content": f"[Translated Perplexity Reply] {bot_reply_formatted}"})
                                    context.chat_data['chat_history'] = chat_history  # Update the chat data with the new history

                                    await context.bot.send_message(
                                        chat_id=update.effective_chat.id,
                                        text=bot_reply_formatted,
                                        parse_mode=ParseMode.HTML
                                    )
                                else:
                                    # Log the error and maybe send a different message or handle the error differently
                                    logging.error("Error processing or translating the Perplexity response.")
                                    await context.bot.send_message(
                                        chat_id=update.effective_chat.id,
                                        text="Sorry, I couldn't fetch an answer for that. Please try again later."
                                    )
                            else:
                                logging.error("No valid response from Perplexity.")
                                await context.bot.send_message(
                                    chat_id=update.effective_chat.id,
                                    text="Sorry, I couldn't fetch an answer for that. Please try again later."
                                )
                        else:
                            logging.warning("No question was provided for the Perplexity query.")
                            await context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text="I need a question to ask. Please try again with a question."
                            )
                        
                        return

                    #
                    # > currently unused function calls
                    #

                    """ elif function_name == 'get_local_time':
                        arguments = json.loads(function_call.get('arguments', '{}'))
                        location_name = arguments.get('location_name', '')

                        logging.info(f"Fetching local time for location: {location_name}")

                        # Assuming you have implemented this function to fetch the time
                        local_time = await get_local_time_for_location(location_name)

                        if local_time:
                            logging.info(f"Local time for {location_name}: {local_time}")
                        else:
                            logging.error(f"Failed to fetch local time for {location_name}.")

                        action_note = f"[Fetched and sent the local time for: {location_name} is {local_time}]"

                        # Append the note and local time to the chat history
                        chat_history.append({"role": "assistant", "content": action_note})
                        context.chat_data['chat_history'] = chat_history

                        # Send the local time as a reply
                        await context.bot.send_message(chat_id=chat_id, text=local_time, parse_mode=ParseMode.HTML)
                        # return  # Exit the loop after handling the custom function """

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