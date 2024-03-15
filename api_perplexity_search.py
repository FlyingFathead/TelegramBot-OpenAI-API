# api_perplexity_search.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# https://github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import nltk
import re
import openai
import httpx
import logging
import os
import httpx
import asyncio

from langdetect import detect
from telegram import constants

# ~~~~~~~~~
# variables
# ~~~~~~~~~

# Global variable for chunk size
# Set this value as needed
CHUNK_SIZE = 500

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
        "model": "sonar-small-online",  # Specifying the pplx-70b-online model
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.0,  # Adjust based on how deterministic you want the responses to be
        "messages": [
            #{
            #    "role": "system",
            #    "content": "Be precise and concise in your responses."
            #},
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

# queries perplexity
async def query_perplexity(bot, chat_id, question: str):
    # Trigger typing animation
    # await bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = {
        # i.e. `7b-online` or `70b-online`
        # note: models such as "pplx-70b-online" are deprecated and will be out in march 2024
        # use the new sonar models instead; see: https://docs.perplexity.ai/docs/model-cards#perplexity-models
        "model": "sonar-small-online",
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0.0,
        "messages": [
            # {"role": "system", "content": "Be precise in your responses. Answer in English. Use online sources as much as possible."},
            {"role": "user", "content": question}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        logging.info(f"Response type: {type(response.json())}, Content: {response.text}")

        if response.status_code == 200:
            response_data = response.json()

            if 'choices' in response_data and len(response_data['choices']) > 0 and 'message' in response_data['choices'][0] and 'content' in response_data['choices'][0]['message']:
                bot_reply_content = response_data['choices'][0]['message']['content']
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
        # Directly convert and return if language detection fails; assuming English or Markdown needs HTML conversion
        formatted_response = format_headers_for_telegram(perplexity_response)
        return markdown_to_html(formatted_response)
    
    # Check if the detected language is English, skip translation if it is
    if user_lang == 'en':
        logging.info("User's question is in English, converting Markdown to HTML.")
        formatted_response = format_headers_for_telegram(perplexity_response)
        return markdown_to_html(formatted_response)
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
async def translate_response_chunked(bot, user_message, perplexity_response, context, update):
    logging.info(f"Perplexity API Response to be translated: {perplexity_response}")

    # Clean the user_message as before
    cleaned_message = re.sub(r"\[Whisper STT transcribed message from the user\]|\[end\]", "", user_message).strip()

    try:
        user_lang = detect(cleaned_message)
        logging.info(f"Detected user language: {user_lang} -- user request: {user_message}")
    except Exception as e:
        logging.error(f"Error detecting user language: {e}")
        formatted_response = format_headers_for_telegram(perplexity_response)
        return markdown_to_html(formatted_response)

    # Skip translation if the language is English
    if user_lang == 'en':
        logging.info("User's question is in English, skipping translation, converting Markdown to HTML.")

        # Sanitize URLs in the Perplexity response
        sanitized_response = sanitize_urls(perplexity_response)
        logging.info(f"Sanitized Perplexity response: {sanitized_response}")

        # Apply Telegram-specific formatting to the sanitized response
        formatted_response = format_headers_for_telegram(sanitized_response)

        # Convert the Telegram-formatted response to HTML
        html_response = markdown_to_html(formatted_response)
        logging.info(f"Parsed translated response: {html_response}")

        return html_response

    # Show typing animation at the start
    await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

    # Use smart_chunk to split the response text
    chunks = smart_chunk(perplexity_response)

    logging.info(f"Total chunks created: {len(chunks)}")  # Log total number of chunks
    translated_chunks = []

    for index, chunk in enumerate(chunks):
        # logging.info(f"Translating chunk: {chunk}")
        logging.info(f"Translating chunk {index+1}/{len(chunks)}: {chunk}")

        # Prepare the payload for each chunk

        # Show typing animation at the start
        await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=constants.ChatAction.TYPING)

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
            logging.info(f"Translation response for chunk {index + 1}: {response.status_code}")            

        if response.status_code == 200:
            try:
                response_json = response.json()
                translated_chunk = response_json['choices'][0]['message']['content'].strip()
                translated_chunks.append(translated_chunk)
                # Log the translated chunk content for verification
                logging.info(f"Chunk {index + 1} translated successfully with content: {translated_chunk}")                
            except Exception as e:
                logging.error(f"Error processing translation response for a chunk: {e}")
                # Handle partial translation or decide to abort/return error based on your preference
        else:
            logging.error(f"Error in translating chunk {index + 1}: {response.text}")
            # Handle error, e.g., by breaking the loop or accumulating errors

    # Wait for 1 second before processing the next chunk
    await asyncio.sleep(1)

    # Now, instead of manually concatenating translated chunks, use the rejoin_chunks function
    rejoined_text = rejoin_chunks(translated_chunks)

    logging.info(f"Final rejoined text length: {len(rejoined_text)}")
    logging.info(f"Rejoined translated response: {rejoined_text}")

    # Continue with your existing logic to format and return the translated text...
    
    # Sanitize URLs in the rejoined text
    sanitized_text = sanitize_urls(rejoined_text)
    logging.info(f"Sanitized translated response: {sanitized_text}")

    # Apply the header formatting for Telegram before converting to HTML
    # telegram_formatted_response = format_headers_for_telegram(rejoined_text)
    
    # Apply Telegram-specific formatting
    telegram_formatted_response = format_headers_for_telegram(sanitized_text)

    # Then convert the Telegram-formatted response to HTML
    html_response = markdown_to_html(telegram_formatted_response)

    logging.info(f"Parsed translated response: {html_response}")

    return html_response

# ~~~~~~
# others 
# ~~~~~~

# safe strip
def safe_strip(value):
    return value.strip() if value else value

# smart chunking with improved end-of-text handling (v1.12)
def smart_chunk(text, chunk_size=CHUNK_SIZE):
    # Initialize a list to store the chunks
    chunks = []
    
    # Split the text into blocks separated by two newline characters to maintain paragraph breaks.
    blocks = text.split('\n\n')
    
    # Initialize an empty string to hold the current chunk content
    current_chunk = ""

    for block in blocks:
        if len(current_chunk) + len(block) + 2 <= chunk_size:  # +2 for the newline characters
            # If adding the block doesn't exceed the chunk size, add it to the current chunk
            current_chunk += block + "\n\n"
        else:
            # If the current chunk is not empty, store it before processing the new block
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            # If the block itself is too large, split it further
            if len(block) > chunk_size:
                lines = block.split('\n')
                temp_chunk = ""

                for line in lines:
                    if len(temp_chunk) + len(line) + 1 <= chunk_size:  # +1 for the newline character
                        temp_chunk += line + "\n"
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                            temp_chunk = ""
                        # Split the line if it's too long, handling sentence boundaries or splitting directly
                        sentences = re.split('([.!?] )', line)
                        sentence_chunk = ""
                        for sentence in sentences:
                            if sentence.strip():  # Avoid adding empty sentences
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
                # If the block is not too large but the current chunk is full, start a new chunk
                current_chunk = block + "\n\n"
    
    # After processing all blocks, add any remaining content in the current chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

# rejoining chunks
def rejoin_chunks(chunks):
    # Initialize an empty string to hold the rejoined text
    rejoined_text = ""
    
    # Iterate over the chunks
    for i, chunk in enumerate(chunks):
        # Trim any leading or trailing whitespace from the chunk
        trimmed_chunk = chunk.strip()
        
        # Append the trimmed chunk to the rejoined text
        if i == 0:
            # Directly append if it's the first chunk
            rejoined_text += trimmed_chunk
        else:
            # Check if the previous chunk ended with a paragraph break (two newlines)
            if rejoined_text.endswith('\n\n'):
                # If so, append the next chunk with a single newline if it does not start with a list marker or header
                if not trimmed_chunk.startswith('- ') and not trimmed_chunk.startswith('### ') and not trimmed_chunk.startswith('## '):
                    rejoined_text += '\n' + trimmed_chunk
                else:
                    rejoined_text += trimmed_chunk
            else:
                # Otherwise, append it with a paragraph break
                rejoined_text += '\n\n' + trimmed_chunk
    
    return rejoined_text

# adding paragraph breaks back to headers
def add_paragraph_breaks_to_headers(translated_response):
    # Split the translated response into lines
    lines = translated_response.split('\n')

    # Initialize a list to hold the adjusted lines
    adjusted_lines = []

    # Iterate over the lines, adding a newline before headers as necessary
    for i, line in enumerate(lines):
        # Check if the line starts with a header marker and is not the first line
        if (line.startswith('##') or line.startswith('###')) and i > 0:
            # Ensure there is an empty line before the header
            if adjusted_lines[-1] != '':
                adjusted_lines.append('')

        adjusted_lines.append(line)

    # Join the adjusted lines back into a single string
    adjusted_response = '\n'.join(adjusted_lines)
    return adjusted_response

# formatting headers to look neater for TG and ensure proper breaks
def format_headers_for_telegram(translated_response):
    # Split the translated response into lines
    lines = translated_response.split('\n')

    # Initialize a list to hold the formatted lines
    formatted_lines = []

    # Iterate over the lines, adding symbols before headers and ensuring proper line breaks
    for i, line in enumerate(lines):
        if line.startswith('####'):
            # Add a newline before the sub-sub-header if it's not the first line and the previous line is not empty
            if i > 0 and lines[i - 1].strip() != '':
                formatted_lines.append('')
            # Format the sub-sub-header and add a newline after
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

    # Join the adjusted lines back into a single string
    formatted_response = '\n'.join(formatted_lines)
    return formatted_response

# ~~~~~~~~~~~~~~~~
# additional tools
# ~~~~~~~~~~~~~~~~

# markdown to html // in case replies from Perplexity need to be parsed.
def markdown_to_html(md_text):
    # Handle LaTeX blocks first, treating them as code blocks
    html_text = re.sub(r'\$\$(.*?)\$\$', r'<pre>\1</pre>', md_text)
    html_text = re.sub(r'\\\[(.*?)\\\]', r'<pre>\1</pre>', html_text)

    # Convert Markdown headers to HTML <b> tags
    html_text = re.sub(r'^#### (.*)', r'<b>\1</b>', html_text, flags=re.MULTILINE)
    html_text = re.sub(r'^### (.*)', r'<b>\1</b>', html_text, flags=re.MULTILINE)
    html_text = re.sub(r'^## (.*)', r'<b>\1</b>', html_text, flags=re.MULTILINE)
    
    # Convert bold syntax
    html_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_text)
    
    # Convert italic syntax
    html_text = re.sub(r'\*(.*?)\*|_(.*?)_', r'<i>\1\2</i>', html_text)
    
    # Convert Markdown links to HTML <a> tags
    html_text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html_text)

    # Handle inline code with backticks `these`
    html_text = re.sub(r'`(.*?)`', r'<code>\1</code>', html_text)

    # Convert multiline code blocks with triple backticks
    html_text = re.sub(r'```(.*?)```', r'<pre>\1</pre>', html_text, flags=re.DOTALL)

    return html_text

