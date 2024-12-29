# # # api_perplexity_search.py
# # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # # https://github.com/FlyingFathead/TelegramBot-OpenAI-API/
# # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import re
import openai
import httpx
import logging
import os
import asyncio
import configparser
import random
from config_paths import CONFIG_PATH

# Load the configuration file
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

# Perplexity API model to use -- NOTE: the models keep on changing; latest list is at: https://docs.perplexity.ai/guides/model-cards
# As of December 2024/January 2025, the latest model is in the llama-3.1 family, i.e.: "llama-3.1-sonar-large-128k-online" (can be small/large/huge)
DEFAULT_PERPLEXITY_MODEL = "llama-3.1-sonar-large-128k-online"
DEFAULT_PERPLEXITY_MAX_TOKENS = 1024
DEFAULT_PERPLEXITY_TEMPERATURE = 0.0
DEFAULT_PERPLEXITY_MAX_RETRIES = 3
DEFAULT_PERPLEXITY_RETRY_DELAY = 25
DEFAULT_PERPLEXITY_TIMEOUT = 30
DEFAULT_CHUNK_SIZE = 1000
PERPLEXITY_MODEL = config.get('Perplexity', 'Model', fallback=DEFAULT_PERPLEXITY_MODEL)
PERPLEXITY_MAX_TOKENS = config.getint('Perplexity', 'MaxTokens', fallback=DEFAULT_PERPLEXITY_MAX_TOKENS)
PERPLEXITY_TEMPERATURE = config.getfloat('Perplexity', 'Temperature', fallback=DEFAULT_PERPLEXITY_TEMPERATURE)
PERPLEXITY_MAX_RETRIES = config.getint('Perplexity', 'MaxRetries', fallback=DEFAULT_PERPLEXITY_MAX_RETRIES)
PERPLEXITY_RETRY_DELAY = config.getint('Perplexity', 'RetryDelay', fallback=DEFAULT_PERPLEXITY_RETRY_DELAY)
PERPLEXITY_TIMEOUT = config.getint('Perplexity', 'Timeout', fallback=DEFAULT_PERPLEXITY_TIMEOUT)
CHUNK_SIZE = config.getint('Perplexity', 'ChunkSize', fallback=DEFAULT_CHUNK_SIZE)
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
MAX_TELEGRAM_MESSAGE_LENGTH = 4000

async def fact_check_with_perplexity(question: str):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        "model": PERPLEXITY_MODEL,
        "stream": False,
        "max_tokens": PERPLEXITY_MAX_TOKENS,
        "temperature": PERPLEXITY_TEMPERATURE,
        "messages": [{"role": "user", "content": question}]
    }

    async with httpx.AsyncClient(timeout=PERPLEXITY_TIMEOUT) as client:
        for attempt in range(PERPLEXITY_MAX_RETRIES):
            try:
                response = await client.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 500:
                    logging.error("Perplexity API returned a 500 server error.")
                    return {"error": "server_error"}
                else:
                    logging.error(f"Perplexity API Error: {response.text}")
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logging.error(f"Error while calling Perplexity API: {e}")

            backoff_delay = min(PERPLEXITY_RETRY_DELAY, (2 ** attempt) + random.uniform(0, 1))
            await asyncio.sleep(backoff_delay)

    return None

async def query_perplexity(bot, chat_id, question: str):
    logging.info(f"Querying Perplexity with question: {question}")
    response_data = await fact_check_with_perplexity(question)

    if response_data and 'choices' in response_data:
        bot_reply_content = response_data['choices'][0].get('message', {}).get('content', "").strip()
        if bot_reply_content:
            return bot_reply_content
        else:
            logging.warning("Processed content is empty after stripping.")
            return "Received an empty response, please try again."
    elif response_data and response_data.get('error') == 'server_error':
        logging.error("Perplexity API server error.")
        return "Perplexity API is currently unavailable due to server issues. Please try again later."
    else:
        logging.error("Unexpected response structure from Perplexity API.")
        return "Error interpreting the response."

# <<< pre v0.737 code below >>>

# # # api_perplexity_search.py
# # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # # https://github.com/FlyingFathead/TelegramBot-OpenAI-API/
# # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# import re
# import openai
# import httpx
# import logging
# import os
# import asyncio
# import configparser
# import random
# from langdetect import detect
# from telegram import constants

# # Load the configuration file
# config = configparser.ConfigParser()
# config.read('config.ini')

# # ~~~~~~~~~
# # Variables
# # ~~~~~~~~~
# DEFAULT_PERPLEXITY_MODEL = "llama-3-sonar-large-32k-online"
# DEFAULT_PERPLEXITY_MAX_TOKENS = 1024
# DEFAULT_PERPLEXITY_TEMPERATURE = 0.0
# DEFAULT_PERPLEXITY_MAX_RETRIES = 3
# DEFAULT_PERPLEXITY_RETRY_DELAY = 25
# DEFAULT_PERPLEXITY_TIMEOUT = 30
# DEFAULT_CHUNK_SIZE = 1000
# PERPLEXITY_MODEL = config.get('Perplexity', 'Model', fallback=DEFAULT_PERPLEXITY_MODEL)
# PERPLEXITY_MAX_TOKENS = config.getint('Perplexity', 'MaxTokens', fallback=DEFAULT_PERPLEXITY_MAX_TOKENS)
# PERPLEXITY_TEMPERATURE = config.getfloat('Perplexity', 'Temperature', fallback=DEFAULT_PERPLEXITY_TEMPERATURE)
# PERPLEXITY_MAX_RETRIES = config.getint('Perplexity', 'MaxRetries', fallback=DEFAULT_PERPLEXITY_MAX_RETRIES)
# PERPLEXITY_RETRY_DELAY = config.getint('Perplexity', 'RetryDelay', fallback=DEFAULT_PERPLEXITY_RETRY_DELAY)
# PERPLEXITY_TIMEOUT = config.getint('Perplexity', 'Timeout', fallback=DEFAULT_PERPLEXITY_TIMEOUT)
# CHUNK_SIZE = config.getint('Perplexity', 'ChunkSize', fallback=DEFAULT_CHUNK_SIZE)
# PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
# MAX_TELEGRAM_MESSAGE_LENGTH = 4000

# async def fact_check_with_perplexity(question: str):
#     url = "https://api.perplexity.ai/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
#         "Content-Type": "application/json",
#         "Accept": "application/json",
#     }
#     data = {
#         "model": PERPLEXITY_MODEL,
#         "stream": False,
#         "max_tokens": PERPLEXITY_MAX_TOKENS,
#         "temperature": PERPLEXITY_TEMPERATURE,
#         "messages": [{"role": "user", "content": question}]
#     }

