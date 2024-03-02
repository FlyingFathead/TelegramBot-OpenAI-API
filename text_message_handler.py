# text_message_handler.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import configparser
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
from telegram.constants import ChatAction

# tg-bot specific stuff
from modules import markdown_to_html

# the tg-bot's API function calls
from custom_functions import custom_functions, observe_chat
from api_get_openrouteservice import get_route, get_directions_from_addresses, format_and_translate_directions
from api_get_openweathermap import get_weather, format_and_translate_weather, format_weather_response
from api_get_maptiler import get_coordinates_from_address, get_static_map_image
from api_perplexity_search import query_perplexity, translate_response, translate_response_chunked, smart_chunk

# RAG via elasticsearch
from elasticsearch_handler import search_es_for_context
from elasticsearch_functions import action_token_functions

# Load the configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# Access the Elasticsearch enabled flag
elasticsearch_enabled = config.getboolean('Elasticsearch', 'ElasticsearchEnabled', fallback=False)
ELASTICSEARCH_ENABLED = elasticsearch_enabled

# Add extra wait time if we're in the middle of i.e. a translation process
extra_wait_time = 30  # Additional seconds to wait when in translation mode

# text message handling logic
async def handle_message(bot, update: Update, context: CallbackContext, logger) -> None:

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

        # get date & time for timestamps
        now_utc = datetime.datetime.utcnow()
        current_time = now_utc
        # utc_timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # display abbreviated 
        utc_timestamp = now_utc.strftime("%Y-%m-%d %H:%M:%S %a UTC")

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

        # (old) // Show typing animation
        # await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

        # ~~~~~~~~~~~~~~~~~
        # Elasticsearch RAG
        # ~~~~~~~~~~~~~~~~~
        # es_context = await search_es_for_context(user_message)

        # Initialize chat_history_with_es_context to default value
        chat_history_with_es_context = chat_history_with_system_message

        # Assuming ELASTICSEARCH_ENABLED is true and we have fetched es_context
        if ELASTICSEARCH_ENABLED:
            logger.info(f"Elasticsearch is enabled, searching for context for user message: {user_message}")

            es_context = await search_es_for_context(user_message)
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
                        # chat_history_with_es_context = integrate_data_into_context(data, chat_history_with_system_message)
                        break  # Stop checking after the first match to avoid multiple actions

                # If no action token was found, just add the Elasticsearch context to the chat history
                if not action_triggered:
                    chat_history_with_es_context = [{"role": "system", "content": "Elasticsearch RAG data: " + es_context}] + chat_history_with_system_message
            else:
                logger.info("No relevant or non-empty context found via Elasticsearch. Proceeding.")
                chat_history_with_es_context = chat_history_with_system_message
        else:
            chat_history_with_es_context = chat_history_with_system_message

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
                        country = arguments.get('country', None)  # Fetch the country parameter, defaulting to None if not provided

                        # Now pass the country parameter to your get_weather function
                        weather_info = await get_weather(city_name, forecast_type, country=country)  # Assuming get_weather is updated to accept country

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
                            perplexity_response = await query_perplexity(context.bot, chat_id, question)

                            # Log the raw Perplexity API response for debugging
                            logging.info(f"Raw Perplexity API Response: {perplexity_response}")

                            if perplexity_response is not None:  # Ensure there's a response
                                # Flag for translation in progress
                                context.user_data['active_translation'] = True

                                # Translate or process the response as necessary
                                bot_reply_formatted = await translate_response_chunked(bot, user_message, perplexity_response, context, update)

                                # After translation or processing is completed, clear the active translation flag
                                context.user_data.pop('active_translation', None)                                

                                if bot_reply_formatted and not bot_reply_formatted.startswith("Error"):  # Check for a valid, non-error response

                                    # Append the bot's reply to the chat history before sending it 
                                    # chat_history.append({"role": "assistant", "content": f"[Fetched data from perplexity.ai API]"})
                                    chat_history.append({"role": "assistant", "content": bot_reply_formatted})
                                    context.chat_data['chat_history'] = chat_history  # Update the chat data with the new history

                                    await context.bot.send_message(
                                        chat_id=update.effective_chat.id,
                                        text=bot_reply_formatted,
                                        # parse_mode=ParseMode.HTML
                                        parse_mode=ParseMode.HTML
                                    )

                                    response_sent = True  # Indicate that a response has been sent
                                    break  # Exit the loop since response has been handled

                                else:
                                    # Log the error and maybe send a different message or handle the error differently
                                    logging.error("Error processing or translating the Perplexity response.")
                                    
                                    # Append a system message noting the fallback due to processing error
                                    chat_history.append({"role": "system", "content": "Fallback to base model due to processing error in Perplexity response."})
                        
                                    # "ungraceful exit"
                                    """ await context.bot.send_message(
                                        chat_id=update.effective_chat.id,
                                        text="Sorry, I couldn't fetch an answer for that. Please try again later."
                                    ) """
                            else:
                                logging.error("No valid response from Perplexity, Perplexity response was None or empty.")

                                # Append a system message noting the fallback due to invalid response
                                chat_history.append({"role": "system", "content": "Fallback to base model due to invalid Perplexity response."})

                                # "ungraceful exit"
                                """ await context.bot.send_message(
                                    chat_id=update.effective_chat.id,
                                    text="Sorry, I couldn't fetch an answer for that. Please try again later."
                                ) """

                        else:
                            logging.warning("No question was provided for the Perplexity query.")
                            """ await context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text="I need a question to ask. Please try again with a question."
                            ) """

                            chat_history.append({"role": "system", "content": "No question was provided for the Perplexity query. A question is needed to proceed."})
                            
                        # Update the chat history in context with the new system message
                        context.chat_data['chat_history'] = chat_history

                        # originally we just hit a return value                            
                        # return

## ~~~~~~~~~~~~~~ others ~~~~~~~~~~~~~~~

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

                escaped_reply = markdown_to_html(bot_reply)
                logger.info(f"[Debug] Reply message after escaping: {escaped_reply}")

                # Log the bot's response
                bot.log_message('Bot', bot.telegram_bot_token, bot_reply)

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=escaped_reply,
                    parse_mode=ParseMode.HTML
                )

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
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(5)  # Telegram's typing status lasts for a few seconds, so we repeat.

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

# (old version) /// typing message animation as an async module, if needed for longer wait times
""" async def send_typing_animation(bot, chat_id, duration=30):
    # Send typing action every few seconds.
    end_time = asyncio.get_running_loop().time() + duration
    while True:
        await bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
        await asyncio.sleep(5)  # Send typing action every 5 seconds
        if asyncio.get_running_loop().time() >= end_time:
            break
 """