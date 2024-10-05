# api_key.py
# Read the OPENAI API key with configurable fallback

import os
import sys
import configparser
import logging
from config_paths import CONFIG_PATH, API_TOKEN_PATH # Import the centralized CONFIG_PATH

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flag to enable or disable fallback to environment variable if the key is not found in the file
ENABLE_KEY_READING_FALLBACK = True

def read_env_api_key():
    """
    Reads the OpenAI API key from the environment variable.

    Returns:
        str: The API key if found, else None.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        logging.info("OpenAI API key loaded from environment variable.")
    return api_key

def get_api_key(config_path=CONFIG_PATH, token_file=API_TOKEN_PATH):
    """
    Retrieves the OpenAI API key, prioritizing the method as per the config file or defaults.

    Args:
        config_path (str): Path to the configuration file.
        token_file (str): Path to the file containing the API key.

    Returns:
        str: The OpenAI API key.

    Raises:
        SystemExit: If the API key is not found through any method.
    """
    config = configparser.ConfigParser()
    api_key = None

    try:
        config.read(config_path)
        if not config.sections():
            logging.warning(f"Config file '{config_path}' is missing or empty. OpenAI API key reading falling back to environment variable preference.")
            prefer_env = True  # Defaulting to True if config read fails
        else:
            prefer_env = config.getboolean('DEFAULT', 'PreferEnvForAPIKey', fallback=True)
            logging.info(f"Preference for environment variables for the OpenAI API key set in config: {'Yes' if prefer_env else 'No'}")
    except Exception as e:
        logging.error(f"Failed to read OpenAI API key from config file: {e}")
        prefer_env = True  # Defaulting to True if config read fails
        logging.info("Defaulting to environment variable preference due to config read failure.")

    if prefer_env:
        api_key = read_env_api_key()
        if api_key:
            return api_key.strip()

    if not api_key:
        try:
            with open(token_file, 'r') as file:
                api_key = file.read().strip()
                if api_key:
                    logging.info("OpenAI API key loaded from file.")
                    return api_key
        except FileNotFoundError:
            logging.warning("OpenAI API token file not found.")
            if not prefer_env and ENABLE_KEY_READING_FALLBACK:
                api_key = read_env_api_key()
                if api_key:
                    return api_key.strip()

    if not api_key:
        logging.error("The OPENAI_API_KEY environment variable is not set, and `api_token.txt` was not found. Please set either one and adjust `config.ini` if needed for the preferred load order.")
        sys.exit(1)

# Example usage for standalone testing
if __name__ == "__main__":
    api_key = get_api_key()
    print("OpenAI API Key (for testing & debugging only):", api_key)

# ~~~ old method below ~~~
# import os
# import sys
# import configparser

# # set `prefer_env` to `True` if you wish to prioritize the environment variable over the configuration text file
# # (determines load order)
# def get_api_key():
#     config = configparser.ConfigParser()
#     config.read('config.ini')
#     prefer_env = config.getboolean('DEFAULT', 'PreferEnvForAPIKey', fallback=True)

#     if prefer_env:
#         api_key = os.getenv('OPENAI_API_KEY')
#         if api_key is not None:
#             return api_key

#     try:
#         with open('api_token.txt', 'r') as file:
#             return file.read().strip()
#     except FileNotFoundError:
#         if not prefer_env:
#             api_key = os.getenv('OPENAI_API_KEY')
#             if api_key is not None:
#                 return api_key

#         print("The OPENAI_API_KEY environment variable is not set, and `api_token.txt` was not found. Please set either one and adjust `config.ini` if needed for the preferred load order.")
#         sys.exit(1)