#     async with httpx.AsyncClient(timeout=PERPLEXITY_TIMEOUT) as client:
#         for attempt in range(PERPLEXITY_MAX_RETRIES):
#             try:
#                 response = await client.post(url, json=data, headers=headers)
#                 if response.status_code == 200:
#                     return response.json()
#                 elif response.status_code == 500:
#                     logging.error("Perplexity API returned a 500 server error.")
#                     return {"error": "server_error"}
#                 elif response.status_code in [502, 503, 504]:
#                     logging.error(f"Perplexity API Error: {response.text}")
#                 else:
#                     logging.error(f"Perplexity API Error: {response.text}")
#                     break
#             except httpx.RequestError as e:
#                 logging.error(f"RequestError while calling Perplexity API: {e}")
#             except httpx.HTTPStatusError as e:
#                 logging.error(f"HTTPStatusError while calling Perplexity API: {e}")
#             except Exception as e:
#                 logging.error(f"Unexpected error while calling Perplexity API: {e}")

#             backoff_delay = min(PERPLEXITY_RETRY_DELAY, (2 ** attempt) + random.uniform(0, 1))
#             await asyncio.sleep(backoff_delay)

#     return None

# async def query_perplexity(bot, chat_id, question: str):
#     logging.info(f"Querying Perplexity with question: {question}")
#     response_data = await fact_check_with_perplexity(question)

#     if response_data:
#         if 'choices' in response_data and len(response_data['choices']) > 0:
#             bot_reply_content = response_data['choices'][0].get('message', {}).get('content', "")
#             if bot_reply_content:
#                 final_message = bot_reply_content.strip()
#                 if final_message:
#                     return final_message
#                 else:
#                     logging.warning("Processed content is empty after stripping.")
#                     return "Received an empty response, please try again."
#             else:
#                 logging.warning("No content received from Perplexity API.")
#                 return "No answer received."
#         elif 'error' in response_data and response_data['error'] == 'server_error':
#             logging.error("Perplexity API server error.")
#             return "[System message: Perplexity API is currently unavailable due to server issues. Please try again later.]"
#         else:
#             logging.error("Unexpected response structure from Perplexity API.")
#             return "Error interpreting the response."
#     else:
#         return "API error encountered."

# async def translate_response_chunked(bot, user_message, openai_response, context, update):
#     logging.info(f"OpenAI API Response to be translated: {openai_response}")

#     try:
#         user_lang = await detect_language(bot, user_message)
#         logging.info(f"Detected user language: {user_lang} -- user request: {user_message}")
#     except Exception as e:
#         logging.error(f"Error detecting user language: {e}")
#         formatted_response = format_headers_for_telegram(openai_response)
#         await handle_long_response(context, update.effective_message.chat_id, markdown_to_html(formatted_response))
#         return True

#     if user_lang == 'en':
#         logging.info("User's question is in English, skipping translation, converting Markdown to HTML.")
#         sanitized_response = sanitize_urls(openai_response)
#         formatted_response = format_headers_for_telegram(sanitized_response)
#         html_response = markdown_to_html(formatted_response)
#         logging.info(f"Parsed translated response: {html_response}")

#         if not html_response.strip():
#             logging.warning("Attempted to send an empty response. Skipping.")
#             return True

#         await handle_long_response(context, update.effective_message.chat_id, html_response)
#         logging.info("Response sent successfully, no further actions should be triggered.")
#         return True

#     await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

#     chunks = smart_chunk(openai_response)
#     logging.info(f"Total chunks created: {len(chunks)}")
#     translated_chunks = []

#     for index, chunk in enumerate(chunks):
#         logging.info(f"Translating chunk {index+1}/{len(chunks)}: {chunk}")

#         payload = {
#             "model": bot.model,
#             "messages": [
#                 {"role": "system", "content": f"Translate the message to: {user_lang}."},
#                 {"role": "user", "content": chunk}
#             ],
#             "temperature": 0.5
#         }

#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {bot.openai_api_key}"
#         }

#         for attempt in range(PERPLEXITY_MAX_RETRIES):
#             try:
#                 async with httpx.AsyncClient() as client:
#                     response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
#                     logging.info(f"Translation response for chunk {index + 1}: {response.status_code}")

#                 if response.status_code == 200:
#                     try:
#                         response_json = response.json()
#                         translated_chunk = response_json['choices'][0]['message']['content'].strip()
#                         translated_chunks.append(translated_chunk)
#                         logging.info(f"Chunk {index + 1} translated successfully with content: {translated_chunk}")
#                         break
#                     except Exception as e:
#                         logging.error(f"Error processing translation response for a chunk: {e}")
#                 else:
#                     logging.error(f"Error in translating chunk {index + 1}: {response.text}")
#             except httpx.RequestError as e:
#                 logging.error(f"RequestError while calling OpenAI API: {e}")
#             except httpx.HTTPStatusError as e:
#                 logging.error(f"HTTPStatusError while calling OpenAI API: {e}")
#             except Exception as e:
#                 logging.error(f"Unexpected error while calling OpenAI API: {e}")

#             backoff_delay = min(PERPLEXITY_RETRY_DELAY, (2 ** attempt) + random.uniform(0, 1))
#             await asyncio.sleep(backoff_delay)

#         await asyncio.sleep(1)

#     rejoined_text = rejoin_chunks(translated_chunks)
#     logging.info(f"Final rejoined text length: {len(rejoined_text)}")
#     logging.info(f"Rejoined translated response: {rejoined_text}")

#     sanitized_text = sanitize_urls(rejoined_text)
#     logging.info(f"Sanitized translated response: {sanitized_text}")

#     telegram_formatted_response = format_headers_for_telegram(sanitized_text)
#     html_response = markdown_to_html(telegram_formatted_response)
#     logging.info(f"Parsed translated response: {html_response}")

#     if not html_response.strip():
#         logging.warning("Attempted to send an empty response. Skipping.")
#         return True

#     await handle_long_response(context, update.effective_message.chat_id, html_response)
#     logging.info("Response sent successfully, no further actions should be triggered.")
#     return True

# # original response translation; used only as a backup
# async def translate_response(bot, user_message, perplexity_response):
#     logging.info(f"Perplexity API Response to be translated: {perplexity_response}")

#     cleaned_message = re.sub(r"\[Whisper STT transcribed message from the user\]|\[end\]", "", user_message).strip()

#     try:
#         user_lang = detect(cleaned_message)
#         logging.info(f"Detected user language: {user_lang} -- user request: {user_message}")
#     except Exception as e:
#         logging.error(f"Error detecting user language: {e}")
#         formatted_response = format_headers_for_telegram(perplexity_response)
#         return markdown_to_html(formatted_response)

#     if user_lang == 'en':
#         logging.info("User's question is in English, converting Markdown to HTML.")
#         formatted_response = format_headers_for_telegram(perplexity_response)
#         return markdown_to_html(formatted_response)
#     else:
#         logging.info(f"User's question is in {user_lang}, proceeding with translation.")

