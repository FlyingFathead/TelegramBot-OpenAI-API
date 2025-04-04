# db_utils.py

import sqlite3
import logging
import os
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta # Ensure timezone is imported

# --- Define DB Paths by importing LOGS_DIR ---
USAGE_DB_PATH = None
REMINDERS_DB_PATH = None
LOGS_DIR_PATH = None # Store the directory path itself

try:
    # Import the directory path
    from config_paths import LOGS_DIR
    if LOGS_DIR and isinstance(LOGS_DIR, Path):
        LOGS_DIR_PATH = LOGS_DIR # Store the Path object
        # Ensure the directory exists
        try:
            LOGS_DIR_PATH.mkdir(parents=True, exist_ok=True)
            logging.info(f"Ensured logs directory exists at {LOGS_DIR_PATH}")

            # Define paths for both databases within the logs directory
            USAGE_DB_FILENAME = 'usage_tracker.db'
            REMINDERS_DB_FILENAME = 'reminders.db' # New filename for reminders
            USAGE_DB_PATH = LOGS_DIR_PATH / USAGE_DB_FILENAME
            REMINDERS_DB_PATH = LOGS_DIR_PATH / REMINDERS_DB_FILENAME # Path for the new DB

            logging.info(f"Usage SQLite database path set to: {USAGE_DB_PATH}")
            logging.info(f"Reminders SQLite database path set to: {REMINDERS_DB_PATH}")

        except OSError as e:
             logging.error(f"Failed to ensure logs directory exists at {LOGS_DIR_PATH}: {e}")
             # If directory fails, paths remain None
             USAGE_DB_PATH = None
             REMINDERS_DB_PATH = None
    else:
        logging.critical("LOGS_DIR imported from config_paths is invalid or not a Path object.")
except ImportError:
    logging.critical("Could not import LOGS_DIR from config_paths.py.")
except Exception as e:
     logging.critical(f"Unexpected error setting DB paths: {e}")
# --- End DB Path Definitions ---