# url sanitizing for any url's that are returned like <https://example.com> ...
def sanitize_urls(text):
    # Define a regex pattern to identify URLs wrapped in angle brackets
    # This pattern aims to match a URL starting with http or https and enclosed in angle brackets
    url_pattern = re.compile(r'<(http[s]?://[^\s<>]+)>')

    # Replace all occurrences of the pattern in the text
    # The replacement will keep the URL itself but remove the surrounding angle brackets
    sanitized_text = re.sub(url_pattern, r'\1', text)

    return sanitized_text

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# > archived code below, to be removed ...
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# smart chunking (v1.09)
""" def smart_chunk(text, chunk_size=CHUNK_SIZE):
    chunks = []
    start_index = 0
    text_length = len(text)

    # Regular expressions to identify list items
    list_item_pattern = re.compile(r'^[\-\*] |\d+\. ')

    while start_index < text_length:
        end_index = start_index + chunk_size if start_index + chunk_size < text_length else text_length
        chunk = text[start_index:end_index]

        # Check if the chunk ends in the middle of a list item or paragraph
        if end_index != text_length:
            next_newline = text.find('\n', end_index)
            next_list_item = list_item_pattern.search(text, end_index)
            
            # Extend chunk to the end of the paragraph or list item if necessary
            if next_newline != -1 and (not next_list_item or next_newline < next_list_item.start()):
                end_index = next_newline + 1
            elif next_list_item:
                end_index = next_list_item.start()

        # Append the processed chunk and update start_index
        chunks.append(text[start_index:end_index].strip())
        start_index = end_index

    return chunks
 """

