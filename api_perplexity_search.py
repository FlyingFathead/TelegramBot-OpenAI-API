# api_perplexity_search.py

import re
import openai
import httpx
import logging
import os
import httpx
import asyncio

from langdetect import detect

# ~~~~~~~~~
# variables
# ~~~~~~~~~

# Global variable for chunk size
CHUNK_SIZE = 500  # Set this value as needed

# Assuming you've set PERPLEXITY_API_KEY in your environment variables
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# can be adjusted to any model
async def fact_check_with_perplexity(question: str):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "model": "pplx-7b-online",  # Specifying the pplx-70b-online model
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.0,  # Adjust based on how deterministic you want the responses to be
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise in your responses."
            },
            {
                "role": "user",
                "content": question
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Perplexity API Error: {response.text}")
        return None

# perplexity 70b query
async def query_pplx_70b_online(prompt):
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")  # Ensure this is securely set
    url = "https://api.perplexity.ai/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    data = {
        "model": "pplx-70b-online",  # Specifying the pplx-70b-online model
        "messages": [
            {"role": "system", "content": "You are a Discord helper bot. Answer accordingly."},
            {"role": "user", "content": prompt},
        ],
        # Include other parameters as necessary
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.text}")
        return None

# queries perplexity
async def query_perplexity(question: str):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "model": "pplx-7b-online",
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.0,  # Adjust as needed
        "messages": [
            {"role": "system", "content": "Be precise in your responses."},
            {"role": "user", "content": question}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        logging.info(f"Response type: {type(response.json())}, Content: {response.text}")

        if response.status_code == 200:
            response_data = response.json()  # Ensure we're parsing the JSON response

            # Properly extract the message content using .get()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                bot_reply_content = response_data['choices'][0].get('message', {}).get('content', "")
                return bot_reply_content.strip() if bot_reply_content else "Sorry, I couldn't fetch an answer for that. Please try again later."
            else:
                logging.error("Perplexity API returned an unexpected structure.")
                return "Unexpected response structure from Perplexity API."
        else:
            logging.error(f"Perplexity API Error: {response.text}")
            return None

# translate response; in one go
async def translate_response(bot, user_message, perplexity_response):
    # Log the Perplexity API response before translation
    logging.info(f"Perplexity API Response to be translated: {perplexity_response}")

    # Preprocess the user_message to remove known metadata patterns
    cleaned_message = re.sub(r"\[Whisper STT transcribed message from the user\]|\[end\]", "", user_message).strip()

    # Detect the language of the user's question
    try:
        user_lang = detect(cleaned_message)
        logging.info(f"Detected user language: {user_lang} -- user request: {user_message}")
    except Exception as e:
        logging.error(f"Error detecting user language: {e}")
        return perplexity_response  # Return original response if language detection fails

    # Check if the detected language is English, skip translation if it is
    if user_lang == 'en':
        logging.info("User's question is in English, skipping translation.")
        return perplexity_response
    else:
        # await context.bot.send_message(chat_id=update.effective_chat.id, text="<i>Translating, please wait...</i>", parse_mode=telegram.ParseMode.HTML)
        logging.info(f"User's question is in {user_lang}, proceeding with translation.")
    
    # System message to guide the model for translating
    system_message = {
        "role": "system",
        "content": f"Translate the message to: {user_lang}."
    }
    
    # Prepare the chat history with only the Perplexity's response as the assistant's message to be translated
    chat_history = [
        system_message,
        # {"role": "user", "content": user_message},
        {"role": "user", "content": perplexity_response}
    ]

    # Prepare the payload for the OpenAI API
    payload = {
        "model": bot.model,  # Specify the OpenAI model you're using for translating
        "messages": chat_history,
        "temperature": 0.5  # Adjust based on your preference for randomness in translation
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bot.openai_api_key}"  # Use the correct API key variable
    }

    # Make the API request to OpenAI
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.openai.com/v1/chat/completions",
                                     json=payload,
                                     headers=headers)

    # Process the response
    if response.status_code == 200:
        try:
            response_json = response.json()
            translated_reply = response_json['choices'][0]['message']['content'].strip()
            logging.info(f"Translated response: {translated_reply}")
            return translated_reply
        except Exception as e:
            logging.error(f"Error processing translation response: {e}")
            return f"Translation failed due to an error: {e}"  
    else:
        logging.error(f"Error in translating response: {response.text}")
        return f"Failed to translate, API returned status code {response.status_code}: {response.text}"

