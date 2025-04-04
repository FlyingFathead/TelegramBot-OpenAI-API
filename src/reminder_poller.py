# src/reminder_poller.py

import asyncio
import logging
import configparser
from datetime import datetime, timezone # Import timezone

# --- Corrected Imports ---
from config_paths import CONFIG_PATH, REMINDERS_DB_PATH
import db_utils
from telegram.ext import Application
from telegram.error import Forbidden, BadRequest
from telegram.constants import ParseMode

# load and use logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load configuration
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

# Read configuration safely
try:
    POLLING_INTERVAL = config.getint('Reminders', 'PollingIntervalSeconds', fallback=60) # Default to 60s
    REMINDERS_ENABLED = config.getboolean('Reminders', 'EnableReminders', fallback=False)
except configparser.NoSectionError:
    logger.warning("[Reminders] section missing in config.ini, using defaults (Polling=60s, Enabled=False)")
    POLLING_INTERVAL = 60
    REMINDERS_ENABLED = False
except ValueError:
    logger.error("Invalid non-integer value for PollingIntervalSeconds in config.ini. Using default 60s.")
    POLLING_INTERVAL = 60
    REMINDERS_ENABLED = config.getboolean('Reminders', 'EnableReminders', fallback=False) # Still try to read enable flag

# split to fit to telegram's msg length
MAX_TG_MSG_LENGTH = 4096

def split_long_message(message, max_length=MAX_TG_MSG_LENGTH):
    """
    Splits a message into multiple parts, each up to max_length characters,
    and returns a list of parts.
    """
    parts = []
    start_index = 0
    while start_index < len(message):
        # Slice out a chunk of up to 'max_length' characters
        part = message[start_index:start_index + max_length]
        parts.append(part)
        start_index += max_length
    return parts

# --- Corrected Function Signature ---
async def reminder_poller(application: Application):
    """Periodically checks for due reminders and sends notifications."""

    # Check if the feature is enabled right at the start
    if not REMINDERS_ENABLED:
        logger.info("Reminder Poller exiting: Feature disabled in config.ini.")
        return # Stop the poller task if disabled

    # Check if the database was initialized successfully
    if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
        logger.error("Reminder Poller exiting: DB was not initialized successfully.")
        return

    logger.info(f"Reminder poller started. Checking every {POLLING_INTERVAL} seconds.")

    while True:
        try:
            # --- Get Current Time ---
            now_utc_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

            # --- Fetch due reminders using the correct DB path and time ---
            due_reminders = db_utils.get_due_reminders(REMINDERS_DB_PATH, now_utc_str)

            if due_reminders:
                logger.info(f"Found {len(due_reminders)} due reminders.")
                for r in due_reminders:
                    reminder_id = r['reminder_id']
                    user_id = r['user_id']
                    chat_id = r['chat_id']
                    raw_text = r['reminder_text']

                    # The text you'd like to send (with an optional emoji, etc.)
                    msg = f"🔔 {raw_text}"

                    # 1) Split into multiple parts if over 4k
                    msg_parts = split_long_message(msg)

                    try:
                        # 2) Send each part in a separate message
                        for part in msg_parts:
                            await application.bot.send_message(
                                chat_id=chat_id,
                                text=part,
                                parse_mode=ParseMode.HTML
                            )

                        # 3) Mark the reminder as sent
                        db_utils.update_reminder_status(REMINDERS_DB_PATH, reminder_id, 'sent')
                        logger.info(f"Sent reminder {reminder_id} to chat {chat_id} for user {user_id}.")

                    # --- Specific Error Handling ---
                    except Forbidden:
                        logger.warning(f"Failed sending reminder {reminder_id} to chat {chat_id}. Bot forbidden (blocked?).")
                        db_utils.update_reminder_status(REMINDERS_DB_PATH, reminder_id, 'failed_forbidden')
                    except BadRequest as e:
                        logger.error(f"Failed sending reminder {reminder_id} to chat {chat_id}. Bad request (chat not found?): {e}")
                        db_utils.update_reminder_status(REMINDERS_DB_PATH, reminder_id, 'failed_bad_request')
                    except Exception as e:
                        logger.error(f"Unexpected error sending reminder {reminder_id} to chat {chat_id}: {e}")
                        # Decide: update status to 'failed_unknown' or leave 'pending' to retry?
                        # Let's mark as failed for now to avoid potential spamming if the error persists.
                        db_utils.update_reminder_status(REMINDERS_DB_PATH, reminder_id, 'failed_unknown')
            else:
                logger.debug("No reminders due.")

        except Exception as e:
             logger.error(f"Error in reminder polling loop: {e}")
             # Avoid crashing the poller, wait before next cycle
             await asyncio.sleep(POLLING_INTERVAL) # Still wait even if there was an error fetching

        # Wait for the next polling interval
        await asyncio.sleep(POLLING_INTERVAL)