# --- Initialization Function for Usage DB ---
def _create_usage_db_if_not_exists(db_path):
    if not db_path: return False
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_usage (
                usage_date TEXT PRIMARY KEY,
                premium_tokens INTEGER DEFAULT 0,
                mini_tokens INTEGER DEFAULT 0
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_date ON daily_usage (usage_date);")
        conn.commit()
        logging.info(f"Ensured SQLite table 'daily_usage' exists in {db_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to create or verify usage table in {db_path}: {e}")
        return False
    finally:
        if conn: conn.close()

# --- Initialization Function for Reminders DB ---
def _create_reminders_db_if_not_exists(db_path):
    if not db_path: return False
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                reminder_text TEXT NOT NULL,
                due_time_utc TEXT NOT NULL,
                creation_time_utc TEXT NOT NULL, -- Added creation time
                status TEXT NOT NULL DEFAULT 'pending' -- Added status
            );
        """)
        # Add potentially useful indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminder_user_status ON reminders (user_id, status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminder_due_status ON reminders (due_time_utc, status);")
        conn.commit()
        logging.info(f"Ensured SQLite table 'reminders' exists in {db_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to create or verify reminders table in {db_path}: {e}")
        return False
    finally:
        if conn: conn.close()

# --- Initialize Flags ---
USAGE_DB_INITIALIZED_SUCCESSFULLY = False
if USAGE_DB_PATH:
    USAGE_DB_INITIALIZED_SUCCESSFULLY = _create_usage_db_if_not_exists(USAGE_DB_PATH)
else:
    logging.error("Usage database path could not be determined. Usage DB functions will be disabled.")

REMINDERS_DB_INITIALIZED_SUCCESSFULLY = False
if REMINDERS_DB_PATH:
    REMINDERS_DB_INITIALIZED_SUCCESSFULLY = _create_reminders_db_if_not_exists(REMINDERS_DB_PATH)
else:
    logging.error("Reminders database path could not be determined. Reminder functions will be disabled.")

# ===========================================
# == USAGE TRACKING FUNCTIONS (No changes) ==
# ===========================================
# These functions now implicitly operate on USAGE_DB_PATH
# because that's the path passed to them from other modules.
# Make sure to pass USAGE_DB_PATH where these are called.

def _get_daily_usage_sync(usage_db_path, usage_date_str):
    if not USAGE_DB_INITIALIZED_SUCCESSFULLY: # Check specific flag
        logging.warning("Usage SQLite DB not initialized. Cannot get usage.")
        return None
    conn = None
    # ... (rest of the function remains the same, uses usage_db_path argument) ...
    try:
        conn = sqlite3.connect(usage_db_path, timeout=10)
        # ... rest of the logic ...
    except Exception as e:
        logging.error(f"Error getting daily usage from {usage_db_path} for {usage_date_str}: {e}")
        # ... rest of error handling ...
    finally:
        if conn: conn.close()


def _update_daily_usage_sync(usage_db_path, usage_date_str, model_tier, tokens_used):
    if not USAGE_DB_INITIALIZED_SUCCESSFULLY: # Check specific flag
        logging.warning("Usage SQLite DB not initialized. Cannot update usage.")
        return
    if tokens_used <= 0: return
    conn = None
    retries = 5
    delay = 0.2
    # ... (rest of the function remains the same, uses usage_db_path argument) ...
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(usage_db_path, timeout=10)
            # ... rest of logic ...
        except Exception as e:
             logging.error(f"Error updating usage in {usage_db_path} for {usage_date_str}: {e}")
             # ... rest of error handling ...
        finally:
            if conn: conn.close()


def _cleanup_old_usage_sync(usage_db_path, max_history_days):
    if not USAGE_DB_INITIALIZED_SUCCESSFULLY: # Check specific flag
        logging.warning("Usage SQLite DB not initialized. Cannot cleanup old usage.")
        return
    conn = None
    # ... (rest of the function remains the same, uses usage_db_path argument) ...
    try:
        conn = sqlite3.connect(usage_db_path, timeout=10)
        # ... rest of logic ...
    except Exception as e:
        logging.error(f"Error cleaning up usage in {usage_db_path}: {e}")
        # ... rest of error handling ...
    finally:
        if conn: conn.close()


# ===========================================
# ===== REMINDER FUNCTIONS (Operate on REMINDERS_DB_PATH) =====
# ===========================================
# These functions should be called passing REMINDERS_DB_PATH

def add_reminder_to_db(reminders_db_path, user_id, chat_id, reminder_text, due_time_utc_str):
    """Adds a reminder to the reminders database."""
    if not REMINDERS_DB_INITIALIZED_SUCCESSFULLY:
        logging.error("Reminders DB not initialized. Cannot add reminder.")
        return None

    conn = None
    retries = 3 # Add basic retry for writes
    delay = 0.1
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(reminders_db_path, timeout=10)
            cur = conn.cursor()
            created_at_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            cur.execute("""
                INSERT INTO reminders (user_id, chat_id, reminder_text, due_time_utc, creation_time_utc, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, chat_id, reminder_text, due_time_utc_str, created_at_str, 'pending')) # Explicitly set status
            reminder_id = cur.lastrowid
            conn.commit()
            logging.info(f"Successfully added reminder {reminder_id} for user {user_id} to {reminders_db_path}")
            return reminder_id
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < retries - 1:
                 logging.warning(f"Reminders DB locked during add (Attempt {attempt+1}/{retries}). Retrying...")
                 if conn: conn.rollback() # Rollback before retry
                 time.sleep(delay * (attempt + 1)) # Basic backoff
            else:
                logging.error(f"Error adding reminder for user {user_id} after {retries} attempts: {e}")
                if conn: conn.rollback()
                return None # Failed after retries
        except Exception as e:
            logging.error(f"Unexpected error adding reminder for user {user_id}: {e}")
            if conn: conn.rollback()
            return None
        finally:
            if conn: conn.close()
    return None # Should not be reached if loop completes, but explicit return

