# api_key.py
# Read the OPENAI API key with configurable fallback

import os
import sys
import configparser
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flag to enable or disable fallback to environment variable if the key is not found in the file
ENABLE_KEY_READING_FALLBACK = True

def get_api_key():
    config = configparser.ConfigParser()
    config_path = 'config.ini'
    api_key = None

    try:
        config.read(config_path)
        prefer_env = config.getboolean('DEFAULT', 'PreferEnvForAPIKey', fallback=True)
    except Exception as e:
        logging.error(f"Failed to read from config file: {e}")
        prefer_env = True  # Defaulting to True if config read fails
        logging.info("Defaulting to environment variable preference due to config read failure.")

    logging.info(f"Preference for environment variables: {'Yes' if prefer_env else 'No'}")

    if prefer_env:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            logging.info("API key loaded from environment variable.")
            return api_key.strip()

    if not api_key:
        try:
            with open('api_token.txt', 'r') as file:
                api_key = file.read().strip()
                if api_key:
                    logging.info("API key loaded from file.")
                    return api_key
        except FileNotFoundError:
            logging.warning("API token file not found.")
            if not prefer_env and ENABLE_KEY_READING_FALLBACK:
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    logging.info("API key loaded from environment variable on fallback.")
                    return api_key.strip()

    if not api_key:
        logging.error("The OPENAI_API_KEY environment variable is not set, and `api_token.txt` was not found. Please set either one and adjust `config.ini` if needed for the preferred load order.")
        sys.exit(1)

# Example usage
if __name__ == "__main__":
    api_key = get_api_key()
    print("API Key:", api_key)

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