# nltk-tryouts // smart chunking (v1.06)
""" def smart_chunk(text, chunk_size=CHUNK_SIZE):
  chunks = []
  sentence_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

  # Split the text into sentences
  sentences = sentence_tokenizer.tokenize(text)

  # Iterate through sentences
  for sentence in sentences:
    # Check if sentence length exceeds chunk size
    if len(sentence) > chunk_size:
      # Look for the next full stop or list item indicator
      next_stop = sentence.find(".", 0)
      next_list_item = sentence.find("-", 0) if "-" in sentence else sentence.find("*", 0)

      # Split only until the next full stop or list item indicator
      split_point = min(next_stop, next_list_item) if next_stop > -1 or next_list_item > -1 else len(sentence)
      chunk = sentence[:split_point].strip()

      # If there's remaining text, handle it recursively
      remaining_text = sentence[split_point:].strip()
      if remaining_text:
        chunks.extend(smart_chunk(remaining_text, chunk_size))
    else:
      # If sentence length is smaller than chunk size, add it directly
      chunks.append(sentence.strip())

  return chunks """

# nltk-tryouts // smart chunking (v1.05)
""" def smart_chunk(text, chunk_size=CHUNK_SIZE):
  chunks = []
  sentence_tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')  # Replace with your preferred library

  # Split the text into sentences
  sentences = sentence_tokenizer.tokenize(text)

  # Iterate through sentences
  for sentence in sentences:
    # Check if the sentence length exceeds chunk size
    if len(sentence) > chunk_size:
      # Split the sentence into smaller chunks
      for sub_sentence in nltk.sent_tokenize(sentence, language='english'):  # Replace with your preferred library
        chunks.append(sub_sentence.strip())
    else:
      # If sentence length is smaller than chunk size, add it directly
      chunks.append(sentence.strip())

  return chunks """