#     system_message = {
#         "role": "system",
#         "content": f"Translate the message to: {user_lang}."
#     }

#     chat_history = [
#         system_message,
#         {"role": "user", "content": perplexity_response}
#     ]

#     payload = {
#         "model": bot.model,
#         "messages": chat_history,
#         "temperature": 0.5
#     }

#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {bot.openai_api_key}"
#     }

#     async with httpx.AsyncClient() as client:
#         response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)

#     if response.status_code == 200:
#         try:
#             response_json = response.json()
#             translated_reply = response_json['choices'][0]['message']['content'].strip()
#             logging.info(f"Translated response: {translated_reply}")
#             return translated_reply
#         except Exception as e:
#             logging.error(f"Error processing translation response: {e}")
#             return f"Translation failed due to an error: {e}"
#     else:
#         logging.error(f"Error in translating response: {response.text}")
#         return f"Failed to translate, API returned status code {response.status_code}: {response.text}"

# Utilities
def smart_chunk(text, chunk_size=CHUNK_SIZE):
    chunks = []
    blocks = text.split('\n\n')
    current_chunk = ""

    for block in blocks:
        if len(current_chunk) + len(block) + 2 <= chunk_size:
            current_chunk += block + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            if len(block) > chunk_size:
                lines = block.split('\n')
                temp_chunk = ""

                for line in lines:
                    if len(temp_chunk) + len(line) + 1 <= chunk_size:
                        temp_chunk += line + "\n"
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                            temp_chunk = ""
                        sentences = re.split('([.!?] )', line)
                        sentence_chunk = ""
                        for sentence in sentences:
                            if sentence.strip():
                                if len(sentence_chunk) + len(sentence) <= chunk_size:
                                    sentence_chunk += sentence
                                else:
                                    if sentence_chunk:
                                        chunks.append(sentence_chunk.strip())
                                        sentence_chunk = ""
                                    sentence_chunk = sentence
                        if sentence_chunk:
                            chunks.append(sentence_chunk.strip())
            else:
                current_chunk = block + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

def rejoin_chunks(chunks):
    rejoined_text = ""
    for i, chunk in enumerate(chunks):
        trimmed_chunk = chunk.strip()
        if i == 0:
            rejoined_text += trimmed_chunk
        else:
            if rejoined_text.endswith('\n\n'):
                if not trimmed_chunk.startswith('- ') and not trimmed_chunk.startswith('### ') and not trimmed_chunk.startswith('## '):
                    rejoined_text += '\n' + trimmed_chunk
                else:
                    rejoined_text += trimmed_chunk
            else:
                rejoined_text += '\n\n' + trimmed_chunk
    return rejoined_text

def format_headers_for_telegram(translated_response):
    lines = translated_response.split('\n')
    formatted_lines = []

    for i, line in enumerate(lines):
        if line.startswith('####'):
            if i > 0 and lines[i - 1].strip() != '':
                formatted_lines.append('')
            formatted_line = '◦ <b>' + line[4:].strip() + '</b>'
            formatted_lines.append(formatted_line)
            if i < len(lines) - 1 and lines[i + 1].strip() != '':
                formatted_lines.append('')
        elif line.startswith('###'):
            if i > 0 and lines[i - 1].strip() != '':
                formatted_lines.append('')
            formatted_line = '• <b>' + line[3:].strip() + '</b>'
            formatted_lines.append(formatted_line)
            if i < len(lines) - 1 and lines[i + 1].strip() != '':
                formatted_lines.append('')
        elif line.startswith('##'):
            if i > 0 and lines[i - 1].strip() != '':
                formatted_lines.append('')
            formatted_line = '➤ <b>' + line[2:].strip() + '</b>'
            formatted_lines.append(formatted_line)
            if i < len(lines) - 1 and lines[i + 1].strip() != '':
                formatted_lines.append('')
        else:
            formatted_lines.append(line)

    formatted_response = '\n'.join(formatted_lines)
    return formatted_response

def markdown_to_html(md_text):
    html_text = re.sub(r'\$\$(.*?)\$\$', r'<pre>\1</pre>', md_text)
    html_text = re.sub(r'\\\[(.*?)\\\]', r'<pre>\1</pre>', html_text)
    html_text = re.sub(r'^#### (.*)', r'<b>\1</b>', html_text, flags=re.MULTILINE)
    html_text = re.sub(r'^### (.*)', r'<b>\1</b>', html_text, flags=re.MULTILINE)
    html_text = re.sub(r'^## (.*)', r'<b>\1</b>', html_text, flags=re.MULTILINE)
    html_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_text)
    html_text = re.sub(r'\*(.*?)\*|_(.*?)_', r'<i>\1\2</i>', html_text)
    html_text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html_text)
    html_text = re.sub(r'`(.*?)`', r'<code>\1</code>', html_text)
    html_text = re.sub(r'```(.*?)```', r'<pre>\1</pre>', html_text, flags=re.DOTALL)
    return html_text

def sanitize_urls(text):
    url_pattern = re.compile(r'<(http[s]?://[^\s<>]+)>')
    sanitized_text = re.sub(url_pattern, r'\1', text)
    return sanitized_text

# split long messages
def split_message(text, max_length=MAX_TELEGRAM_MESSAGE_LENGTH):
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 1 <= max_length:
            current_chunk += paragraph + "\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Further split chunks that are still too large
    final_chunks = []
    for chunk in chunks:
        while len(chunk) > max_length:
            split_point = chunk.rfind('.', 0, max_length)
            if split_point == -1:
                split_point = max_length
            final_chunks.append(chunk[:split_point].strip())
            chunk = chunk[split_point:].strip()
        if chunk:
            final_chunks.append(chunk.strip())

    logging.info(f"Total number of chunks created: {len(final_chunks)}")
    return final_chunks

async def send_split_messages(context, chat_id, text):
    chunks = split_message(text)
    logging.info(f"Total number of chunks to be sent: {len(chunks)}")

    for chunk in chunks:
        if not chunk.strip():
            logging.warning("send_split_messages attempted to send an empty chunk. Skipping.")
            continue

        logging.info(f"Sending chunk with length: {len(chunk)}")
        await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode='HTML')
        logging.info(f"Sent chunk with length: {len(chunk)}")
    logging.info("send_split_messages completed.")

async def handle_long_response(context, chat_id, long_response_text):
    if not long_response_text.strip():
        logging.warning("handle_long_response received an empty message. Skipping.")
        return

    logging.info(f"Handling long response with text length: {len(long_response_text)}")
    await send_split_messages(context, chat_id, long_response_text)

