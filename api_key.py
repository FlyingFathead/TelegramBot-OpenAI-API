# ~~~ read the OpenAI API key ~~~
import os
import sys

def get_api_key():
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key is None:
        try:
            with open('api_token.txt', 'r') as file:
                api_key = file.read().strip()
        except FileNotFoundError:
            print("The OPENAI_API_KEY environment variable is not set, and `api_token.txt` was not found. Please configure either the `OPENAI_API_KEY` environment variable, OR insert your OpenAI API key inside a text file in this directory named `api_token.txt`.")
            sys.exit(1)
    return api_key
