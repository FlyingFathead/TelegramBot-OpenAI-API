# db_utils.py

import sqlite3
import logging
import os
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

# --- Define DB_PATH by importing DATA_DIR --- # Changed from LOGS_DIR
DB_PATH = None
REMINDERS_TABLE_NAME = 'reminders'
USAGE_TABLE_NAME = 'daily_usage'
try:
    # Import DATA_DIR as the reminders DB should logically be in the data directory
    from config_paths import DATA_DIR
    if DATA_DIR and isinstance(DATA_DIR, Path):
        # Keep usage tracker in logs, but reminders in data
        REMINDERS_DB_FILENAME = 'reminders.db'
        REMINDERS_DB_PATH = DATA_DIR / REMINDERS_DB_FILENAME # Path for reminders DB
        USAGE_DB_FILENAME = 'usage_tracker.db'
        USAGE_DB_PATH = DATA_DIR / USAGE_DB_FILENAME # Path for usage DB (or keep in logs if preferred)

        # Ensure DATA_DIR exists
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            logging.info(f"Reminders SQLite database path set to: {REMINDERS_DB_PATH}")
            logging.info(f"Usage SQLite database path set to: {USAGE_DB_PATH}")
            DB_PATH = REMINDERS_DB_PATH # Use reminders path as the primary DB_PATH for initialization check? Or handle separately? Let's use reminders for now.

        except OSError as e:
             logging.error(f"Failed to ensure data directory exists at {DATA_DIR}: {e}")
             DB_PATH = None
             REMINDERS_DB_PATH = None
             USAGE_DB_PATH = None
    else:
        logging.critical("DATA_DIR imported from config_paths is invalid.")
        DB_PATH = None
        REMINDERS_DB_PATH = None
        USAGE_DB_PATH = None
except ImportError:
    logging.critical("Could not import DATA_DIR from config_paths.py.")
    DB_PATH = None
    REMINDERS_DB_PATH = None
    USAGE_DB_PATH = None
except Exception as e:
     logging.critical(f"Unexpected error setting DB_PATHs: {e}")
     DB_PATH = None
     REMINDERS_DB_PATH = None
     USAGE_DB_PATH = None
# --- End DB_PATH Definition ---

def _execute_sql(db_path, sql, params=(), fetch_one=False, fetch_all=False, commit=False, get_last_rowid=False):
    """Helper function to execute SQL commands with retry logic for locks."""
    if not db_path:
        logging.error("Database path is not set. Cannot execute SQL.")
        return None if fetch_one or fetch_all or get_last_rowid else False

    conn = None
    retries = 5
    delay = 0.2
    last_exception = None

    for attempt in range(retries):
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute(sql, params)

            result = None
            if commit:
                conn.commit()
                result = True
                if get_last_rowid:
                    result = cursor.lastrowid
            elif fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            else:
                 result = True # Indicate success for non-query/non-commit operations if needed

            return result # Success

        except sqlite3.OperationalError as e:
            last_exception = e
            if "locked" in str(e).lower() and attempt < retries - 1:
                 logging.warning(f"SQLite DB locked (Attempt {attempt+1}/{retries}). Retrying in {delay:.2f}s... SQL: {sql[:100]}")
                 if conn: conn.rollback() # Rollback before retrying
                 time.sleep(delay)
                 delay = min(delay * 1.5, 2.0)
            else:
                 logging.error(f"SQLite DB locked or error executing SQL after {retries} attempts: {e}\nSQL: {sql}")
                 if conn: conn.rollback()
                 break # Failed after retries or non-lock error
        except Exception as e:
            last_exception = e
            logging.error(f"Unexpected error executing SQL: {e}\nSQL: {sql}")
            if conn: conn.rollback()
            break # Failed due to unexpected error
        finally:
            if conn:
                conn.close()

    # If loop finishes without returning, it means failure
    logging.error(f"Failed to execute SQL command after {retries} attempts. Last error: {last_exception}")
    return None if fetch_one or fetch_all or get_last_rowid else False


