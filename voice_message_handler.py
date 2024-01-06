# voice_message_handler.py
# ~~~~~~~~~~~~~~~~~~~~~
# voice message handler
# ~~~~~~~~~~~~~~~~~~~~~
import os
import sys
import httpx
import logging
import datetime
import json
import asyncio
import openai
# tg modules
from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
# tg-bot stuff
import utils

# voice message handling logic    
# async def handle_voice_message(bot, update: Update, context: CallbackContext, data_directory, enable_whisper, max_voice_message_length, logger) -> None:
async def handle_voice_message(bot, update: Update, context: CallbackContext):
    
    # send a "holiday message" if the bot is on a break
    if bot.is_bot_disabled:
        await context.bot.send_message(chat_id=update.message.chat_id, text=bot.bot_disabled_msg)
        return

    # print("Voice message received.", flush=True)  # Debug print
    bot.logger.info("Voice message received.")  # Log the message

    if bot.enable_whisper:
        await update.message.reply_text("<i>Voice message received. Transcribing...</i>", parse_mode=ParseMode.HTML)

        # Ensure the data directory exists
        if not os.path.exists(bot.data_directory):
            os.makedirs(bot.data_directory)

        # Retrieve the File object of the voice message
        file = await context.bot.get_file(update.message.voice.file_id)

        # Construct the URL to download the voice message
        file_url = f"{file.file_path}"

        transcription = None  # Initialize transcription

        # Download the file using requests
        async with httpx.AsyncClient() as client:
            response = await client.get(file_url)
            if response.status_code == 200:
                voice_file_path = os.path.join(bot.data_directory, f"{file.file_id}.ogg")
                with open(voice_file_path, 'wb') as f:
                    f.write(response.content)

                # Add a message to indicate successful download
                bot.logger.info(f"Voice message file downloaded successfully as: {voice_file_path}")

                # Check the duration of the voice message
                voice_duration = await utils.get_voice_message_duration(voice_file_path)

                # Compare against the max allowed duration
                if voice_duration > bot.max_voice_message_length:
                    await update.message.reply_text("Your voice message is too long. Please keep it under {} minutes.".format(bot.max_voice_message_length))
                    bot.logger.info(f"Voice file rejected for being too long: {voice_file_path}")
                    return

                # Process the voice message with WhisperAPI
                transcription = await process_voice_message(voice_file_path, bot.enable_whisper, bot.logger)

                # Add a flushing statement to check the transcription
                bot.logger.info(f"Transcription: {transcription}")

            if transcription:
                
                # Remove HTML bold tags for processing
                transcription_for_model = transcription.replace("<b>", "[Whisper STT transcribed message from the user] ").replace("</b>", " [end]")
                
                # Store the cleaned transcription in `context.user_data` for further processing
                context.user_data['transcribed_text'] = transcription_for_model

                # Log the transcription
                bot.log_message('Transcription', update.message.from_user.id, transcription_for_model)

                # Send the transcription back to the user as is (with HTML tags for formatting)
                await update.message.reply_text(transcription, parse_mode=ParseMode.HTML)

                # Now pass the cleaned transcription to the handle_message method
                # which will then use it as part of the conversation with the model
                await bot.handle_message(update, context)

            else:
                # await update.message.reply_text("Voice message transcription failed.")
                # If transcription fails or is unavailable
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Voice message transcription failed.")                
    else:
        # If Whisper API is disabled, send a different response or handle accordingly
        await update.message.reply_text("Voice message transcription is currently disabled.")

# the logic to interact with WhisperAPI here
async def process_voice_message(file_path: str, enable_whisper, logger):
    if enable_whisper:
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
            logger.error(f"File not found: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return 'An unexpected error occurred during transcription.'

    else:
        logger.info("Whisper transcription is disabled.")
        return None
        