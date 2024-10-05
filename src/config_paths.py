# config_paths.py
import os
from pathlib import Path
import configparser

# Define the base directory (the parent of the 'src' directory)
BASE_DIR = Path(__file__).resolve().parents[1]

# Read configuration to get the logs directory
CONFIG_PATH = BASE_DIR / 'config' / 'config.ini'
config = configparser.ConfigParser()
config.read(CONFIG_PATH)
logs_directory = config['DEFAULT'].get('LogsDirectory', 'logs')

# Define the logs directory path
LOGS_DIR = BASE_DIR / logs_directory

# Ensure the logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Define paths for log files and token usage file
LOG_FILE_PATH = LOGS_DIR / config['DEFAULT'].get('LogFile', 'bot.log')
CHAT_LOG_FILE_PATH = LOGS_DIR / config['DEFAULT'].get('ChatLogFile', 'chat.log')
TOKEN_USAGE_FILE_PATH = LOGS_DIR / 'token_usage.json'

# Define ChatLogMaxSizeMB and convert it to bytes
ChatLogMaxSizeMB = config['DEFAULT'].getint('ChatLogMaxSizeMB', fallback=10)  # Default to 10 MB if not set
CHAT_LOG_MAX_SIZE = ChatLogMaxSizeMB * 1024 * 1024  # Convert MB to bytes

# Other paths remain the same
TOKEN_FILE_PATH = BASE_DIR / 'config' / 'bot_token.txt'
API_TOKEN_PATH = BASE_DIR / 'config' / 'api_token.txt'