def _create_tables_if_not_exist(db_path):
    """Creates both the reminders and daily_usage tables if they don't exist."""
    if not db_path: return False

    # SQL for reminders table
    sql_reminders = f"""
        CREATE TABLE IF NOT EXISTS {REMINDERS_TABLE_NAME} (
            reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            reminder_text TEXT NOT NULL,
            due_time_utc TEXT NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'sent', 'failed_forbidden', 'failed_bad_request', 'failed_unknown', 'deleted')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    # SQL for usage table
    sql_usage = f"""
        CREATE TABLE IF NOT EXISTS {USAGE_TABLE_NAME} (
            usage_date TEXT PRIMARY KEY,
            premium_tokens INTEGER DEFAULT 0,
            mini_tokens INTEGER DEFAULT 0
        );
    """
    # SQL for indexes
    sql_reminders_index = f"CREATE INDEX IF NOT EXISTS idx_reminders_user_status ON {REMINDERS_TABLE_NAME} (user_id, status);"
    sql_reminders_due_index = f"CREATE INDEX IF NOT EXISTS idx_reminders_due_status ON {REMINDERS_TABLE_NAME} (due_time_utc, status);"
    sql_usage_index = f"CREATE INDEX IF NOT EXISTS idx_usage_date ON {USAGE_TABLE_NAME} (usage_date);"

    success = True
    success &= _execute_sql(db_path, sql_reminders, commit=True)
    success &= _execute_sql(db_path, sql_usage, commit=True)
    success &= _execute_sql(db_path, sql_reminders_index, commit=True)
    success &= _execute_sql(db_path, sql_reminders_due_index, commit=True)
    success &= _execute_sql(db_path, sql_usage_index, commit=True)

    if success:
        logging.info(f"Ensured SQLite tables '{REMINDERS_TABLE_NAME}' and '{USAGE_TABLE_NAME}' exist in {db_path}")
    else:
        logging.error(f"Failed to create or verify SQLite tables in {db_path}")
    return success

DB_INITIALIZED_SUCCESSFULLY = False
if REMINDERS_DB_PATH: # Check specifically the reminders DB path for initialization status
    DB_INITIALIZED_SUCCESSFULLY = _create_tables_if_not_exist(REMINDERS_DB_PATH)
    # Optionally initialize the usage DB too if it's separate
    if USAGE_DB_PATH and USAGE_DB_PATH != REMINDERS_DB_PATH:
        _create_tables_if_not_exist(USAGE_DB_PATH) # Ensure usage table exists too
else:
    logging.error("Reminders database path could not be determined. SQLite functions related to reminders will be disabled.")


# --- Reminder Functions ---

def count_pending_reminders_for_user(db_path, user_id):
    """Counts the number of pending reminders for a specific user."""
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.warning("SQLite DB not initialized. Cannot count reminders.")
        return 0
    sql = f"SELECT COUNT(*) FROM {REMINDERS_TABLE_NAME} WHERE user_id = ? AND status = 'pending'"
    result = _execute_sql(db_path, sql, (user_id,), fetch_one=True)
    count = result[0] if result else 0
    logging.debug(f"Found {count} pending reminders for user {user_id}.")
    return count

def add_reminder_to_db(db_path, user_id, chat_id, reminder_text, due_time_utc_str):
    """Adds a new reminder to the database."""
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.error("DB not initialized. Cannot add reminder.")
        return None
    sql = f"""
        INSERT INTO {REMINDERS_TABLE_NAME} (user_id, chat_id, reminder_text, due_time_utc)
        VALUES (?, ?, ?, ?)
    """
    last_row_id = _execute_sql(db_path, sql, (user_id, chat_id, reminder_text, due_time_utc_str), commit=True, get_last_rowid=True)
    return last_row_id # Returns the ID of the inserted row or False/None on failure

def get_pending_reminders_for_user(db_path, user_id):
    """Gets all pending reminders for a user."""
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.error("DB not initialized. Cannot get reminders.")
        return []
    sql = f"SELECT reminder_id, reminder_text, due_time_utc FROM {REMINDERS_TABLE_NAME} WHERE user_id = ? AND status = 'pending' ORDER BY due_time_utc ASC"
    rows = _execute_sql(db_path, sql, (user_id,), fetch_all=True)
    return [{'reminder_id': r[0], 'reminder_text': r[1], 'due_time_utc': r[2]} for r in rows] if rows else []

def delete_reminder_from_db(db_path, reminder_id, user_id):
    """Deletes a reminder by ID if it belongs to the user."""
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.error("DB not initialized. Cannot delete reminder.")
        return False
    # First verify ownership - this prevents accidental deletion if API passes wrong ID
    owner_check_sql = f"SELECT user_id FROM {REMINDERS_TABLE_NAME} WHERE reminder_id = ?"
    owner_result = _execute_sql(db_path, owner_check_sql, (reminder_id,), fetch_one=True)

    if not owner_result or owner_result[0] != user_id:
        logging.warning(f"Attempt to delete reminder {reminder_id} failed: Not found or ownership mismatch for user {user_id}.")
        return False

    # If ownership confirmed, proceed with deletion
    sql = f"DELETE FROM {REMINDERS_TABLE_NAME} WHERE reminder_id = ? AND user_id = ?"
    return _execute_sql(db_path, sql, (reminder_id, user_id), commit=True)

def get_reminder_by_id(db_path, reminder_id):
    """Gets a specific reminder by its ID."""
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.error("DB not initialized. Cannot get reminder by ID.")
        return None
    sql = f"SELECT user_id, reminder_text, due_time_utc, status FROM {REMINDERS_TABLE_NAME} WHERE reminder_id = ?"
    row = _execute_sql(db_path, sql, (reminder_id,), fetch_one=True)
    return {'user_id': row[0], 'reminder_text': row[1], 'due_time_utc': row[2], 'status': row[3]} if row else None

def update_reminder(db_path, reminder_id, new_due_time_utc, new_text):
    """Updates the due time and/or text of a reminder."""
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.error("DB not initialized. Cannot update reminder.")
        return False
    sql = f"UPDATE {REMINDERS_TABLE_NAME} SET due_time_utc = ?, reminder_text = ?, status = 'pending' WHERE reminder_id = ?"
    # Also reset status to 'pending' in case it was failed etc.
    return _execute_sql(db_path, sql, (new_due_time_utc, new_text, reminder_id), commit=True)

def get_due_reminders(db_path, current_utc_time_str):
    """Gets all pending reminders that are due."""
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.error("DB not initialized. Cannot get due reminders.")
        return []
    sql = f"SELECT reminder_id, user_id, chat_id, reminder_text FROM {REMINDERS_TABLE_NAME} WHERE status = 'pending' AND due_time_utc <= ? ORDER BY due_time_utc ASC"
    rows = _execute_sql(db_path, sql, (current_utc_time_str,), fetch_all=True)
    return [{'reminder_id': r[0], 'user_id': r[1], 'chat_id': r[2], 'reminder_text': r[3]} for r in rows] if rows else []

def get_past_reminders_for_user(db_path, user_id, limit=5):
    """
    Gets the most recent 'past' reminders (status != 'pending') for a user,
    ordered by the time they were due or created. 
    Typically we consider 'sent','failed_*','deleted' as "past."
    """
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.error("DB not initialized. Cannot get past reminders.")
        return []

    sql = f"""
        SELECT reminder_id, reminder_text, due_time_utc, status 
        FROM {REMINDERS_TABLE_NAME}
        WHERE user_id = ? 
          AND status != 'pending'
        ORDER BY due_time_utc DESC
        LIMIT ?
    """
    rows = _execute_sql(db_path, sql, (user_id, limit), fetch_all=True)
    if not rows:
        return []
    # Build a list of dicts
    reminders = []
    for row in rows:
        reminders.append({
            'reminder_id': row[0],
            'reminder_text': row[1],
            'due_time_utc': row[2],
            'status': row[3]
        })
    return reminders

def update_reminder_status(db_path, reminder_id, new_status):
    """Updates the status of a reminder (e.g., to 'sent' or 'failed')."""
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.error("DB not initialized. Cannot update reminder status.")
        return False
    sql = f"UPDATE {REMINDERS_TABLE_NAME} SET status = ? WHERE reminder_id = ?"
    return _execute_sql(db_path, sql, (new_status, reminder_id), commit=True)

# --- Usage Functions (Using USAGE_DB_PATH) ---

def _get_daily_usage_sync(db_path, usage_date_str):
    """
    Retrieves the token usage for a specific date from the USAGE database.
    Returns tuple (premium_tokens, mini_tokens) on success, or None if DB is not initialized or any error occurs.
    """
    if not USAGE_DB_PATH: # Check if the specific path for usage DB is set
        logging.warning("Usage SQLite DB path not set. Cannot get usage.")
        return None

    # Ensure the usage table exists in the correct DB file
    _create_tables_if_not_exist(USAGE_DB_PATH) # Redundant if called at start, but safe

    sql = f"SELECT premium_tokens, mini_tokens FROM {USAGE_TABLE_NAME} WHERE usage_date = ?"
    row = _execute_sql(USAGE_DB_PATH, sql, (usage_date_str,), fetch_one=True)

    if row:
        premium = row[0] if row[0] is not None else 0
        mini = row[1] if row[1] is not None else 0
        return premium, mini
    else:
        return 0, 0 # No record found, return 0,0

def _update_daily_usage_sync(db_path, usage_date_str, model_tier, tokens_used):
    """
    Adds tokens used to the appropriate counter for the given date in the USAGE database.
    Handles concurrent access with retries. Does nothing if USAGE_DB_PATH isn't set.
    """
    if not USAGE_DB_PATH:
        logging.warning("Usage SQLite DB path not set. Cannot update usage.")
        return
    if tokens_used <= 0: return

    # Ensure the usage table exists
    _create_tables_if_not_exist(USAGE_DB_PATH)

    conn = None
    retries = 5
    delay = 0.2
    last_exception = None

    for attempt in range(retries):
        try:
            conn = sqlite3.connect(USAGE_DB_PATH, timeout=10) # Connect to USAGE DB
            cursor = conn.cursor()
            # Use INSERT OR IGNORE to handle the case where the date doesn't exist yet
            cursor.execute(f"INSERT OR IGNORE INTO {USAGE_TABLE_NAME} (usage_date, premium_tokens, mini_tokens) VALUES (?, 0, 0)", (usage_date_str,))

            if model_tier == 'premium':
                column_to_update = 'premium_tokens'
            elif model_tier == 'mini':
                column_to_update = 'mini_tokens'
            else:
                 logging.warning(f"Unknown model tier '{model_tier}' provided for usage update. Cannot log.")
                 return

            # Use atomic update
            sql = f"UPDATE {USAGE_TABLE_NAME} SET {column_to_update} = {column_to_update} + ? WHERE usage_date = ?"
            cursor.execute(sql, (tokens_used, usage_date_str))
            conn.commit()
            logging.debug(f"Successfully updated usage for {usage_date_str}, tier {model_tier}, tokens {tokens_used}.")
            return # Success

        except sqlite3.OperationalError as e:
            last_exception = e
            if "locked" in str(e).lower() and attempt < retries - 1:
                 logging.warning(f"Usage SQLite DB locked (Attempt {attempt+1}/{retries}). Retrying in {delay:.2f}s...")
                 if conn: conn.rollback()
                 time.sleep(delay)
                 delay = min(delay * 1.5, 2.0)
            else:
                 logging.error(f"Usage SQLite DB locked or error during write for {usage_date_str} after {retries} attempts: {e}")
                 if conn: conn.rollback()
                 break
        except Exception as e:
            last_exception = e
            logging.error(f"Unexpected error updating daily usage in SQLite ({USAGE_DB_PATH}) for {usage_date_str}: {e}")
            if conn: conn.rollback()
            break
        finally:
            if conn:
                conn.close()
    logging.error(f"Failed to update usage for {usage_date_str}, tier {model_tier}, tokens {tokens_used} after {retries} attempts. Last error: {last_exception}")

def _cleanup_old_usage_sync(db_path, max_history_days):
    """Deletes usage records older than max_history_days from the USAGE database."""
    if not USAGE_DB_PATH:
        logging.warning("Usage SQLite DB path not set. Cannot cleanup old usage.")
        return

    cutoff_date_dt = datetime.now(timezone.utc) - timedelta(days=max_history_days)
    cutoff_date_str = cutoff_date_dt.strftime('%Y-%m-%d')
    sql = f"DELETE FROM {USAGE_TABLE_NAME} WHERE usage_date < ?"

    success = _execute_sql(USAGE_DB_PATH, sql, (cutoff_date_str,), commit=True)

    # Note: _execute_sql doesn't easily return rowcount, so logging detail is reduced
    if success:
        logging.info(f"SQLite Usage Cleanup: Attempted deletion of records older than {cutoff_date_str}.")
    else:
        logging.error(f"Error cleaning up old usage in SQLite ({USAGE_DB_PATH}).")