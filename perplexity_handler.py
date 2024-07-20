# perplexity_handler.py

import logging
import json
from telegram.constants import ParseMode
from api_perplexity_search import query_perplexity, translate_response_chunked, split_message

MAX_TELEGRAM_MESSAGE_LENGTH = 4000

async def handle_query_perplexity(context, update, chat_id, function_call, user_message, bot, chat_history):
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

    if perplexity_response == "[System message: Perplexity API is currently unavailable due to server issues. Inform the user about this issue in their language.]":
        # Handle the system message for API unavailability
        logging.error("Perplexity API is down. Informing the model to notify the user.")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Perplexity API is currently unavailable due to server issues. Please try again later.",
            parse_mode=ParseMode.HTML
        )
        return True

    if perplexity_response is None:
        logging.error("No valid response from Perplexity, Perplexity response was None or empty.")
        await context.bot.send_message(
            chat_id=chat_id,
            text="No valid response from Perplexity, Perplexity response was None or empty.",
            parse_mode=ParseMode.HTML
        )
        return True

    # Flag for translation in progress
    context.user_data['active_translation'] = True

    # Translate or process the response as necessary
    bot_reply_formatted = await translate_response_chunked(bot, user_message, perplexity_response, context, update)

    # After translation or processing is completed, clear the active translation flag
    context.user_data.pop('active_translation', None)

    if isinstance(bot_reply_formatted, bool) and bot_reply_formatted:  # Check if translation function returned successfully
        return True  # Ensure function exits after handling success

    if not bot_reply_formatted or bot_reply_formatted.startswith("Error"):
        logging.error("Error processing or translating the Perplexity response.")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Error processing or translating the Perplexity response.",
            parse_mode=ParseMode.HTML
        )
        return True

    # Append the bot's reply to the chat history before sending it
    chat_history.append({"role": "assistant", "content": bot_reply_formatted})
    context.chat_data['chat_history'] = chat_history  # Update the chat data with the new history

    if len(bot_reply_formatted) > MAX_TELEGRAM_MESSAGE_LENGTH:
        # Split the message into chunks if it exceeds the maximum length
        chunks = split_message(bot_reply_formatted)

        for chunk in chunks:
            await context.bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=ParseMode.HTML
            )
            logging.info(f"Sent chunk with length: {len(chunk)}")
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=bot_reply_formatted,
            parse_mode=ParseMode.HTML
        )
        logging.info(f"Sent message with length: {len(bot_reply_formatted)}")

    logging.info("Response sent successfully, no further actions should be triggered.")
    return True