# OLD // deprecated // perplexity 70b query
""" async def query_pplx_70b_online(prompt):
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
        return None """

# smart chunking (v1.03)
""" def smart_chunk(text, chunk_size=CHUNK_SIZE, buffer_zone=50):    
    # Splits the text into chunks, trying to break at logical points within CHUNK_SIZE,
    # with special consideration for list items starting with "-" and numbered list items.
    # If no logical split point is found within the chunk, it tries to split at the nearest space
    # within a buffer zone before the end of the chunk.

    # Args:
    # - text (str): The text to be chunked.
    # - chunk_size (int): Maximum size of each chunk.
    # - buffer_zone (int): The range within the end of the chunk to look for a space as a split point.

    # Returns:
    # - List[str]: List of text chunks.

    chunks = []
    start_index = 0

    # Pattern to identify numbered list items and bullet points
    list_item_pattern = re.compile(r'^(\d+\.\s+|\-\s+)', re.MULTILINE)

    while start_index < len(text):
        # Determine the tentative end index of the next chunk
        end_index = min(start_index + chunk_size, len(text))

        # Search for the last occurrence of a list item or newline within the chunk
        matches = list(list_item_pattern.finditer(text, start_index, end_index))
        last_match = matches[-1] if matches else None

        if last_match and last_match.start() > start_index:
            # Split just before the last list item found, if any
            split_pos = last_match.start()
        else:
            # Attempt to find the nearest space within the buffer zone before the end of the chunk
            buffer_start = max(start_index, end_index - buffer_zone)
            space_pos = text.rfind(' ', buffer_start, end_index)
            
            if space_pos != -1:
                # If a space is found, use it as the split point
                split_pos = space_pos + 1
            else:
                # If no space is found within the buffer zone, split at the end of the chunk
                split_pos = end_index

        # Extract the chunk
        chunk = text[start_index:split_pos].rstrip()

        # Append the chunk and update the start_index for the next chunk
        chunks.append(chunk)
        start_index = split_pos

    return chunks """

