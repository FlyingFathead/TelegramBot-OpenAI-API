# src/reminder_handler.py

import logging
import configparser
from datetime import datetime, timezone
from config_paths import CONFIG_PATH, DB_PATH
import db_utils

# Load config to get MaxAlertsPerUser
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

try:
    MAX_ALERTS_PER_USER = config.getint('Reminders', 'MaxAlertsPerUser', fallback=30)
except configparser.NoSectionError:
    MAX_ALERTS_PER_USER = 30

logger = logging.getLogger(__name__)

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
    current_count = db_utils.count_pending_reminders_for_user(DB_PATH, user_id)
    if current_count >= MAX_ALERTS_PER_USER:
        logger.info(f"User {user_id} has {current_count} reminders; reached max of {MAX_ALERTS_PER_USER}.")
        return f"You already have {current_count} pending reminders. The maximum is {MAX_ALERTS_PER_USER}."

    # 4) Add to DB
    reminder_id = db_utils.add_reminder_to_db(DB_PATH, user_id, chat_id, reminder_text, due_time_utc_str)
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

    reminders = db_utils.get_pending_reminders_for_user(DB_PATH, user_id)
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

    success = db_utils.delete_reminder_from_db(DB_PATH, reminder_id, user_id)
    if success:
        logger.info(f"User {user_id} deleted reminder #{reminder_id}.")
        return f"Reminder #{reminder_id} has been deleted."
    else:
        logger.warning(f"User {user_id} tried to delete reminder #{reminder_id}, which didn't exist or didn't belong to them.")
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
    reminder = db_utils.get_reminder_by_id(DB_PATH, reminder_id)
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
    updated_ok = db_utils.update_reminder(DB_PATH, reminder_id, new_due_time_utc, new_text)
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
        logger.error(f"User {user_id} tried to edit reminder #{reminder_id}, but update_reminder DB call failed.")
        return "Failed to update your reminder due to a database error."


# # src/reminder_handler.py

# # reminder_handler.py

# import logging
# from datetime import datetime, timezone
# import configparser
# from config_paths import CONFIG_PATH, DB_PATH
# import db_utils

# config = configparser.ConfigParser()
# config.read(CONFIG_PATH)

# try:
#     MAX_ALERTS_PER_USER = config.getint('Reminders', 'MaxAlertsPerUser', fallback=30)
# except configparser.NoSectionError:
#     MAX_ALERTS_PER_USER = 30

# logger = logging.getLogger(__name__)

# async def handle_add_reminder(user_id, chat_id, reminder_text, due_time_utc_str):
#     """Handles the logic to add a reminder."""
#     if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
#         return "Error: Reminder database is not available."

#     # Validate time format or parse user input here
#     # Example: user passes 'YYYY-MM-DDTHH:MM:SSZ' for UTC or some relative time
#     # If user says "5 minutes from now," you convert that to a real UTC string, etc.

#     try:
#         datetime.strptime(due_time_utc_str, '%Y-%m-%dT%H:%M:%SZ')  
#     except ValueError:
#         return "Error: Invalid or unsupported time format. Use e.g. 2025-01-02T13:00:00Z"

#     # Check user's limit
#     current_count = db_utils.count_pending_reminders_for_user(DB_PATH, user_id)
#     if current_count >= MAX_ALERTS_PER_USER:
#         return f"You already have {current_count} pending reminders; max is {MAX_ALERTS_PER_USER}."

#     # Add it
#     reminder_id = db_utils.add_reminder_to_db(DB_PATH, user_id, chat_id, reminder_text, due_time_utc_str)
#     if reminder_id:
#         return f"Reminder #{reminder_id} set for {due_time_utc_str} (UTC)."
#     else:
#         return "Failed to add reminder."

# async def handle_view_reminders(user_id):
#     if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
#         return "Error: DB not available."

#     reminders = db_utils.get_pending_reminders_for_user(DB_PATH, user_id)
#     if not reminders:
#         return "You have no pending reminders."
    
#     lines = ["Your pending reminders:"]
#     for r in reminders:
#         lines.append(f"• ID: {r['reminder_id']} | Due: {r['due_time_utc']} | Text: {r['reminder_text']}")
#     return "\n".join(lines)

# async def handle_delete_reminder(user_id, reminder_id):
#     if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
#         return "Error: DB not available."

