# voice_message_handler.py
# ~~~~~~~~~~~~~~~~~~~~~
# voice message handler
# ~~~~~~~~~~~~~~~~~~~~~
#
# Handles Telegram voice messages:
#   1. downloads the .ogg voice file
#   2. checks duration
#   3. sends it to OpenAI speech-to-text
#   4. stores the plain transcription in context.user_data['transcribed_text']
#   5. calls the normal text message handler path
#
# Supported STT models via bot.stt_model / config.ini STTModel / env:
#   - gpt-4o-transcribe
#   - gpt-4o-mini-transcribe
#   - whisper-1

import os
import html
from typing import Optional

import httpx
import openai

# tg modules
from telegram import Update
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

# tg-bot stuff
import utils


DEFAULT_STT_MODEL = "gpt-4o-transcribe"

KNOWN_STT_MODELS = {
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
    "gpt-4o-transcribe-diarize",
    "whisper-1",
}

VOICE_DOWNLOAD_TIMEOUT_SECONDS = 60.0

# Lazy client cache.
# Important: do NOT instantiate AsyncOpenAI at import time, because main.py sets
# openai.api_key only after configuration/token loading.
_openai_client: Optional[openai.AsyncOpenAI] = None
_openai_client_api_key: Optional[str] = None

def get_voice_log_context(update: Update, voice_file_path: Optional[str] = None, stt_model: Optional[str] = None) -> dict:
    """
    Build a compact logging context for Telegram voice messages.
    """
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    voice = message.voice if message and message.voice else None

    return {
        "user_id": user.id if user else None,
        "username": user.username if user else None,
        "first_name": user.first_name if user else None,
        "last_name": user.last_name if user else None,
        "chat_id": chat.id if chat else None,
        "chat_type": chat.type if chat else None,
        "chat_title": chat.title if chat else None,
        "message_id": message.message_id if message else None,
        "voice_file_id": voice.file_id if voice else None,
        "voice_unique_id": voice.file_unique_id if voice else None,
        "voice_duration": voice.duration if voice else None,
        "voice_mime_type": voice.mime_type if voice else None,
        "voice_file_size": voice.file_size if voice else None,
        "local_file_path": voice_file_path,
        "stt_model": stt_model,
    }

def get_openai_client() -> openai.AsyncOpenAI:
    """
    Lazily create/reuse the OpenAI async client.

    This respects:
      1. openai.api_key set elsewhere by main.py
      2. OPENAI_API_KEY from environment
      3. default OpenAI SDK behavior if neither is explicitly set
    """
    global _openai_client
    global _openai_client_api_key

    current_api_key = getattr(openai, "api_key", None) or os.getenv("OPENAI_API_KEY")

    if _openai_client is None or _openai_client_api_key != current_api_key:
        if current_api_key:
            _openai_client = openai.AsyncOpenAI(api_key=current_api_key)
        else:
            _openai_client = openai.AsyncOpenAI()

        _openai_client_api_key = current_api_key

    return _openai_client


def get_stt_model(bot) -> str:
    """
    Select the speech-to-text model.

    Priority:
      1. bot.stt_model          -- recommended; loaded from config.ini in main.py
      2. OPENAI_STT_MODEL env   -- useful override for systemd/docker/shell
      3. DEFAULT_STT_MODEL      -- gpt-4o-transcribe

    Good values:
      - gpt-4o-transcribe
      - gpt-4o-mini-transcribe
      - whisper-1
    """
    configured_model = getattr(bot, "stt_model", None)
    env_model = os.getenv("OPENAI_STT_MODEL")

    stt_model = (configured_model or env_model or DEFAULT_STT_MODEL).strip()

    if not stt_model:
        return DEFAULT_STT_MODEL

    return stt_model


def extract_transcription_text(transcript_response) -> Optional[str]:
    """
    Extract transcription text from OpenAI SDK response.

    Handles both:
      - modern SDK objects with .text
      - dict-like responses with ["text"]
    """
    if transcript_response is None:
        return None

    if hasattr(transcript_response, "text"):
        text = transcript_response.text
        return text.strip() if text else None

    if isinstance(transcript_response, dict):
        text = transcript_response.get("text")
        return text.strip() if text else None

    return None


def format_transcription_for_telegram(transcription_text: str) -> str:
    """
    Format the transcription for Telegram HTML output.

    The transcription text is escaped before wrapping in <b>, because Telegram
    HTML parse mode will otherwise choke/misparse on &, <, >, etc.
    """
    safe_text = html.escape(transcription_text)
    return f"🎤📝\n<b>{safe_text}</b>"


def format_transcription_for_model(transcription_text: str) -> str:
    """
    Format the transcription as model input.

    Keep this plain text. Do not feed Telegram HTML to the chat model.
    """
    return (
        "🎤📝 [STT transcribed voice message from the user] "
        f"{transcription_text.strip()} "
        "[end]"
    )


