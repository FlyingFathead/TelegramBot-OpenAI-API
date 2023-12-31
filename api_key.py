# ~~~ read the OpenAI API key ~~~
import os
import sys

# set `prefer_env` to `True` if you wish to prioritize the environment variable over the configuration text file (determines load order)
def get_api_key(prefer_env=True):
    if prefer_env:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key is not None:
            return api_key

    try:
        with open('api_token.txt', 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        if not prefer_env:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key is not None:
                return api_key

        print("The OPENAI_API_KEY environment variable is not set, and `api_token.txt` was not found.")
        sys.exit(1)
        