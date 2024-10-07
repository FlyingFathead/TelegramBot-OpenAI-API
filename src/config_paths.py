# config_paths.py

import os
from pathlib import Path
import configparser
import logging

# Initialize the logger for this module
logger = logging.getLogger('TelegramBotLogger')  # Ensure that 'TelegramBotLogger' is initialized in main.py

# Define the base directory (the parent of the 'src' directory)
BASE_DIR = Path(__file__).resolve().parents[1]

# Path to the configuration file
CONFIG_PATH = BASE_DIR / 'config' / 'config.ini'

# Initialize the ConfigParser
config = configparser.ConfigParser()

# Initialize variables with default values
logs_directory = 'logs'
LOG_FILE_PATH = BASE_DIR / logs_directory / 'bot.log'
CHAT_LOG_FILE_PATH = BASE_DIR / logs_directory / 'chat.log'
TOKEN_USAGE_FILE_PATH = BASE_DIR / logs_directory / 'token_usage.json'
CHAT_LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
ELASTICSEARCH_ENABLED = False
ELASTICSEARCH_HOST = 'localhost'
ELASTICSEARCH_PORT = 9200
ELASTICSEARCH_USERNAME = ''
ELASTICSEARCH_PASSWORD = ''

# Default NWS settings
NWS_USER_AGENT = 'ChatKekeWeather/1.0 (flyingfathead@protonmail.com)'
NWS_RETRIES = 0
NWS_RETRY_DELAY = 2

# Attempt to read the configuration file
if CONFIG_PATH.exists():
    try:
        config.read(CONFIG_PATH)
        logger.info(f"Configuration file found and loaded from {CONFIG_PATH}.")
        
        # Read logs directory
        logs_directory = config['DEFAULT'].get('LogsDirectory', 'logs')
        
        # Define the logs directory path
        LOGS_DIR = BASE_DIR / logs_directory
        
        # Ensure the logs directory exists
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Update log file paths
        LOG_FILE_PATH = LOGS_DIR / config['DEFAULT'].get('LogFile', 'bot.log')
        CHAT_LOG_FILE_PATH = LOGS_DIR / config['DEFAULT'].get('ChatLogFile', 'chat.log')
        TOKEN_USAGE_FILE_PATH = LOGS_DIR / 'token_usage.json'
        
        # Read ChatLogMaxSizeMB and convert to bytes
        ChatLogMaxSizeMB = config['DEFAULT'].getint('ChatLogMaxSizeMB', fallback=10)
        CHAT_LOG_MAX_SIZE = ChatLogMaxSizeMB * 1024 * 1024
        
        # Read Elasticsearch configurations
        if 'Elasticsearch' in config:
            ELASTICSEARCH_ENABLED = config['Elasticsearch'].getboolean('ElasticsearchEnabled', fallback=False)
            ELASTICSEARCH_HOST = config['Elasticsearch'].get('Host', fallback='localhost')
            ELASTICSEARCH_PORT = config['Elasticsearch'].getint('Port', fallback=9200)
            ELASTICSEARCH_SCHEME = config.get('Elasticsearch', 'ELASTICSEARCH_SCHEME', fallback='http')
            ELASTICSEARCH_USERNAME = config['Elasticsearch'].get('Username', fallback='')
            ELASTICSEARCH_PASSWORD = config['Elasticsearch'].get('Password', fallback='')
            logger.info(f"Elasticsearch Enabled: {ELASTICSEARCH_ENABLED}")
        else:
            # Elasticsearch section missing
            ELASTICSEARCH_ENABLED = False
            ELASTICSEARCH_HOST = 'localhost'
            ELASTICSEARCH_PORT = 9200
            ELASTICSEARCH_SCHEME = 'http'
            ELASTICSEARCH_USERNAME = ''
            ELASTICSEARCH_PASSWORD = ''
            logger.warning("Elasticsearch section missing in config.ini. Using default Elasticsearch settings.")
        
        # NWS Configuration
        if 'NWS' in config:
            NWS_USER_AGENT = config['NWS'].get('NWSUserAgent', fallback='ChatKekeWeather/1.0 (flyingfathead@protonmail.com)')
            NWS_RETRIES = config['NWS'].getint('NWSRetries', fallback=0)
            NWS_RETRY_DELAY = config['NWS'].getint('NWSRetryDelay', fallback=2)
            FETCH_NWS_FORECAST = config['NWS'].getboolean('FetchNWSForecast', fallback=True)
            FETCH_NWS_ALERTS = config['NWS'].getboolean('FetchNWSAlerts', fallback=True)
            logger.info(f"NWS Config: User-Agent={NWS_USER_AGENT}, Retries={NWS_RETRIES}, Retry Delay={NWS_RETRY_DELAY}, Fetch Forecast={FETCH_NWS_FORECAST}, Fetch Alerts={FETCH_NWS_ALERTS}")
        else:
            logger.warning("NWS section not found in config.ini. Using default NWS settings.")

    except Exception as e:
        # Handle exceptions during config parsing
        logger.error(f"Error reading configuration file: {e}")
else:
    # config.ini not found
    logger.warning(f"Configuration file NOT found at {CONFIG_PATH}. Using default settings. This is NOT a good idea!")
    # Ensure the logs directory exists
    LOGS_DIR = BASE_DIR / logs_directory
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    # Define log file paths
    LOG_FILE_PATH = LOGS_DIR / 'bot.log'
    CHAT_LOG_FILE_PATH = LOGS_DIR / 'chat.log'
    TOKEN_USAGE_FILE_PATH = LOGS_DIR / 'token_usage.json'
    # CHAT_LOG_MAX_SIZE already set to 10 MB
    # Elasticsearch settings already set to defaults

# Define paths for token files
TOKEN_FILE_PATH = BASE_DIR / 'config' / 'bot_token.txt'
API_TOKEN_PATH = BASE_DIR / 'config' / 'api_token.txt'
