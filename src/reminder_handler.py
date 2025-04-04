# src/reminder_handler.py

import logging
import configparser
from datetime import datetime, timezone
from config_paths import CONFIG_PATH, REMINDERS_DB_PATH
import db_utils

# Load config to get MaxAlertsPerUser
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

try:
    MAX_ALERTS_PER_USER = config.getint('Reminders', 'MaxAlertsPerUser', fallback=30)
except configparser.NoSectionError:
    MAX_ALERTS_PER_USER = 30

# Get a logger for this module
logger = logging.getLogger(__name__)
# Ensure logs bubble up to the root logger (which has the timestamp format)
logger.propagate = True
# DO NOT setLevel or add handlers here; rely on main.py or root config for formatting

async def handle_add_reminder(user_id, chat_id, reminder_text, due_time_utc_str):
    """
    Create a new reminder for user 'user_id', to be delivered in chat 'chat_id' 
    at time 'due_time_utc_str' (ISO8601 UTC). 
    'reminder_text' is the user-provided note.

    Returns a string describing success/failure to be inserted 
    into the chat conversation.
    """
    # 1) Check if DB is initialized
    if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
        logger.error("Attempt to add reminder but DB not initialized!")
        return "Error: DB not available. Reminders cannot be added."

    # 2) Validate/parse time format
    try:
        datetime.strptime(due_time_utc_str, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        logger.warning(f"User {user_id} attempted to add reminder with invalid due_time_utc: {due_time_utc_str}")
        return (
            "The time format is invalid. "
            "Please specify in ISO8601 UTC, e.g. 2025-01-02T13:00:00Z "
            "or convert user-friendly times to UTC first."
        )

    # 3) Check user's current reminder count
    current_count = db_utils.count_pending_reminders_for_user(REMINDERS_DB_PATH, user_id)

    # Only enforce the limit if it's > 0
    if MAX_ALERTS_PER_USER > 0 and current_count >= MAX_ALERTS_PER_USER:
        logger.info(f"User {user_id} has {current_count} reminders; reached max of {MAX_ALERTS_PER_USER}.")
        return f"You already have {current_count} pending reminders. The maximum is {MAX_ALERTS_PER_USER}."

    # 4) Add to DB
    reminder_id = db_utils.add_reminder_to_db(
        REMINDERS_DB_PATH, user_id, chat_id, reminder_text, due_time_utc_str
    )
    if reminder_id:
        logger.info(
            f"User {user_id} created reminder #{reminder_id}: "
            f"'{reminder_text}' at {due_time_utc_str}"
        )
        return (
            f"Your reminder (#{reminder_id}) has been set for {due_time_utc_str} (UTC). "
            f"Message: '{reminder_text}'"
        )
    else:
        logger.error(f"Failed to add reminder to DB for user {user_id}. Possibly DB error.")
        return "Failed to add your reminder due to a database error. Sorry!"


async def handle_view_reminders(user_id):
    """
    Return a string summarizing all of the user's pending reminders 
    (status='pending'). If none exist, say so.
    """
    if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
        logger.error("Attempt to view reminders but DB not available!")
        return "Error: DB not available. Cannot view reminders."

    reminders = db_utils.get_pending_reminders_for_user(REMINDERS_DB_PATH, user_id)
    if not reminders:
        logger.info(f"User {user_id} has no pending reminders.")
        return "You currently have no pending reminders."

    logger.info(f"User {user_id} is viewing {len(reminders)} reminders.")
    lines = ["Here are your current reminders:"]
    for r in reminders:
        rid = r['reminder_id']
        text = r['reminder_text']
        due_utc = r['due_time_utc']
        lines.append(f"• Reminder #{rid}: due {due_utc}, text: '{text}'")
    return "\n".join(lines)


async def handle_delete_reminder(user_id, reminder_id):
    """
    Delete a reminder by ID. Only deletes if it belongs to 'user_id'.
    Returns success/failure text.
    """
    if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
        logger.error("Attempt to delete reminder but DB not available!")
        return "Error: DB not available. Cannot delete reminders."

    success = db_utils.delete_reminder_from_db(REMINDERS_DB_PATH, reminder_id, user_id)
    if success:
        logger.info(f"User {user_id} deleted reminder #{reminder_id}.")
        return f"Reminder #{reminder_id} has been deleted."
    else:
        logger.warning(
            f"User {user_id} tried to delete reminder #{reminder_id}, "
            "which didn't exist or didn't belong to them."
        )
        return f"No reminder #{reminder_id} was found (or it's not yours)."


async def handle_edit_reminder(user_id, reminder_id, new_due_time_utc=None, new_text=None):
    """
    Edit the time and/or text of an existing reminder. If new_due_time_utc or new_text 
    are None, the old value is retained. 
    Only the user who owns the reminder can edit it.

    Return success/failure text for the user. 
    """
    if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
        logger.error("Attempt to edit reminder but DB not initialized!")
        return "Error: DB not available. Cannot edit reminders."

    # 1) Fetch existing to ensure user owns it
    reminder = db_utils.get_reminder_by_id(REMINDERS_DB_PATH, reminder_id)
    if not reminder:
        logger.warning(f"User {user_id} tried to edit reminder #{reminder_id} which doesn't exist.")
        return f"No such reminder #{reminder_id} found."

    if reminder['user_id'] != user_id:
        logger.warning(f"User {user_id} tried to edit reminder #{reminder_id}, but ownership mismatch.")
        return "That reminder doesn't appear to be yours."

    # 2) Decide new due_time_utc
    if new_due_time_utc:
        # Validate it
        try:
            datetime.strptime(new_due_time_utc, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            logger.warning(f"User {user_id} gave invalid date for reminder #{reminder_id}: {new_due_time_utc}")
            return "Invalid UTC date/time format. Please provide e.g. 2025-01-02T13:00:00Z."
    else:
        new_due_time_utc = reminder['due_time_utc']

    # 3) Decide new text
    if not new_text or new_text.strip() == "":
        new_text = reminder['reminder_text']

    # 4) Update in DB
    updated_ok = db_utils.update_reminder(REMINDERS_DB_PATH, reminder_id, new_due_time_utc, new_text)
    if updated_ok:
        logger.info(
            f"User {user_id} edited reminder #{reminder_id} -> new time: "
            f"{new_due_time_utc}, new text: '{new_text}'"
        )
        return (
            f"Reminder #{reminder_id} updated! \n"
            f"New time: {new_due_time_utc}\nNew text: '{new_text}'"
        )
    else:
        logger.error(
            f"User {user_id} tried to edit reminder #{reminder_id}, "
            "but update_reminder DB call failed."
        )
        return "Failed to update your reminder due to a database error."