async def get_voice_duration_seconds(
    update: Update,
    voice_file_path: str,
    logger,
) -> Optional[float]:
    """
    Get voice message duration in seconds.

    Prefer Telegram's metadata if available; fall back to utils-based duration
    detection from the downloaded file.
    """
    try:
        if update.message and update.message.voice and update.message.voice.duration:
            return float(update.message.voice.duration)
    except Exception as e:
        logger.warning(f"Could not read Telegram voice duration metadata: {e}")

    try:
        duration = await utils.get_voice_message_duration(voice_file_path)
        return float(duration) if duration is not None else None
    except Exception as e:
        logger.warning(f"Could not determine voice message duration from file: {e}")
        return None


async def download_voice_file(
    file_url: str,
    voice_file_path: str,
    logger,
) -> bool:
    """
    Download Telegram voice file to disk.

    Returns True on success, False on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=VOICE_DOWNLOAD_TIMEOUT_SECONDS) as client:
            response = await client.get(file_url)

        if response.status_code != 200:
            logger.error(
                f"Failed to download voice message. "
                f"HTTP status: {response.status_code}"
            )
            return False

        if not response.content:
            logger.error("Downloaded voice message was empty.")
            return False

        with open(voice_file_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Voice message file downloaded successfully as: {voice_file_path}")
        return True

    except httpx.ReadTimeout:
        logger.error("Timeout occurred while downloading voice message.")
        raise

    except Exception as e:
        logger.error(f"Unexpected error while downloading voice message: {e}")
        return False


async def handle_voice_message(bot, update: Update, context: CallbackContext):
    """
    Main Telegram voice message handler.

    Expected bot attributes:
      - bot.is_bot_disabled
      - bot.bot_disabled_msg
      - bot.logger
      - bot.enable_whisper
      - bot.data_directory
      - bot.max_voice_message_length    # minutes
      - bot.handle_message(...)
      - bot.log_message(...)
      - bot.stt_model                   # optional, recommended
    """

    if not update.message:
        return

    # Send a "holiday message" if the bot is on a break.
    if bot.is_bot_disabled:
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=bot.bot_disabled_msg,
        )
        return

    bot.logger.info("Voice message received.")

    # Log initial Telegram-side metadata before download/STT.
    initial_log_ctx = get_voice_log_context(update)
    bot.logger.info(f"Voice message context: {initial_log_ctx}")

    if not bot.enable_whisper:
        await update.message.reply_text("Voice message transcription is currently disabled.")
        return

    if not update.message.voice:
        await update.message.reply_text("No voice message found in this update.")
        return

    await update.message.reply_text(
        "<i>Voice message received. Transcribing...</i>",
        parse_mode=ParseMode.HTML,
    )

    # Ensure the data directory exists.
    os.makedirs(bot.data_directory, exist_ok=True)

    try:
        # Retrieve the Telegram File object of the voice message.
        tg_file = await context.bot.get_file(update.message.voice.file_id)

        # Telegram gives us the downloadable file path/URL here.
        file_url = f"{tg_file.file_path}"

        voice_file_path = os.path.join(bot.data_directory, f"{tg_file.file_id}.ogg")

        downloaded_ok = await download_voice_file(
            file_url=file_url,
            voice_file_path=voice_file_path,
            logger=bot.logger,
        )

        if not downloaded_ok:
            await update.message.reply_text("Failed to download voice message.")
            return

        # Duration check.
        # Config value MaxDurationMinutes is minutes, but duration values are seconds.
        voice_duration_seconds = await get_voice_duration_seconds(
            update=update,
            voice_file_path=voice_file_path,
            logger=bot.logger,
        )

        max_voice_seconds = float(bot.max_voice_message_length) * 60.0

        if voice_duration_seconds is not None:
            bot.logger.info(
                f"Voice duration: {voice_duration_seconds:.2f}s "
                f"/ limit: {max_voice_seconds:.2f}s"
            )

            if voice_duration_seconds > max_voice_seconds:
                await update.message.reply_text(
                    "Your voice message is too long. Please keep it under {} minutes.".format(
                        bot.max_voice_message_length
                    )
                )
                bot.logger.info(f"Voice file rejected for being too long: {voice_file_path}")
                return
        else:
            bot.logger.warning(
                "Could not determine voice message duration. "
                "Proceeding with transcription anyway."
            )

        # Select STT model from bot.stt_model / env / default.
        stt_model = get_stt_model(bot)

        # Full context after local file path and STT model are known.
        voice_log_ctx = get_voice_log_context(
            update=update,
            voice_file_path=voice_file_path,
            stt_model=stt_model,
        )

        bot.logger.info(f"Voice message processing context: {voice_log_ctx}")

        if stt_model not in KNOWN_STT_MODELS:
            bot.logger.warning(
                f"STT model '{stt_model}' is not in the known local allow-list. "
                "Trying it anyway because OpenAI may have added newer models."
            )

        transcription_text = await process_voice_message(
            file_path=voice_file_path,
            enable_whisper=bot.enable_whisper,
            logger=bot.logger,
            stt_model=stt_model,
        )

        if not transcription_text:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Voice message transcription failed.",
            )
            return

        # Build model-facing and Telegram-facing versions.
        transcription_for_model = format_transcription_for_model(transcription_text)
        transcription_for_telegram = format_transcription_for_telegram(transcription_text)

        # Full operational audit log into bot.log.
        bot.logger.info(
            "Voice transcription completed: "
            f"user_id={voice_log_ctx.get('user_id')}, "
            f"username={voice_log_ctx.get('username')}, "
            f"first_name={voice_log_ctx.get('first_name')}, "
            f"last_name={voice_log_ctx.get('last_name')}, "
            f"chat_id={voice_log_ctx.get('chat_id')}, "
            f"chat_type={voice_log_ctx.get('chat_type')}, "
            f"chat_title={voice_log_ctx.get('chat_title')}, "
            f"message_id={voice_log_ctx.get('message_id')}, "
            f"voice_file_id={voice_log_ctx.get('voice_file_id')}, "
            f"voice_unique_id={voice_log_ctx.get('voice_unique_id')}, "
            f"voice_duration={voice_log_ctx.get('voice_duration')}, "
            f"voice_mime_type={voice_log_ctx.get('voice_mime_type')}, "
            f"voice_file_size={voice_log_ctx.get('voice_file_size')}, "
            f"local_file_path={voice_log_ctx.get('local_file_path')}, "
            f"stt_model={voice_log_ctx.get('stt_model')}, "
            f"transcription={transcription_text!r}"
        )

        # Store the cleaned/plain transcription in context.user_data for text handler.
        context.user_data["transcribed_text"] = transcription_for_model

        # Log the transcription into chat.log too, if ChatLoggingEnabled=True.
        bot.log_message(
            "Transcription",
            update.message.from_user.id if update.message.from_user else None,
            (
                f"user_id={voice_log_ctx.get('user_id')} | "
                f"username={voice_log_ctx.get('username')} | "
                f"first_name={voice_log_ctx.get('first_name')} | "
                f"last_name={voice_log_ctx.get('last_name')} | "
                f"chat_id={voice_log_ctx.get('chat_id')} | "
                f"chat_type={voice_log_ctx.get('chat_type')} | "
                f"chat_title={voice_log_ctx.get('chat_title')} | "
                f"message_id={voice_log_ctx.get('message_id')} | "
                f"voice_file_id={voice_log_ctx.get('voice_file_id')} | "
                f"voice_unique_id={voice_log_ctx.get('voice_unique_id')} | "
                f"voice_duration={voice_log_ctx.get('voice_duration')} | "
                f"voice_mime_type={voice_log_ctx.get('voice_mime_type')} | "
                f"voice_file_size={voice_log_ctx.get('voice_file_size')} | "
                f"local_file_path={voice_log_ctx.get('local_file_path')} | "
                f"stt_model={voice_log_ctx.get('stt_model')} | "
                f"{transcription_for_model}"
            ),
        )

        # Send transcription back to the user with Telegram HTML formatting.
        await update.message.reply_text(
            transcription_for_telegram,
            parse_mode=ParseMode.HTML,
        )

        # Pass the transcription to the normal text message handler.
        # Your text handler should read context.user_data["transcribed_text"].
        await bot.handle_message(update, context)

    except httpx.ReadTimeout:
        await update.message.reply_text(
            "Failed to download the voice message due to a timeout. Please try again."
        )
        return

    except Exception as e:
        bot.logger.error(f"Error while processing voice message: {e}")
        await update.message.reply_text("An error occurred while processing your voice message.")
        return

async def process_voice_message(
    file_path: str,
    enable_whisper,
    logger,
    stt_model: str = DEFAULT_STT_MODEL,
) -> Optional[str]:
    """
    Send an audio file to OpenAI STT and return plain transcription text.

    Works with:
      - gpt-4o-transcribe
      - gpt-4o-mini-transcribe
      - whisper-1

    Uses response_format="json" because that is the common sane denominator.
    """
    if not enable_whisper:
        logger.info("Voice transcription is disabled.")
        return None

    try:
        client = get_openai_client()

        with open(file_path, "rb") as audio_file:
            logger.info(f"Audio file being sent to OpenAI STT: {file_path}")
            logger.info(f"OpenAI STT model: {stt_model}")

            transcript_response = await client.audio.transcriptions.create(
                file=audio_file,
                model=stt_model,
                response_format="json",
            )

        logger.info(f"Transcription Response: {transcript_response}")

        transcription_text = extract_transcription_text(transcript_response)

        if not transcription_text:
            logger.warning("No transcription text returned by OpenAI STT.")
            return None

        return transcription_text

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return None

    except Exception as e:
        logger.error(f"Unexpected transcription error: {e}")
        return None