#     success = db_utils.delete_reminder_from_db(DB_PATH, reminder_id, user_id)
#     if success:
#         return f"Reminder #{reminder_id} deleted."
#     else:
#         return f"Reminder #{reminder_id} not found (or not yours)."


# # import logging
# # from datetime import datetime, timezone
# # import db_utils # Assuming db_utils functions are implemented
# # import configparser
# # from config_paths import CONFIG_PATH, DB_PATH # Import necessary paths

# # # Load config to get MaxAlertsPerUser
# # config = configparser.ConfigParser()
# # config.read(CONFIG_PATH)
# # try:
# #     MAX_ALERTS_PER_USER = config.getint('Reminders', 'MaxAlertsPerUser', fallback=30)
# # except configparser.NoSectionError:
# #     MAX_ALERTS_PER_USER = 30 # Default if section missing

# # logger = logging.getLogger(__name__)

# # async def handle_add_reminder(user_id, chat_id, reminder_text, due_time_utc_str):
# #     """Handles the logic to add a reminder."""
# #     if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
# #         return "Error: Reminder database is not available."

# #     try:
# #         # Validate UTC time format (basic check)
# #         datetime.strptime(due_time_utc_str, '%Y-%m-%dT%H:%M:%SZ') # Or use a more robust parser if needed

# #         # Check user's current reminder count
# #         current_count = db_utils.count_pending_reminders_for_user(DB_PATH, user_id)
# #         if current_count >= MAX_ALERTS_PER_USER:
# #             return f"Sorry, you've reached the maximum limit of {MAX_ALERTS_PER_USER} pending reminders."

# #         # Add to DB
# #         reminder_id = db_utils.add_reminder_to_db(DB_PATH, user_id, chat_id, reminder_text, due_time_utc_str)

# #         if reminder_id:
# #             # Convert UTC time string to datetime object for formatting
# #             due_dt = datetime.strptime(due_time_utc_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
# #             # Format for user confirmation (consider local time if feasible, otherwise UTC)
# #             readable_time = due_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
# #             return f"Reminder #{reminder_id} set! I'll remind you about '{reminder_text}' at {readable_time}."
# #         else:
# #             return "Failed to add reminder to the database."

# #     except ValueError:
# #         logger.error(f"Invalid due_time_utc format received: {due_time_utc_str}")
# #         return "Error: Invalid time format received for the reminder."
# #     except Exception as e:
# #         logger.error(f"Error adding reminder: {e}")
# #         return "An error occurred while setting the reminder."

# # async def handle_view_reminders(user_id):
# #     """Handles the logic to view pending reminders."""
# #     if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
# #         return "Error: Reminder database is not available."

# #     try:
# #         reminders = db_utils.get_pending_reminders_for_user(DB_PATH, user_id)
# #         if not reminders:
# #             return "You have no pending reminders."

# #         response_text = "Your pending reminders:\n"
# #         for reminder in reminders:
# #             # reminder format depends on what get_pending_reminders_for_user returns, e.g., a list of dicts
# #             reminder_id = reminder['reminder_id']
# #             text = reminder['reminder_text']
# #             due_dt = datetime.strptime(reminder['due_time_utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
# #             readable_time = due_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
# #             response_text += f"- ID: {reminder_id}, Due: {readable_time}, Text: {text}\n"
# #         return response_text

# #     except Exception as e:
# #         logger.error(f"Error viewing reminders for user {user_id}: {e}")
# #         return "An error occurred while fetching your reminders."

# # async def handle_delete_reminder(user_id, reminder_id):
# #     """Handles the logic to delete a reminder."""
# #     if not db_utils.DB_INITIALIZED_SUCCESSFULLY:
# #         return "Error: Reminder database is not available."

# #     try:
# #         success = db_utils.delete_reminder_from_db(DB_PATH, reminder_id, user_id)
# #         if success:
# #             return f"Reminder #{reminder_id} has been deleted."
# #         else:
# #             # This could be because the ID doesn't exist or doesn't belong to the user
# #             return f"Could not delete reminder #{reminder_id}. Please ensure the ID is correct and belongs to you."
# #     except Exception as e:
# #         logger.error(f"Error deleting reminder {reminder_id} for user {user_id}: {e}")
# #         return "An error occurred while deleting the reminder."