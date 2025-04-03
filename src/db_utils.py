# db_utils.py

import sqlite3
import logging
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
# --- Add import for timedelta ---
from datetime import timedelta

# --- Define DB_PATH by importing LOGS_DIR ---
DB_PATH = None
try:
    from config_paths import LOGS_DIR
    if LOGS_DIR and isinstance(LOGS_DIR, Path):
        DB_FILENAME = 'usage_tracker.db'
        DB_PATH = LOGS_DIR / DB_FILENAME
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            logging.info(f"SQLite database path set to: {DB_PATH}")
        except OSError as e:
             logging.error(f"Failed to ensure logs directory exists at {LOGS_DIR}: {e}")
             DB_PATH = None
    else:
        logging.critical("LOGS_DIR imported from config_paths is invalid.")
        DB_PATH = None
except ImportError:
    logging.critical("Could not import LOGS_DIR from config_paths.py.")
    DB_PATH = None
except Exception as e:
     logging.critical(f"Unexpected error setting DB_PATH: {e}")
     DB_PATH = None
# --- End DB_PATH Definition ---

def _create_db_if_not_exists(db_path):
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
        logging.error(f"Failed to create or verify SQLite table in {db_path}: {e}")
        return False
    finally:
        if conn: conn.close()

DB_INITIALIZED_SUCCESSFULLY = False
if DB_PATH:
    DB_INITIALIZED_SUCCESSFULLY = _create_db_if_not_exists(DB_PATH)
else:
    logging.error("Database path could not be determined. SQLite functions will be disabled.")

def _get_daily_usage_sync(db_path, usage_date_str):
    """
    Retrieves the token usage for a specific date.
    Returns tuple (premium_tokens, mini_tokens) on success,
    or None if DB is not initialized or any error occurs.
    """
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.warning("SQLite DB not initialized. Cannot get usage.")
        return None # Indicate failure clearly
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT premium_tokens, mini_tokens FROM daily_usage WHERE usage_date = ?", (usage_date_str,))
        row = cursor.fetchone()
        if row:
            premium = row[0] if row[0] is not None else 0
            mini = row[1] if row[1] is not None else 0
            return premium, mini
        else:
            # No record found for today, which is valid, return 0,0
            return 0, 0
    except sqlite3.OperationalError as e:
        logging.error(f"SQLite DB locked or error during read for date {usage_date_str}: {e}")
        return None # Indicate failure
    except Exception as e:
        logging.error(f"Error getting daily usage from SQLite ({db_path}) for date {usage_date_str}: {e}")
        return None # Indicate failure
    finally:
        if conn:
            conn.close()

def _update_daily_usage_sync(db_path, usage_date_str, model_tier, tokens_used):
    """
    Adds tokens used to the appropriate counter for the given date.
    Handles concurrent access with retries. Does nothing if DB isn't initialized.
    """
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.warning("SQLite DB not initialized. Cannot update usage.")
        return
    if tokens_used <= 0: return

    conn = None
    retries = 5
    delay = 0.2

    for attempt in range(retries):
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO daily_usage (usage_date, premium_tokens, mini_tokens) VALUES (?, 0, 0)", (usage_date_str,))

            if model_tier == 'premium':
                column_to_update = 'premium_tokens'
            elif model_tier == 'mini':
                column_to_update = 'mini_tokens'
            else:
                 logging.warning(f"Unknown model tier '{model_tier}' provided for usage update. Cannot log.")
                 return

            sql = f"UPDATE daily_usage SET {column_to_update} = {column_to_update} + ? WHERE usage_date = ?"
            cursor.execute(sql, (tokens_used, usage_date_str))
            conn.commit()
            return # Success

        except sqlite3.OperationalError as e:
             if "locked" in str(e).lower() and attempt < retries - 1:
                 logging.warning(f"SQLite DB locked during write (Attempt {attempt+1}/{retries}). Retrying in {delay:.2f}s...")
                 time.sleep(delay)
                 delay = min(delay * 1.5, 2.0)
             else:
                 logging.error(f"SQLite DB locked or error during write for {usage_date_str} after {retries} attempts: {e}")
                 if conn: conn.rollback()
                 break
        except Exception as e:
            logging.error(f"Unexpected error updating daily usage in SQLite ({db_path}) for {usage_date_str}: {e}")
            if conn: conn.rollback()
            break
        finally:
            if conn:
                conn.close()
    logging.error(f"Failed to update usage for {usage_date_str}, tier {model_tier}, tokens {tokens_used} after {retries} attempts.")


def _cleanup_old_usage_sync(db_path, max_history_days):
    """Deletes usage records older than max_history_days."""
    if not DB_INITIALIZED_SUCCESSFULLY:
        logging.warning("SQLite DB not initialized. Cannot cleanup old usage.")
        return
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        cutoff_date_dt = datetime.utcnow() - timedelta(days=max_history_days)
        cutoff_date_str = cutoff_date_dt.strftime('%Y-%m-%d')
        cursor.execute("DELETE FROM daily_usage WHERE usage_date < ?", (cutoff_date_str,))
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            logging.info(f"SQLite Cleanup: Deleted {deleted_count} usage records older than {cutoff_date_str}.")
    except sqlite3.OperationalError as e:
        logging.error(f"SQLite DB locked or error during cleanup: {e}")
    except Exception as e:
        logging.error(f"Error cleaning up old usage in SQLite ({db_path}): {e}")
    finally:
        if conn:
            conn.close()