# language detection over OpenAI API
async def detect_language(bot, text):
    prompt = f"Detect the language of the following text:\n\n{text}\n\nRespond with only the language code, e.g., 'en' for English, 'fi' for Finnish, 'jp' for Japanese. HINT: If the query starts off with i.e. 'kuka', 'mikä', 'mitä' or 'missä', 'milloin', 'miksi', 'minkä', 'minkälainen', 'mikä', 'kenen', 'kenenkä', 'keiden', 'kenestä, 'kelle', 'keneltä', 'kenelle', it's probably in Finnish ('fi')."
    
    payload = {
        "model": bot.model,
        "messages": [
            {"role": "system", "content": "You are a language detection assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
        "max_tokens": 10
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bot.openai_api_key}"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            detected_language = response.json()['choices'][0]['message']['content'].strip()
            logging.info(f"Detected language: {detected_language}")
            return detected_language
    except httpx.RequestError as e:
        logging.error(f"RequestError while calling OpenAI API: {e}")
    except httpx.HTTPStatusError as e:
        logging.error(f"HTTPStatusError while calling OpenAI API: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while calling OpenAI API: {e}")
        return 'en'  # Default to English in case of an error

# # ~~~~~~~~~~~~~~~~~~~~
# # legacy code below
# # (for reference only)
# # ~~~~~~~~~~~~~~~~~~~~

# # import nltk
# # import re
# # import openai
# # import httpx
# # import logging
# # import os
# # import httpx
# # import asyncio
# # import configparser
# # import random

# # from langdetect import detect
# # from telegram import constants

# # # Load the configuration file
# # config = configparser.ConfigParser()
# # config.read('config.ini')

# # # ~~~~~~~~~
# # # variables
# # # ~~~~~~~~~
# # # Define fallback default values
# # DEFAULT_PERPLEXITY_MODEL = "llama-3-sonar-large-32k-online"
# # DEFAULT_PERPLEXITY_MAX_TOKENS = 1024
# # DEFAULT_PERPLEXITY_TEMPERATURE = 0.0
# # DEFAULT_PERPLEXITY_MAX_RETRIES = 3
# # DEFAULT_PERPLEXITY_RETRY_DELAY = 25
# # DEFAULT_PERPLEXITY_TIMEOUT = 30
# # # chunk sizes are for translations
# # DEFAULT_CHUNK_SIZE = 500

# # # Perplexity API settings from config with fallback defaults
# # PERPLEXITY_MODEL = config.get('Perplexity', 'Model', fallback=DEFAULT_PERPLEXITY_MODEL)
# # PERPLEXITY_MAX_TOKENS = config.getint('Perplexity', 'MaxTokens', fallback=DEFAULT_PERPLEXITY_MAX_TOKENS)
# # PERPLEXITY_TEMPERATURE = config.getfloat('Perplexity', 'Temperature', fallback=DEFAULT_PERPLEXITY_TEMPERATURE)
# # PERPLEXITY_MAX_RETRIES = config.getint('Perplexity', 'MaxRetries', fallback=DEFAULT_PERPLEXITY_MAX_RETRIES)
# # PERPLEXITY_RETRY_DELAY = config.getint('Perplexity', 'RetryDelay', fallback=DEFAULT_PERPLEXITY_RETRY_DELAY)
# # PERPLEXITY_TIMEOUT = config.getint('Perplexity', 'Timeout', fallback=DEFAULT_PERPLEXITY_TIMEOUT)
# # CHUNK_SIZE = config.getint('Perplexity', 'ChunkSize', fallback=DEFAULT_CHUNK_SIZE)

# # # Assuming you've set PERPLEXITY_API_KEY in your environment variables
# # PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# # # Set the maximum length for a TG message, split accordingly 
# # # (4096 is the absolute maximum, better to stay under it)
# # MAX_TELEGRAM_MESSAGE_LENGTH = 4000

# # # Main Perplexity function
# # async def fact_check_with_perplexity(question: str):
# #     url = "https://api.perplexity.ai/chat/completions"
# #     headers = {
# #         "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
# #         "Content-Type": "application/json",
# #         "Accept": "application/json",
# #     }
# #     data = {
# #         "model": PERPLEXITY_MODEL,  # Specifying the model
# #         "stream": False,
# #         "max_tokens": PERPLEXITY_MAX_TOKENS,
# #         "temperature": PERPLEXITY_TEMPERATURE,  # Adjust based on how deterministic you want the responses to be
# #         "messages": [
# #             {
# #                 "role": "user",
# #                 "content": question
# #             }
# #         ]
# #     }

# #     async with httpx.AsyncClient(timeout=PERPLEXITY_TIMEOUT) as client:
# #         for attempt in range(PERPLEXITY_MAX_RETRIES):  # Retry mechanism
# #             try:
# #                 response = await client.post(url, json=data, headers=headers)
# #                 if response.status_code == 200:
# #                     return response.json()
# #                 elif response.status_code == 500:
# #                     logging.error("Perplexity API returned a 500 server error.")
# #                     return {"error": "server_error"}
# #                 elif response.status_code in [502, 503, 504]:  # Retry for server-related errors
# #                     logging.error(f"Perplexity API Error: {response.text}")
# #                 else:
# #                     logging.error(f"Perplexity API Error: {response.text}")
# #                     break
# #             except httpx.RequestError as e:
# #                 logging.error(f"RequestError while calling Perplexity API: {e}")
# #             except httpx.HTTPStatusError as e:
# #                 logging.error(f"HTTPStatusError while calling Perplexity API: {e}")
# #             except Exception as e:
# #                 logging.error(f"Unexpected error while calling Perplexity API: {e}")

# #             # Exponential backoff with jitter
# #             backoff_delay = min(PERPLEXITY_RETRY_DELAY, (2 ** attempt) + random.uniform(0, 1))
# #             await asyncio.sleep(backoff_delay)

# #     return None

# # # Queries Perplexity
# # async def query_perplexity(bot, chat_id, question: str):
# #     logging.info(f"Querying Perplexity with question: {question}")
# #     response_data = await fact_check_with_perplexity(question)

# #     if response_data:
# #         if 'choices' in response_data and len(response_data['choices']) > 0:
# #             bot_reply_content = response_data['choices'][0].get('message', {}).get('content', "")
# #             if bot_reply_content:
# #                 final_message = bot_reply_content.strip()
# #                 if final_message:  # Check if final message is not empty
# #                     return final_message
# #                 else:
# #                     logging.warning("Processed content is empty after stripping.")
# #                     return "Received an empty response, please try again."
# #             else:
# #                 logging.warning("No content received from Perplexity API.")
# #                 return "No answer received."
# #         elif 'error' in response_data and response_data['error'] == 'server_error':
# #             logging.error("Perplexity API server error.")
# #             return "[System message: Perplexity API is currently unavailable due to server issues. Please try again later.]"
# #         else:
# #             logging.error("Unexpected response structure from Perplexity API.")
# #             return "Error interpreting the response."
# #     else:
# #         return "API error encountered."

# # # latest, as per 0.724 // chunk the translations w/ jitter, split lengthier responses
# # # Updated translate_response_chunked function
# # # Updated translate_response_chunked function with additional logging and checks
# # async def translate_response_chunked(bot, user_message, openai_response, context, update):
# #     logging.info(f"OpenAI API Response to be translated: {openai_response}")

# #     cleaned_message = re.sub(r"\[Whisper STT transcribed message from the user\]|\[end\]", "", user_message).strip()

# #     try:
# #         user_lang = detect(cleaned_message)
# #         logging.info(f"Detected user language: {user_lang} -- user request: {user_message}")
# #     except Exception as e:
# #         logging.error(f"Error detecting user language: {e}")
# #         formatted_response = format_headers_for_telegram(openai_response)
# #         await handle_long_response(context, update.effective_message.chat_id, markdown_to_html(formatted_response))
# #         return

# #     if user_lang == 'en':
# #         logging.info("User's question is in English, skipping translation, converting Markdown to HTML.")
# #         sanitized_response = sanitize_urls(openai_response)
# #         formatted_response = format_headers_for_telegram(sanitized_response)
# #         html_response = markdown_to_html(formatted_response)
# #         logging.info(f"Parsed translated response: {html_response}")

# #         if not html_response.strip():
# #             logging.warning("Attempted to send an empty response. Skipping.")
# #             return

# #         await handle_long_response(context, update.effective_message.chat_id, html_response)
# #         return

# #     await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

# #     chunks = smart_chunk(openai_response)
# #     logging.info(f"Total chunks created: {len(chunks)}")
# #     translated_chunks = []

# #     for index, chunk in enumerate(chunks):
# #         logging.info(f"Translating chunk {index+1}/{len(chunks)}: {chunk}")

# #         payload = {
# #             "model": bot.model,
# #             "messages": [
# #                 {"role": "system", "content": f"Translate the message to: {user_lang}."},
# #                 {"role": "user", "content": chunk}
# #             ],
# #             "temperature": 0.5
# #         }

# #         headers = {
# #             "Content-Type": "application/json",
# #             "Authorization": f"Bearer {bot.openai_api_key}"
# #         }

# #         for attempt in range(PERPLEXITY_MAX_RETRIES):
# #             try:
# #                 async with httpx.AsyncClient() as client:
# #                     response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
# #                     logging.info(f"Translation response for chunk {index + 1}: {response.status_code}")

# #                 if response.status_code == 200:
# #                     try:
# #                         response_json = response.json()
# #                         translated_chunk = response_json['choices'][0]['message']['content'].strip()
# #                         translated_chunks.append(translated_chunk)
# #                         logging.info(f"Chunk {index + 1} translated successfully with content: {translated_chunk}")
# #                         break
# #                     except Exception as e:
# #                         logging.error(f"Error processing translation response for a chunk: {e}")
# #                 else:
# #                     logging.error(f"Error in translating chunk {index + 1}: {response.text}")
# #             except httpx.RequestError as e:
# #                 logging.error(f"RequestError while calling OpenAI API: {e}")
# #             except httpx.HTTPStatusError as e:
# #                 logging.error(f"HTTPStatusError while calling OpenAI API: {e}")
# #             except Exception as e:
# #                 logging.error(f"Unexpected error while calling OpenAI API: {e}")

# #             backoff_delay = min(PERPLEXITY_RETRY_DELAY, (2 ** attempt) + random.uniform(0, 1))
# #             await asyncio.sleep(backoff_delay)

# #         await asyncio.sleep(1)

# #     rejoined_text = rejoin_chunks(translated_chunks)
# #     logging.info(f"Final rejoined text length: {len(rejoined_text)}")
# #     logging.info(f"Rejoined translated response: {rejoined_text}")

# #     sanitized_text = sanitize_urls(rejoined_text)
# #     logging.info(f"Sanitized translated response: {sanitized_text}")

# #     telegram_formatted_response = format_headers_for_telegram(sanitized_text)
# #     html_response = markdown_to_html(telegram_formatted_response)
# #     logging.info(f"Parsed translated response: {html_response}")

# #     if not html_response.strip():
# #         logging.warning("Attempted to send an empty response. Skipping.")
# #         return

# #     await handle_long_response(context, update.effective_message.chat_id, html_response)
# #     logging.info("Response sent successfully, no further actions should be triggered.")

# #     # Ensure no further response attempts
# #     return

# # # translate response
# # async def translate_response(bot, user_message, perplexity_response):
# #     # Log the Perplexity API response before translation
# #     logging.info(f"Perplexity API Response to be translated: {perplexity_response}")

# #     # Preprocess the user_message to remove known metadata patterns
# #     cleaned_message = re.sub(r"\[Whisper STT transcribed message from the user\]|\[end\]", "", user_message).strip()

# #     # Detect the language of the user's question
# #     try:
# #         user_lang = detect(cleaned_message)
# #         logging.info(f"Detected user language: {user_lang} -- user request: {user_message}")
# #     except Exception as e:
# #         logging.error(f"Error detecting user language: {e}")
# #         # Directly convert and return if language detection fails; assuming English or Markdown needs HTML conversion
# #         formatted_response = format_headers_for_telegram(perplexity_response)
# #         return markdown_to_html(formatted_response)

# #     # Check if the detected language is English, skip translation if it is
# #     if user_lang == 'en':
# #         logging.info("User's question is in English, converting Markdown to HTML.")
# #         formatted_response = format_headers_for_telegram(perplexity_response)
# #         return markdown_to_html(formatted_response)
# #     else:
# #         logging.info(f"User's question is in {user_lang}, proceeding with translation.")

# #     # System message to guide the model for translating
# #     system_message = {
# #         "role": "system",
# #         "content": f"Translate the message to: {user_lang}."
# #     }

# #     # Prepare the chat history with only the Perplexity's response as the assistant's message to be translated
# #     chat_history = [
# #         system_message,
# #         {"role": "user", "content": perplexity_response}
# #     ]

# #     # Prepare the payload for the OpenAI API
# #     payload = {
# #         "model": bot.model,  # Specify the OpenAI model you're using for translating
# #         "messages": chat_history,
# #         "temperature": 0.5  # Adjust based on your preference for randomness in translation
# #     }

# #     headers = {
# #         "Content-Type": "application/json",
# #         "Authorization": f"Bearer {bot.openai_api_key}"  # Use the correct API key variable
# #     }

# #     # Make the API request to OpenAI
# #     async with httpx.AsyncClient() as client:
# #         response = await client.post("https://api.openai.com/v1/chat/completions",
# #                                      json=payload,
# #                                      headers=headers)

# #     # Process the response
# #     if response.status_code == 200:
# #         try:
# #             response_json = response.json()
# #             translated_reply = response_json['choices'][0]['message']['content'].strip()
# #             logging.info(f"Translated response: {translated_reply}")
# #             return translated_reply
# #         except Exception as e:
# #             logging.error(f"Error processing translation response: {e}")
# #             return f"Translation failed due to an error: {e}"
# #     else:
# #         logging.error(f"Error in translating response: {response.text}")
# #         return f"Failed to translate, API returned status code {response.status_code}: {response.text}"


# # # # translate in chunks (new method; with jitter to avoid API flood)
# # # async def translate_response_chunked(bot, user_message, openai_response, context, update):
# # #     logging.info(f"OpenAI API Response to be translated: {openai_response}")

# # #     # Clean the user_message as before
# # #     cleaned_message = re.sub(r"\[Whisper STT transcribed message from the user\]|\[end\]", "", user_message).strip()

# # #     try:
# # #         user_lang = detect(cleaned_message)
# # #         logging.info(f"Detected user language: {user_lang} -- user request: {user_message}")
# # #     except Exception as e:
# # #         logging.error(f"Error detecting user language: {e}")
# # #         formatted_response = format_headers_for_telegram(openai_response)
# # #         return markdown_to_html(formatted_response)

# # #     # Skip translation if the language is English
# # #     if user_lang == 'en':
# # #         logging.info("User's question is in English, skipping translation, converting Markdown to HTML.")

# # #         # Sanitize URLs in the OpenAI response
# # #         sanitized_response = sanitize_urls(openai_response)
# # #         logging.info(f"Sanitized OpenAI response: {sanitized_response}")

# # #         # Apply Telegram-specific formatting to the sanitized response
# # #         formatted_response = format_headers_for_telegram(sanitized_response)

# # #         # Convert the Telegram-formatted response to HTML
# # #         html_response = markdown_to_html(formatted_response)
# # #         logging.info(f"Parsed translated response: {html_response}")

# # #         return html_response

# # #     # Show typing animation at the start
# # #     await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

# # #     # Use smart_chunk to split the response text
# # #     chunks = smart_chunk(openai_response)

# # #     logging.info(f"Total chunks created: {len(chunks)}")  # Log total number of chunks
# # #     translated_chunks = []

# # #     for index, chunk in enumerate(chunks):
# # #         # logging.info(f"Translating chunk: {chunk}")
# # #         logging.info(f"Translating chunk {index+1}/{len(chunks)}: {chunk}")

# # #         # Prepare the payload for each chunk

# # #         # Show typing animation at the start
# # #         await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

# # #         payload = {
# # #             "model": bot.model,
# # #             "messages": [
# # #                 {"role": "system", "content": f"Translate the message to: {user_lang}."},
# # #                 {"role": "user", "content": chunk}
# # #             ],
# # #             "temperature": 0.5  # Keep as per your requirement
# # #         }

# # #         headers = {
# # #             "Content-Type": "application/json",
# # #             "Authorization": f"Bearer {bot.openai_api_key}"
# # #         }

# # #         for attempt in range(PERPLEXITY_MAX_RETRIES):
# # #             try:
# # #                 # Translate each chunk
# # #                 async with httpx.AsyncClient() as client:
# # #                     response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
# # #                     logging.info(f"Translation response for chunk {index + 1}: {response.status_code}")            

# # #                 if response.status_code == 200:
# # #                     try:
# # #                         response_json = response.json()
# # #                         translated_chunk = response_json['choices'][0]['message']['content'].strip()
# # #                         translated_chunks.append(translated_chunk)
# # #                         # Log the translated chunk content for verification
# # #                         logging.info(f"Chunk {index + 1} translated successfully with content: {translated_chunk}")                
# # #                         break
# # #                     except Exception as e:
# # #                         logging.error(f"Error processing translation response for a chunk: {e}")
# # #                         # Handle partial translation or decide to abort/return error based on your preference
# # #                 else:
# # #                     logging.error(f"Error in translating chunk {index + 1}: {response.text}")
# # #                     # Handle error, e.g., by breaking the loop or accumulating errors
# # #             except httpx.RequestError as e:
# # #                 logging.error(f"RequestError while calling OpenAI API: {e}")
# # #             except httpx.HTTPStatusError as e:
# # #                 logging.error(f"HTTPStatusError while calling OpenAI API: {e}")
# # #             except Exception as e:
# # #                 logging.error(f"Unexpected error while calling OpenAI API: {e}")

# # #             # Exponential backoff with jitter
# # #             backoff_delay = min(PERPLEXITY_RETRY_DELAY, (2 ** attempt) + random.uniform(0, 1))
# # #             await asyncio.sleep(backoff_delay)

# # #         # Wait for 1 second before processing the next chunk
# # #         await asyncio.sleep(1)

# # #     # Now, instead of manually concatenating translated chunks, use the rejoin_chunks function
# # #     rejoined_text = rejoin_chunks(translated_chunks)

# # #     logging.info(f"Final rejoined text length: {len(rejoined_text)}")
# # #     logging.info(f"Rejoined translated response: {rejoined_text}")

# # #     # Continue with your existing logic to format and return the translated text...
    
# # #     # Sanitize URLs in the rejoined text
# # #     sanitized_text = sanitize_urls(rejoined_text)
# # #     logging.info(f"Sanitized translated response: {sanitized_text}")

# # #     # Apply the header formatting for Telegram before converting to HTML
# # #     # telegram_formatted_response = format_headers_for_telegram(rejoined_text)
    
# # #     # Apply Telegram-specific formatting
# # #     telegram_formatted_response = format_headers_for_telegram(sanitized_text)

# # #     # Then convert the Telegram-formatted response to HTML
# # #     html_response = markdown_to_html(telegram_formatted_response)

# # #     logging.info(f"Parsed translated response: {html_response}")

# # #     return html_response

# # # # (old method; up until 29.may 2024)
# # # # translate in chunks
# # # async def translate_response_chunked(bot, user_message, perplexity_response, context, update):
# # #     logging.info(f"Perplexity API Response to be translated: {perplexity_response}")

# # #     # Clean the user_message as before
# # #     cleaned_message = re.sub(r"\[Whisper STT transcribed message from the user\]|\[end\]", "", user_message).strip()

# # #     try:
# # #         user_lang = detect(cleaned_message)
# # #         logging.info(f"Detected user language: {user_lang} -- user request: {user_message}")
# # #     except Exception as e:
# # #         logging.error(f"Error detecting user language: {e}")
# # #         formatted_response = format_headers_for_telegram(perplexity_response)
# # #         return markdown_to_html(formatted_response)

# # #     # Skip translation if the language is English
# # #     if user_lang == 'en':
# # #         logging.info("User's question is in English, skipping translation, converting Markdown to HTML.")

# # #         # Sanitize URLs in the Perplexity response
# # #         sanitized_response = sanitize_urls(perplexity_response)
# # #         logging.info(f"Sanitized Perplexity response: {sanitized_response}")

# # #         # Apply Telegram-specific formatting to the sanitized response
# # #         formatted_response = format_headers_for_telegram(sanitized_response)

# # #         # Convert the Telegram-formatted response to HTML
# # #         html_response = markdown_to_html(formatted_response)
# # #         logging.info(f"Parsed translated response: {html_response}")

# # #         return html_response

# # #     # Show typing animation at the start
# # #     await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

# # #     # Use smart_chunk to split the response text
# # #     chunks = smart_chunk(perplexity_response)

# # #     logging.info(f"Total chunks created: {len(chunks)}")  # Log total number of chunks
# # #     translated_chunks = []

# # #     for index, chunk in enumerate(chunks):
# # #         # logging.info(f"Translating chunk: {chunk}")
# # #         logging.info(f"Translating chunk {index+1}/{len(chunks)}: {chunk}")

# # #         # Prepare the payload for each chunk

# # #         # Show typing animation at the start
# # #         await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

# # #         payload = {
# # #             "model": bot.model,
# # #             "messages": [
# # #                 {"role": "system", "content": f"Translate the message to: {user_lang}."},
# # #                 {"role": "user", "content": chunk}
# # #             ],
# # #             "temperature": 0.5  # Keep as per your requirement
# # #         }

# # #         headers = {
# # #             "Content-Type": "application/json",
# # #             "Authorization": f"Bearer {bot.openai_api_key}"
# # #         }

# # #         # Translate each chunk
# # #         async with httpx.AsyncClient() as client:
# # #             response = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
# # #             logging.info(f"Translation response for chunk {index + 1}: {response.status_code}")            

# # #         if response.status_code == 200:
# # #             try:
# # #                 response_json = response.json()
# # #                 translated_chunk = response_json['choices'][0]['message']['content'].strip()
# # #                 translated_chunks.append(translated_chunk)
# # #                 # Log the translated chunk content for verification
# # #                 logging.info(f"Chunk {index + 1} translated successfully with content: {translated_chunk}")                
# # #             except Exception as e:
# # #                 logging.error(f"Error processing translation response for a chunk: {e}")
# # #                 # Handle partial translation or decide to abort/return error based on your preference
# # #         else:
# # #             logging.error(f"Error in translating chunk {index + 1}: {response.text}")
# # #             # Handle error, e.g., by breaking the loop or accumulating errors

# # #     # Wait for 1 second before processing the next chunk
# # #     await asyncio.sleep(1)

# # #     # Now, instead of manually concatenating translated chunks, use the rejoin_chunks function
# # #     rejoined_text = rejoin_chunks(translated_chunks)

# # #     logging.info(f"Final rejoined text length: {len(rejoined_text)}")
# # #     logging.info(f"Rejoined translated response: {rejoined_text}")

# # #     # Continue with your existing logic to format and return the translated text...
    
# # #     # Sanitize URLs in the rejoined text
# # #     sanitized_text = sanitize_urls(rejoined_text)
# # #     logging.info(f"Sanitized translated response: {sanitized_text}")

# # #     # Apply the header formatting for Telegram before converting to HTML
# # #     # telegram_formatted_response = format_headers_for_telegram(rejoined_text)
    
# # #     # Apply Telegram-specific formatting
# # #     telegram_formatted_response = format_headers_for_telegram(sanitized_text)

# # #     # Then convert the Telegram-formatted response to HTML
# # #     html_response = markdown_to_html(telegram_formatted_response)

# # #     logging.info(f"Parsed translated response: {html_response}")

# # #     return html_response


# # # ~~~~~~
# # # others 
# # # ~~~~~~

# # # safe strip
# # def safe_strip(value):
# #     return value.strip() if value else value

# # # smart chunking with improved end-of-text handling (v1.12)
# # def smart_chunk(text, chunk_size=CHUNK_SIZE):
# #     # Initialize a list to store the chunks
# #     chunks = []
    
# #     # Split the text into blocks separated by two newline characters to maintain paragraph breaks.
# #     blocks = text.split('\n\n')
    
# #     # Initialize an empty string to hold the current chunk content
# #     current_chunk = ""

# #     for block in blocks:
# #         if len(current_chunk) + len(block) + 2 <= chunk_size:  # +2 for the newline characters
# #             # If adding the block doesn't exceed the chunk size, add it to the current chunk
# #             current_chunk += block + "\n\n"
# #         else:
# #             # If the current chunk is not empty, store it before processing the new block
# #             if current_chunk:
# #                 chunks.append(current_chunk.strip())
# #                 current_chunk = ""

# #             # If the block itself is too large, split it further
# #             if len(block) > chunk_size:
# #                 lines = block.split('\n')
# #                 temp_chunk = ""

# #                 for line in lines:
# #                     if len(temp_chunk) + len(line) + 1 <= chunk_size:  # +1 for the newline character
# #                         temp_chunk += line + "\n"
# #                     else:
# #                         if temp_chunk:
# #                             chunks.append(temp_chunk.strip())
# #                             temp_chunk = ""
# #                         # Split the line if it's too long, handling sentence boundaries or splitting directly
# #                         sentences = re.split('([.!?] )', line)
# #                         sentence_chunk = ""
# #                         for sentence in sentences:
# #                             if sentence.strip():  # Avoid adding empty sentences
# #                                 if len(sentence_chunk) + len(sentence) <= chunk_size:
# #                                     sentence_chunk += sentence
# #                                 else:
# #                                     if sentence_chunk:
# #                                         chunks.append(sentence_chunk.strip())
# #                                         sentence_chunk = ""
# #                                     sentence_chunk = sentence
# #                         if sentence_chunk:
# #                             chunks.append(sentence_chunk.strip())
# #             else:
# #                 # If the block is not too large but the current chunk is full, start a new chunk
# #                 current_chunk = block + "\n\n"
    
# #     # After processing all blocks, add any remaining content in the current chunk
# #     if current_chunk.strip():
# #         chunks.append(current_chunk.strip())

# #     return chunks

# # # rejoining chunks
# # def rejoin_chunks(chunks):
# #     # Initialize an empty string to hold the rejoined text
# #     rejoined_text = ""
    
# #     # Iterate over the chunks
# #     for i, chunk in enumerate(chunks):
# #         # Trim any leading or trailing whitespace from the chunk
# #         trimmed_chunk = chunk.strip()
        
# #         # Append the trimmed chunk to the rejoined text
# #         if i == 0:
# #             # Directly append if it's the first chunk
# #             rejoined_text += trimmed_chunk
# #         else:
# #             # Check if the previous chunk ended with a paragraph break (two newlines)
# #             if rejoined_text.endswith('\n\n'):
# #                 # If so, append the next chunk with a single newline if it does not start with a list marker or header
# #                 if not trimmed_chunk.startswith('- ') and not trimmed_chunk.startswith('### ') and not trimmed_chunk.startswith('## '):
# #                     rejoined_text += '\n' + trimmed_chunk
# #                 else:
# #                     rejoined_text += trimmed_chunk
# #             else:
# #                 # Otherwise, append it with a paragraph break
# #                 rejoined_text += '\n\n' + trimmed_chunk
    
# #     return rejoined_text

# # # adding paragraph breaks back to headers
# # def add_paragraph_breaks_to_headers(translated_response):
# #     # Split the translated response into lines
# #     lines = translated_response.split('\n')

# #     # Initialize a list to hold the adjusted lines
# #     adjusted_lines = []

# #     # Iterate over the lines, adding a newline before headers as necessary
# #     for i, line in enumerate(lines):
# #         # Check if the line starts with a header marker and is not the first line
# #         if (line.startswith('##') or line.startswith('###')) and i > 0:
# #             # Ensure there is an empty line before the header
# #             if adjusted_lines[-1] != '':
# #                 adjusted_lines.append('')

# #         adjusted_lines.append(line)

# #     # Join the adjusted lines back into a single string
# #     adjusted_response = '\n'.join(adjusted_lines)
# #     return adjusted_response

# # # formatting headers to look neater for TG and ensure proper breaks
# # def format_headers_for_telegram(translated_response):
# #     # Split the translated response into lines
# #     lines = translated_response.split('\n')

# #     # Initialize a list to hold the formatted lines
# #     formatted_lines = []

# #     # Iterate over the lines, adding symbols before headers and ensuring proper line breaks
# #     for i, line in enumerate(lines):
# #         if line.startswith('####'):
# #             # Add a newline before the sub-sub-header if it's not the first line and the previous line is not empty
# #             if i > 0 and lines[i - 1].strip() != '':
# #                 formatted_lines.append('')
# #             # Format the sub-sub-header and add a newline after
# #             formatted_line = '◦ <b>' + line[4:].strip() + '</b>'
# #             formatted_lines.append(formatted_line)
# #             if i < len(lines) - 1 and lines[i + 1].strip() != '':
# #                 formatted_lines.append('')
# #         elif line.startswith('###'):
# #             if i > 0 and lines[i - 1].strip() != '':
# #                 formatted_lines.append('')
# #             formatted_line = '• <b>' + line[3:].strip() + '</b>'
# #             formatted_lines.append(formatted_line)
# #             if i < len(lines) - 1 and lines[i + 1].strip() != '':
# #                 formatted_lines.append('')
# #         elif line.startswith('##'):
# #             if i > 0 and lines[i - 1].strip() != '':
# #                 formatted_lines.append('')
# #             formatted_line = '➤ <b>' + line[2:].strip() + '</b>'
# #             formatted_lines.append(formatted_line)
# #             if i < len(lines) - 1 and lines[i + 1].strip() != '':
# #                 formatted_lines.append('')
# #         else:
# #             formatted_lines.append(line)

# #     # Join the adjusted lines back into a single string
# #     formatted_response = '\n'.join(formatted_lines)
# #     return formatted_response

# # # ~~~~~~~~~~~~~~~~
# # # additional tools
# # # ~~~~~~~~~~~~~~~~

# # # markdown to html // in case replies from Perplexity need to be parsed.
# # def markdown_to_html(md_text):
# #     # Handle LaTeX blocks first, treating them as code blocks
# #     html_text = re.sub(r'\$\$(.*?)\$\$', r'<pre>\1</pre>', md_text)
# #     html_text = re.sub(r'\\\[(.*?)\\\]', r'<pre>\1</pre>', html_text)

# #     # Convert Markdown headers to HTML <b> tags
# #     html_text = re.sub(r'^#### (.*)', r'<b>\1</b>', html_text, flags=re.MULTILINE)
# #     html_text = re.sub(r'^### (.*)', r'<b>\1</b>', html_text, flags=re.MULTILINE)
# #     html_text = re.sub(r'^## (.*)', r'<b>\1</b>', html_text, flags=re.MULTILINE)
    
# #     # Convert bold syntax
# #     html_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_text)
    
# #     # Convert italic syntax
# #     html_text = re.sub(r'\*(.*?)\*|_(.*?)_', r'<i>\1\2</i>', html_text)
    
# #     # Convert Markdown links to HTML <a> tags
# #     html_text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html_text)

# #     # Handle inline code with backticks `these`
# #     html_text = re.sub(r'`(.*?)`', r'<code>\1</code>', html_text)

# #     # Convert multiline code blocks with triple backticks
# #     html_text = re.sub(r'```(.*?)```', r'<pre>\1</pre>', html_text, flags=re.DOTALL)

# #     return html_text

# # # url sanitizing for any url's that are returned like <https://example.com> ...
# # def sanitize_urls(text):
# #     # Define a regex pattern to identify URLs wrapped in angle brackets
# #     # This pattern aims to match a URL starting with http or https and enclosed in angle brackets
# #     url_pattern = re.compile(r'<(http[s]?://[^\s<>]+)>')

# #     # Replace all occurrences of the pattern in the text
# #     # The replacement will keep the URL itself but remove the surrounding angle brackets
# #     sanitized_text = re.sub(url_pattern, r'\1', text)

# #     return sanitized_text

# # # split long messages
# # # Ensure split_message function is robust
# # def split_message(text, max_length=MAX_TELEGRAM_MESSAGE_LENGTH):
# #     sentences = re.split(r'(?<=[.!?]) +', text)
# #     chunks = []
# #     current_chunk = ""

# #     for sentence in sentences:
# #         if len(current_chunk) + len(sentence) + 1 <= max_length:
# #             current_chunk += sentence + " "
# #         else:
# #             if current_chunk:
# #                 chunks.append(current_chunk.strip())
# #             current_chunk = sentence + " "

# #     if current_chunk.strip():
# #         chunks.append(current_chunk.strip())

# #     return chunks

# # # Ensure send_split_messages is correctly implemented with logging
# # async def send_split_messages(context, chat_id, text):
# #     chunks = split_message(text)

# #     for chunk in chunks:
# #         if not chunk.strip():
# #             logging.warning("send_split_messages attempted to send an empty chunk. Skipping.")
# #             continue

# #         await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode='HTML')
# #         logging.info(f"Sent chunk with length: {len(chunk)}")

# # # Updated handle_long_response function to add logging
# # async def handle_long_response(context, chat_id, long_response_text):
# #     if not long_response_text.strip():
# #         logging.warning("handle_long_response received an empty message. Skipping.")
# #         return

# #     logging.info(f"Handling long response with text length: {len(long_response_text)}")
# #     await send_split_messages(context, chat_id, long_response_text)

# # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # # > archived code below <...>
# # # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
