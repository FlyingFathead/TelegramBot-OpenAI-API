# config_paths.py
# setting up the config paths

import os
from pathlib import Path

# Define paths early for global use
# BASE_DIR = Path(__file__).resolve().parents[2]
BASE_DIR = Path(os.getcwd())  # This points to the current working directory
CONFIG_PATH = BASE_DIR / 'config' / 'config.ini'
TOKEN_FILE_PATH = BASE_DIR / 'config' / 'bot_token.txt'