def count_pending_reminders_for_user(reminders_db_path, user_id):
    """Counts pending reminders for a user in the reminders database."""
    if not REMINDERS_DB_INITIALIZED_SUCCESSFULLY:
        logging.warning("Reminders DB not initialized. Cannot count reminders.")
        return 0
    conn = None
    try:
        conn = sqlite3.connect(reminders_db_path, timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM reminders WHERE user_id = ? AND status = 'pending'", (user_id,))
        count_val = cur.fetchone()[0]
        return count_val
    except Exception as e:
        logging.error(f"Error counting reminders for user {user_id} in {reminders_db_path}: {e}")
        return 0
    finally:
        if conn: conn.close()

def get_pending_reminders_for_user(reminders_db_path, user_id):
    """Gets pending reminders for a user from the reminders database."""
    if not REMINDERS_DB_INITIALIZED_SUCCESSFULLY:
        logging.warning("Reminders DB not initialized. Cannot get reminders.")
        return []
    conn = None
    try:
        conn = sqlite3.connect(reminders_db_path, timeout=10)
        # Use row factory for dict results
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT reminder_id, reminder_text, due_time_utc
            FROM reminders
            WHERE user_id = ? AND status = 'pending'
            ORDER BY due_time_utc ASC
        """, (user_id,))
        rows = cur.fetchall()
        # Convert Row objects to dictionaries
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"Error fetching reminders for user {user_id} from {reminders_db_path}: {e}")
        return []
    finally:
        if conn: conn.close()


def delete_reminder_from_db(reminders_db_path, reminder_id, user_id):
    """Deletes a specific reminder belonging to a user from the reminders database."""
    if not REMINDERS_DB_INITIALIZED_SUCCESSFULLY:
        logging.error("Reminders DB not initialized. Cannot delete reminder.")
        return False
    conn = None
    retries = 3
    delay = 0.1
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(reminders_db_path, timeout=10)
            cur = conn.cursor()
            cur.execute("DELETE FROM reminders WHERE reminder_id = ? AND user_id = ?", (reminder_id, user_id))
            rowcount = cur.rowcount
            conn.commit()
            if rowcount > 0:
                logging.info(f"Successfully deleted reminder {reminder_id} for user {user_id} from {reminders_db_path}")
            else:
                logging.warning(f"No reminder found with ID {reminder_id} for user {user_id} to delete in {reminders_db_path}")
            return (rowcount > 0)
        except sqlite3.OperationalError as e:
             if "locked" in str(e).lower() and attempt < retries - 1:
                 logging.warning(f"Reminders DB locked during delete (Attempt {attempt+1}/{retries}). Retrying...")
                 if conn: conn.rollback()
                 time.sleep(delay * (attempt + 1))
             else:
                logging.error(f"Error deleting reminder {reminder_id} for user {user_id} after {retries} attempts: {e}")
                if conn: conn.rollback()
                return False
        except Exception as e:
            logging.error(f"Unexpected error deleting reminder {reminder_id} for user {user_id}: {e}")
            if conn: conn.rollback()
            return False
        finally:
            if conn: conn.close()
    return False

def get_due_reminders(reminders_db_path, current_time_utc_str):
    """Gets due reminders from the reminders database."""
    if not REMINDERS_DB_INITIALIZED_SUCCESSFULLY:
        logging.warning("Reminders DB not initialized. Cannot get due reminders.")
        return []
    conn = None
    try:
        conn = sqlite3.connect(reminders_db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT reminder_id, user_id, chat_id, reminder_text
            FROM reminders
            WHERE status = 'pending' AND due_time_utc <= ?
            ORDER BY due_time_utc ASC
        """, (current_time_utc_str,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"Error fetching due reminders from {reminders_db_path}: {e}")
        return []
    finally:
        if conn: conn.close()

def update_reminder_status(reminders_db_path, reminder_id, new_status):
    """Updates the status of a specific reminder in the reminders database."""
    if not REMINDERS_DB_INITIALIZED_SUCCESSFULLY:
        logging.error("Reminders DB not initialized. Cannot update reminder status.")
        return False
    conn = None
    retries = 3
    delay = 0.1
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(reminders_db_path, timeout=10)
            cur = conn.cursor()
            cur.execute("UPDATE reminders SET status = ? WHERE reminder_id = ?", (new_status, reminder_id))
            rowcount = cur.rowcount
            conn.commit()
            if rowcount > 0:
                logging.info(f"Successfully updated status for reminder {reminder_id} to '{new_status}' in {reminders_db_path}")
            else:
                 logging.warning(f"No reminder found with ID {reminder_id} to update status in {reminders_db_path}")
            return (rowcount > 0)
        except sqlite3.OperationalError as e:
             if "locked" in str(e).lower() and attempt < retries - 1:
                 logging.warning(f"Reminders DB locked during status update (Attempt {attempt+1}/{retries}). Retrying...")
                 if conn: conn.rollback()
                 time.sleep(delay * (attempt + 1))
             else:
                logging.error(f"Error updating status for reminder {reminder_id} after {retries} attempts: {e}")
                if conn: conn.rollback()
                return False
        except Exception as e:
            logging.error(f"Unexpected error updating status for reminder {reminder_id}: {e}")
            if conn: conn.rollback()
            return False
        finally:
            if conn: conn.close()
    return False

# # db_utils.py

# import sqlite3
# import logging
# import os
# import time
# from pathlib import Path
# from datetime import datetime, timedelta
# # --- Add import for timedelta ---
# from datetime import timedelta

# # --- Define DB_PATH by importing LOGS_DIR ---
# DB_PATH = None
# try:
#     from config_paths import LOGS_DIR
#     if LOGS_DIR and isinstance(LOGS_DIR, Path):
#         DB_FILENAME = 'usage_tracker.db'
#         DB_PATH = LOGS_DIR / DB_FILENAME
#         try:
#             LOGS_DIR.mkdir(parents=True, exist_ok=True)
#             logging.info(f"SQLite database path set to: {DB_PATH}")
#         except OSError as e:
#              logging.error(f"Failed to ensure logs directory exists at {LOGS_DIR}: {e}")
#              DB_PATH = None
#     else:
#         logging.critical("LOGS_DIR imported from config_paths is invalid.")
#         DB_PATH = None
# except ImportError:
#     logging.critical("Could not import LOGS_DIR from config_paths.py.")
#     DB_PATH = None
# except Exception as e:
#      logging.critical(f"Unexpected error setting DB_PATH: {e}")
#      DB_PATH = None
# # --- End DB_PATH Definition ---

# def _create_db_if_not_exists(db_path):
#     if not db_path: return False
#     conn = None
#     try:
#         conn = sqlite3.connect(db_path, timeout=10)
#         cursor = conn.cursor()
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS daily_usage (
#                 usage_date TEXT PRIMARY KEY,
#                 premium_tokens INTEGER DEFAULT 0,
#                 mini_tokens INTEGER DEFAULT 0
#             );
#         """)
#         cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_date ON daily_usage (usage_date);")
#         conn.commit()
#         logging.info(f"Ensured SQLite table 'daily_usage' exists in {db_path}")
#         return True
#     except Exception as e:
#         logging.error(f"Failed to create or verify SQLite table in {db_path}: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# DB_INITIALIZED_SUCCESSFULLY = False
# if DB_PATH:
#     DB_INITIALIZED_SUCCESSFULLY = _create_db_if_not_exists(DB_PATH)
# else:
#     logging.error("Database path could not be determined. SQLite functions will be disabled.")

# def _get_daily_usage_sync(db_path, usage_date_str):
#     """
#     Retrieves the token usage for a specific date.
#     Returns tuple (premium_tokens, mini_tokens) on success,
#     or None if DB is not initialized or any error occurs.
#     """
#     if not DB_INITIALIZED_SUCCESSFULLY:
#         logging.warning("SQLite DB not initialized. Cannot get usage.")
#         return None # Indicate failure clearly
#     conn = None
#     try:
#         conn = sqlite3.connect(db_path, timeout=10)
#         cursor = conn.cursor()
#         cursor.execute("SELECT premium_tokens, mini_tokens FROM daily_usage WHERE usage_date = ?", (usage_date_str,))
#         row = cursor.fetchone()
#         if row:
#             premium = row[0] if row[0] is not None else 0
#             mini = row[1] if row[1] is not None else 0
#             return premium, mini
#         else:
#             # No record found for today, which is valid, return 0,0
#             return 0, 0
#     except sqlite3.OperationalError as e:
#         logging.error(f"SQLite DB locked or error during read for date {usage_date_str}: {e}")
#         return None # Indicate failure
#     except Exception as e:
#         logging.error(f"Error getting daily usage from SQLite ({db_path}) for date {usage_date_str}: {e}")
#         return None # Indicate failure
#     finally:
#         if conn:
#             conn.close()

# def _update_daily_usage_sync(db_path, usage_date_str, model_tier, tokens_used):
#     """
#     Adds tokens used to the appropriate counter for the given date.
#     Handles concurrent access with retries. Does nothing if DB isn't initialized.
#     """
#     if not DB_INITIALIZED_SUCCESSFULLY:
#         logging.warning("SQLite DB not initialized. Cannot update usage.")
#         return
#     if tokens_used <= 0: return

#     conn = None
#     retries = 5
#     delay = 0.2

#     for attempt in range(retries):
#         try:
#             conn = sqlite3.connect(db_path, timeout=10)
#             cursor = conn.cursor()
#             cursor.execute("INSERT OR IGNORE INTO daily_usage (usage_date, premium_tokens, mini_tokens) VALUES (?, 0, 0)", (usage_date_str,))

#             if model_tier == 'premium':
#                 column_to_update = 'premium_tokens'
#             elif model_tier == 'mini':
#                 column_to_update = 'mini_tokens'
#             else:
#                  logging.warning(f"Unknown model tier '{model_tier}' provided for usage update. Cannot log.")
#                  return

#             sql = f"UPDATE daily_usage SET {column_to_update} = {column_to_update} + ? WHERE usage_date = ?"
#             cursor.execute(sql, (tokens_used, usage_date_str))
#             conn.commit()
#             return # Success

#         except sqlite3.OperationalError as e:
#              if "locked" in str(e).lower() and attempt < retries - 1:
#                  logging.warning(f"SQLite DB locked during write (Attempt {attempt+1}/{retries}). Retrying in {delay:.2f}s...")
#                  time.sleep(delay)
#                  delay = min(delay * 1.5, 2.0)
#              else:
#                  logging.error(f"SQLite DB locked or error during write for {usage_date_str} after {retries} attempts: {e}")
#                  if conn: conn.rollback()
#                  break
#         except Exception as e:
#             logging.error(f"Unexpected error updating daily usage in SQLite ({db_path}) for {usage_date_str}: {e}")
#             if conn: conn.rollback()
#             break
#         finally:
#             if conn:
#                 conn.close()
#     logging.error(f"Failed to update usage for {usage_date_str}, tier {model_tier}, tokens {tokens_used} after {retries} attempts.")


# def _cleanup_old_usage_sync(db_path, max_history_days):
#     """Deletes usage records older than max_history_days."""
#     if not DB_INITIALIZED_SUCCESSFULLY:
#         logging.warning("SQLite DB not initialized. Cannot cleanup old usage.")
#         return
#     conn = None
#     try:
#         conn = sqlite3.connect(db_path, timeout=10)
#         cursor = conn.cursor()
#         cutoff_date_dt = datetime.utcnow() - timedelta(days=max_history_days)
#         cutoff_date_str = cutoff_date_dt.strftime('%Y-%m-%d')
#         cursor.execute("DELETE FROM daily_usage WHERE usage_date < ?", (cutoff_date_str,))
#         deleted_count = cursor.rowcount
#         conn.commit()
#         if deleted_count > 0:
#             logging.info(f"SQLite Cleanup: Deleted {deleted_count} usage records older than {cutoff_date_str}.")
#     except sqlite3.OperationalError as e:
#         logging.error(f"SQLite DB locked or error during cleanup: {e}")
#     except Exception as e:
#         logging.error(f"Error cleaning up old usage in SQLite ({db_path}): {e}")
#     finally:
#         if conn:
#             conn.close()

# # reminders sqlite table
# def _create_reminders_table(db_path):
#     conn = None
#     try:
#         conn = sqlite3.connect(db_path, timeout=10)
#         cursor = conn.cursor()
#         # Basic schema for reminders
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS reminders (
#                 reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 user_id INTEGER NOT NULL,
#                 chat_id INTEGER NOT NULL,
#                 reminder_text TEXT NOT NULL,
#                 due_time_utc TEXT NOT NULL,
#                 status TEXT NOT NULL DEFAULT 'pending',
#                 created_at TEXT NOT NULL
#             );
#         """)
#         cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminder_due_time ON reminders (due_time_utc);")
#         conn.commit()
#     except Exception as e:
#         logging.error(f"Failed to create or verify 'reminders' table: {e}")
#     finally:
#         if conn:
#             conn.close()

# # reminders handling
# def add_reminder_to_db(db_path, user_id, chat_id, reminder_text, due_time_utc_str):
#     if not db_path:
#         return None

#     try:
#         conn = sqlite3.connect(db_path, timeout=10)
#         cur = conn.cursor()

#         # Insert the new reminder
#         created_at_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
#         cur.execute("""
#             INSERT INTO reminders (user_id, chat_id, reminder_text, due_time_utc, created_at)
#             VALUES (?, ?, ?, ?, ?)
#         """, (user_id, chat_id, reminder_text, due_time_utc_str, created_at_str))

#         reminder_id = cur.lastrowid
#         conn.commit()
#         return reminder_id
#     except Exception as e:
#         logging.error(f"Error adding reminder for user {user_id}: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def count_pending_reminders_for_user(db_path, user_id):
#     if not db_path:
#         return 0
#     try:
#         conn = sqlite3.connect(db_path, timeout=10)
#         cur = conn.cursor()
#         cur.execute("""
#             SELECT COUNT(*)
#             FROM reminders
#             WHERE user_id = ? AND status = 'pending'
#         """, (user_id,))
#         count_val = cur.fetchone()[0]
#         return count_val
#     except Exception as e:
#         logging.error(f"Error counting reminders for user {user_id}: {e}")
#         return 0
#     finally:
#         if conn:
#             conn.close()

# def get_pending_reminders_for_user(db_path, user_id):
#     if not db_path:
#         return []
#     try:
#         conn = sqlite3.connect(db_path, timeout=10)
#         cur = conn.cursor()
#         cur.execute("""
#             SELECT reminder_id, reminder_text, due_time_utc
#             FROM reminders
#             WHERE user_id = ? AND status = 'pending'
#             ORDER BY due_time_utc ASC
#         """, (user_id,))
#         rows = cur.fetchall()
#         reminders = []
#         for r in rows:
#             reminders.append({
#                 "reminder_id": r[0],
#                 "reminder_text": r[1],
#                 "due_time_utc": r[2]
#             })
#         return reminders
#     except Exception as e:
#         logging.error(f"Error fetching reminders for user {user_id}: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def delete_reminder_from_db(db_path, reminder_id, user_id):
#     """Return True if deleted, False if no match or error."""
#     if not db_path:
#         return False
#     try:
#         conn = sqlite3.connect(db_path, timeout=10)
#         cur = conn.cursor()
#         cur.execute("""
#             DELETE FROM reminders
#             WHERE reminder_id = ? AND user_id = ?
#         """, (reminder_id, user_id))
#         rowcount = cur.rowcount
#         conn.commit()
#         return (rowcount > 0)
#     except Exception as e:
#         logging.error(f"Error deleting reminder {reminder_id} for user {user_id}: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def get_due_reminders(db_path):
#     """Fetch all reminders with status='pending' whose due_time_utc <= now (UTC)."""
#     if not db_path:
#         return []
#     try:
#         conn = sqlite3.connect(db_path, timeout=10)
#         cur = conn.cursor()
#         now_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
#         cur.execute("""
#             SELECT reminder_id, user_id, chat_id, reminder_text
#             FROM reminders
#             WHERE status='pending'
#               AND due_time_utc <= ?
#             ORDER BY due_time_utc ASC
#         """, (now_str,))
#         rows = cur.fetchall()
#         reminders = []
#         for r in rows:
#             reminders.append({
#                 "reminder_id": r[0],
#                 "user_id": r[1],
#                 "chat_id": r[2],
#                 "reminder_text": r[3]
#             })
#         return reminders
#     except Exception as e:
#         logging.error(f"Error fetching due reminders: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def mark_reminder_as_sent(db_path, reminder_id):
#     """Mark the given reminder as 'sent' so we don't deliver it again."""
#     if not db_path:
#         return False
#     try:
#         conn = sqlite3.connect(db_path, timeout=10)
#         cur = conn.cursor()
#         cur.execute("""
#             UPDATE reminders
#             SET status='sent'
#             WHERE reminder_id=?
#         """, (reminder_id,))
#         conn.commit()
#         return True
#     except Exception as e:
#         logging.error(f"Error marking reminder {reminder_id} as sent: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()