# smart chunking (v1.02)
""" def smart_chunk(text, chunk_size=CHUNK_SIZE):
    
    # Splits the text into chunks, trying to break at logical points within CHUNK_SIZE,
    # while preserving the original text structure, including paragraph breaks indicated by double newlines.
    # This function aims to maintain the integrity of paragraph formatting by recognizing and preserving double newline characters.

    # Args:
    # - text (str): The text to be chunked.
    # - chunk_size (int): Desired maximum size of each chunk.

    # Returns:
    # - List[str]: List of text chunks, with original paragraph formatting preserved.

    chunks = []
    start_index = 0

    while start_index < len(text):
        # Determine the tentative end index of the next chunk
        end_index = min(start_index + chunk_size, len(text))

        # First, try to respect the paragraph breaks by looking for double newlines
        double_newline_pos = text.rfind('\n\n', start_index, end_index)

        if double_newline_pos != -1 and double_newline_pos + 2 != end_index:
            # If a double newline is found, and it's not right at the end of the chunk,
            # split there to keep paragraphs intact
            split_pos = double_newline_pos + 2  # Include the double newlines in the chunk
        elif end_index < len(text):
            # If we're not at the end of the text, look for the nearest single newline or space
            # to avoid splitting words or sentences
            single_newline_pos = text.rfind('\n', start_index, end_index)
            space_pos = text.rfind(' ', start_index, end_index)
            split_pos = max(single_newline_pos, space_pos) + 1
        else:
            # If at the end of the text, or no suitable break point is found, use the current end_index
            split_pos = end_index

        # Ensure the split position does not exceed the text length
        split_pos = min(split_pos, len(text))

        # Extract the chunk
        chunk = text[start_index:split_pos]

        # Append the chunk and update the start index for the next chunk
        chunks.append(chunk)
        start_index = split_pos

    return chunks """

# v1.0 (old)
# Adjusted smart_chunk method to use the global CHUNK_SIZE
""" def smart_chunk(text, chunk_size=CHUNK_SIZE):

    # Splits the text into chunks, trying to break at logical points within CHUNK_SIZE,
    # with special consideration for list items starting with "-" and numbered list items.

    # Args:
    # - text (str): The text to be chunked.
    # - chunk_size (int): Maximum size of each chunk.

    # Returns:
    # - List[str]: List of text chunks.

    chunks = []
    start_index = 0

    # Pattern to identify numbered list items and bullet points
    list_item_pattern = re.compile(r'^(\d+\.\s+|\-\s+)', re.MULTILINE)

    while start_index < len(text):
        # Determine the tentative end index of the next chunk
        end_index = min(start_index + chunk_size, len(text))

        # Search for the last occurrence of a list item or newline within the chunk
        matches = list(list_item_pattern.finditer(text, start_index, end_index))
        last_match = matches[-1] if matches else None

        # Choose the best place to split the chunk
        if last_match and last_match.start() > start_index:
            # Split just before the last list item found, if any
            split_pos = last_match.start()
        else:
            # If no list item is found, or it's at the start, try to split at the end of the chunk
            split_pos = end_index

        # Extract the chunk
        chunk = text[start_index:split_pos].rstrip()

        # Append the chunk and update the start_index for the next chunk
        chunks.append(chunk)
        start_index = split_pos

    return chunks """

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