# translate in chunks
async def translate_response_chunked(bot, user_message, perplexity_response):
    logging.info(f"Perplexity API Response to be translated: {perplexity_response}")

    # Clean the user_message as before
    cleaned_message = re.sub(r"\[Whisper STT transcribed message from the user\]|\[end\]", "", user_message).strip()

    try:
        user_lang = detect(cleaned_message)
        logging.info(f"Detected user language: {user_lang} -- user request: {user_message}")
    except Exception as e:
        logging.error(f"Error detecting user language: {e}")
        return perplexity_response

    # Skip translation if the language is English
    if user_lang == 'en':
        logging.info("User's question is in English, skipping translation.")
        return perplexity_response

    # Use smart_chunk to split the response text
    chunks = smart_chunk(perplexity_response)

    translated_chunks = []

    for chunk in chunks:
        logging.info(f"Translating chunk: {chunk}")
        # Prepare the payload for each chunk
        payload = {
            "model": bot.model,
            "messages": [
                {"role": "system", "content": f"Translate the message to: {user_lang}."},
                {"role": "user", "content": chunk}
            ],
            "temperature": 0.5  # Keep as per your requirement
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bot.openai_api_key}"
        }

        # Translate each chunk
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)

        if response.status_code == 200:
            try:
                response_json = response.json()
                translated_chunk = response_json['choices'][0]['message']['content'].strip()
                translated_chunks.append(translated_chunk)
            except Exception as e:
                logging.error(f"Error processing translation response for a chunk: {e}")
                # Handle partial translation or decide to abort/return error based on your preference
        else:
            logging.error(f"Error in translating chunk: {response.text}")
            # Handle error, e.g., by breaking the loop or accumulating errors

    # Combine translated chunks
    translated_response = " ".join(translated_chunks)
    return translated_response

# Adjusted smart_chunk method to use the global CHUNK_SIZE
def smart_chunk(text):
    global CHUNK_SIZE
    chunks = []
    start_index = 0

    while start_index < len(text):
        # Check if remaining text is shorter than CHUNK_SIZE
        if len(text) - start_index <= CHUNK_SIZE:
            chunks.append(text[start_index:].strip())
            break
        else:
            # Find the nearest newline within CHUNK_SIZE
            split_pos = text.rfind('\n', start_index, start_index + CHUNK_SIZE)
            if split_pos == -1 or split_pos < start_index:
                # If no newline is found, fallback to space or period, then to CHUNK_SIZE
                split_pos = max(
                    text.rfind('. ', start_index, start_index + CHUNK_SIZE),
                    text.rfind(' ', start_index, start_index + CHUNK_SIZE),
                    start_index + CHUNK_SIZE - 1
                )

            chunks.append(text[start_index:split_pos + 1].strip())
            start_index = split_pos + 1

    return chunks

# ~~~~~~~~~~~~
# alternatives
# ~~~~~~~~~~~~
""" # translate perplexity replies // no language detection
async def translate_response(bot, user_message, perplexity_response):
    # Log the Perplexity API response before translation
    logging.info(f"Perplexity API Response to be translated: {perplexity_response}")

    # System message to guide the model for translating
    system_message = {
        "role": "system",
        "content": "Translate the provided assistant response to the language that the user's question was in, otherwise pass it as-is. Example: if user asked their question in Finnish, translate the provided reply text to Finnish, otherwise pass it back to the user as it is."
    }

    # Prepare the chat history with only the Perplexity's response as the assistant's message to be translated
    chat_history = [
        system_message,
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": perplexity_response}
    ]

    # Prepare the payload for the OpenAI API
    payload = {
        "model": bot.model,  # Specify the OpenAI model you're using for translating
        "messages": chat_history,
        "temperature": 0.5  # Adjust based on your preference for randomness in translation
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bot.openai_api_key}"  # Use the correct API key variable
    }

    # Make the API request to OpenAI
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.openai.com/v1/chat/completions",
                                     json=payload,
                                     headers=headers)

    # Process the response
    if response.status_code == 200:
        try:
            response_json = response.json()
            translated_reply = response_json['choices'][0]['message']['content'].strip()
            logging.info(f"Translated response: {translated_reply}")
            return translated_reply
        except Exception as e:
            logging.error(f"Error processing translation response: {e}")
            return f"Translation failed due to an error: {e}"  
    else:
        logging.error(f"Error in translating response: {response.text}")
        return f"Failed to translate, API returned status code {response.status_code}: {response.text}" """