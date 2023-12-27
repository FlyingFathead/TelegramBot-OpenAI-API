# ~~~ read the openai api key ~~~

import os

def get_api_key():
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key is None:
        try:
            with open('api_token.txt', 'r') as file:
                api_key = file.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError("The OPENAI_API_KEY environment variable is not set, and api_token.txt was not found.")
    return api_key