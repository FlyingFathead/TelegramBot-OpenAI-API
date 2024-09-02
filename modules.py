# modules.py
import os
import json
import asyncio
import datetime
import logging
from transformers import GPT2Tokenizer
import re
import html

logger = logging.getLogger('TelegramBotLogger')

# count tokens (w/ check)
def count_tokens(text, tokenizer):
    if text is None:
        return 0
    token_count = len(tokenizer.encode(text))
    logger.debug(f"Counting tokens for text: '{text[:30]}...' Results in token count: {token_count}")
    return token_count

# read total token usage
def read_total_token_usage(token_usage_file):
    try:
        with open(token_usage_file, 'r') as file:
            data = json.load(file)
        current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        
        # If the current date is not in data, reset the token count
        if current_date not in data:
            data[current_date] = 0

        # Return the usage for the current date
        return data[current_date]
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is invalid, return 0 and reset the count
        return 0

# write latest token count data
def write_total_token_usage(token_usage_file, usage):
    try:
        with open(token_usage_file, 'r') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}  # Initialize a new dictionary if the file doesn't exist or is invalid

    current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    data[current_date] = usage  # Update the current date's usage

    with open(token_usage_file, 'w') as file:
        json.dump(data, file)

# reset token count at midnight
def reset_token_usage_at_midnight(token_usage_file, reset_in_memory_counter_callback=None):
    try:
        current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        if os.path.exists(token_usage_file):
            with open(token_usage_file, 'r+') as file:
                data = json.load(file)
                data[current_date] = 0  # Reset the token usage for the current date
                file.seek(0)
                json.dump(data, file)
                file.truncate()
            logging.info(f"Token usage reset for {current_date}.")
            if reset_in_memory_counter_callback:
                reset_in_memory_counter_callback()  # Reset the in-memory counter if callback is provided
        else:
            logging.error("Token usage file does not exist. No reset performed.")
    except Exception as e:
        logging.error(f"Failed to reset token usage: {e}")


def escape_html(text):
    # Escape only the necessary HTML characters, avoiding double-escaping
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def escape_except_a(text):
    # Escape all HTML special characters except within <a> tags
    escaped_text = ""
    last_end = 0
    for match in re.finditer(r'<a href="(.*?)">(.*?)</a>', text):
        # Append the text before the <a> tag, escaping it
        escaped_text += html.escape(text[last_end:match.start()])
        # Append the <a> tag as it is, without escaping
        escaped_text += match.group(0)
        last_end = match.end()
    # Escape the rest of the text after the last <a> tag
    escaped_text += html.escape(text[last_end:])
    return escaped_text

def preserve_html_and_escape_text(text):
    # Escape all HTML special characters outside of tags
    escaped_text = ""
    last_end = 0
    for match in re.finditer(r'<a href="(.*?)">(.*?)</a>', text):
        # Escape the text before the <a> tag, but leave the <a> tag as it is
        escaped_text += html.escape(text[last_end:match.start()])
        escaped_text += match.group(0)  # Append the <a> tag
        last_end = match.end()
    # Escape the remaining text after the last <a> tag
    escaped_text += html.escape(text[last_end:])
    return escaped_text

# markdown to html parsing
def markdown_to_html(text):
    try:
        # Handle the code blocks with optional language specification
        def replace_codeblock(match):
            full_codeblock = match.group(0)  # Get the entire matched code block
            code_content = match.group(2)  # Get the actual code inside the block
            language = match.group(1)  # Get the language identifier

            # Escape the code content for HTML
            escaped_code = html.escape(code_content.strip())

            # Return the formatted code block with the language class if provided
            if language:
                return f'<pre><code class="language-{language}">{escaped_code}</code></pre>'
            else:
                return f'<pre><code>{escaped_code}</code></pre>'

        # Regex to capture language identifier and code block
        text = re.sub(r'```(\w+)?\n([\s\S]*?)```', replace_codeblock, text)

        # Handle inline code and other markdown elements
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
        text = re.sub(r'`([^`]*)`', r'<code>\1</code>', text)
        text = re.sub(r'######\s*(.*)', r'➤ <b>\1</b>', text)
        text = re.sub(r'#####\s*(.*)', r'➤ <b>\1</b>', text)
        text = re.sub(r'####\s*(.*)', r'➤ <b>\1</b>', text)
        text = re.sub(r'###\s*(.*)', r'➤ <b>\1</b>', text)
        text = re.sub(r'##\s*(.*)', r'➤ <b>\1</b>', text)
        text = re.sub(r'#\s*(.*)', r'➤ <b>\1</b>', text)

        return text

    except Exception as e:
        return str(e)
    
# def markdown_to_html(text):
#     try:
#         # Supported URL schemes, now including tel: and mailto:
#         supported_schemes = r'(https?|ftp|sftp|mailto|tel|sms|geo|file|data|git|ssh|ircs?|svn|news|magnet|ws|wss|jdbc)'
        
#         # Convert Markdown links [text](url) to HTML <a href="url">text</a>
#         text = re.sub(r'\[(.*?)\]\((' + supported_schemes + r':\S+)\)', r'<a href="\2">\1</a>', text)

#         # Handle bold and italics, without over-escaping
#         text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
#         text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
#         text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)

#         # Handle inline code
#         text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)

#         # Handle headers
#         text = re.sub(r'######\s*(.*)', r'➤ <b>\1</b>', text)
#         text = re.sub(r'#####\s*(.*)', r'➤ <b>\1</b>', text)
#         text = re.sub(r'####\s*(.*)', r'➤ <b>\1</b>', text)
#         text = re.sub(r'###\s*(.*)', r'➤ <b>\1</b>', text)
#         text = re.sub(r'##\s*(.*)', r'➤ <b>\1</b>', text)
#         text = re.sub(r'#\s*(.*)', r'➤ <b>\1</b>', text)

#         return text
#     except Exception as e:
#         print(f"Error during markdown to HTML conversion: {str(e)}")
#         return text  # Return original text as a fallback

# def markdown_to_html(text):
#     try:
#         # Convert Markdown links [text](url) to HTML <a href="url">text</a> first
#         text = re.sub(r'\[(.*?)\]\((https?://\S+)\)', r'<a href="\2">\1</a>', text)

#         # Split the text into code blocks and other parts
#         parts = re.split(r'(```.*?```)', text, flags=re.DOTALL)
#         for i, part in enumerate(parts):
#             # Only process non-code blocks
#             if not part.startswith('```'):
#                 # Escape all HTML special characters except within <a> tags
#                 part = preserve_html_and_escape_text(part)

#                 # Apply other markdown to HTML transformations
#                 part = re.sub(r'`(.*?)`', r'<code>\1</code>', part)
#                 part = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', part)
#                 part = re.sub(r'\*(.*?)\*', r'<i>\1</i>', part)
#                 part = re.sub(r'_(.*?)_', r'<i>\1</i>', part)
#                 part = re.sub(r'######\s*(.*)', r'➤ <b>\1</b>', part)
#                 part = re.sub(r'#####\s*(.*)', r'➤ <b>\1</b>', part)
#                 part = re.sub(r'####\s*(.*)', r'➤ <b>\1</b>', part)
#                 part = re.sub(r'###\s*(.*)', r'➤ <b>\1</b>', part)
#                 part = re.sub(r'##\s*(.*)', r'➤ <b>\1</b>', part)
#                 part = re.sub(r'#\s*(.*)', r'➤ <b>\1</b>', part)
#                 parts[i] = part
#             else:
#                 # Handle code blocks
#                 language_match = re.match(r'```(\w+)?\s', part)
#                 language = language_match.group(1) if language_match else ''
#                 code_content = re.sub(r'```(\w+)?\s', '', part, count=1)
#                 code_content = code_content.rstrip('`').rstrip()
#                 code_content = html.escape(code_content)
#                 parts[i] = f'<pre><code class="{language}">{code_content}</code></pre>'

#         # Reassemble the parts into the final HTML
#         final_html = ''.join(parts)
#         return final_html
#     except Exception as e:
#         print(f"Error during markdown to HTML conversion: {str(e)}")
#         return html.escape(text)  # As a fallback, escape the entire input

# # ==========================================
# # v0.737 method // may lead to over-escaping
# # ==========================================
# def escape_html(text):
#     return html.escape(text)

# def markdown_to_html(text):
#     # Split the text into code blocks and other parts
#     parts = re.split(r'(```.*?```)', text, flags=re.DOTALL)
#     for i, part in enumerate(parts):
#         # Only process non-code blocks
#         if not part.startswith('```'):
#             part = escape_html(part)
#             part = re.sub(r'`(.*?)`', r'<code>\1</code>', part)
#             part = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', part)
#             part = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', part)
#             part = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', part)
#             part = re.sub(r'\[(.*?)\]\((https?://\S+)\)', r'<a href="\2">\1</a>', part)            
#             part = re.sub(r'^######\s*(.*)', r'➤ <b>\1</b>', part, flags=re.MULTILINE)
#             part = re.sub(r'^#####\s*(.*)', r'➤ <b>\1</b>', part, flags=re.MULTILINE)
#             part = re.sub(r'^####\s*(.*)', r'➤ <b>\1</b>', part, flags=re.MULTILINE)
#             part = re.sub(r'^###\s*(.*)', r'➤ <b>\1</b>', part, flags=re.MULTILINE)
#             part = re.sub(r'^##\s*(.*)', r'➤ <b>\1</b>', part, flags=re.MULTILINE)
#             part = re.sub(r'^#\s*(.*)', r'➤ <b>\1</b>', part, flags=re.MULTILINE)
#             parts[i] = part
#         else:
#             # For code blocks, extract the language hint (if any)
#             language_match = re.match(r'```(\w+)?\s', part)
#             language = language_match.group(1) if language_match else ''
#             # Remove the language hint and backticks from the actual code
#             code_content = re.sub(r'```(\w+)?\s', '', part, count=1)
#             code_content = code_content.rstrip('`').rstrip()
#             # Escape HTML characters in code content
#             code_content = escape_html(code_content)
#             # Wrap the code with <pre> and <code>
#             parts[i] = f'<pre><code class="{language}">{code_content}</code></pre>'

#     # Reassemble the parts into the final HTML
#     return ''.join(parts)

# # convert markdowns to html
# def escape_html(text):
#     # Escape HTML special characters
#     return (text.replace('&', '&amp;')
#                 .replace('<', '&lt;')
#                 .replace('>', '&gt;')
#                 .replace('"', '&quot;'))

# def markdown_to_html(text):
#     # Split the text into code blocks and other parts
#     parts = re.split(r'(```.*?```)', text, flags=re.DOTALL)
#     for i, part in enumerate(parts):
#         # Only process non-code blocks
#         if not part.startswith('```'):
#             part = escape_html(part)
#             part = re.sub(r'`(.*?)`', r'<code>\1</code>', part)
#             part = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', part)
#             part = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', part)
#             part = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', part)
#             part = re.sub(r'\[(.*?)\]\((https?://\S+)\)', r'<a href="\2">\1</a>', part)
#             parts[i] = part
#         else:
#             # For code blocks, extract the language hint (if any)
#             language_match = re.match(r'```(\w+)\s', part)
#             language = language_match.group(1) if language_match else ''
#             # Remove the language hint and backticks from the actual code
#             code_content = re.sub(r'```(\w+)?\s', '', part, count=1)
#             code_content = code_content.rstrip('`').rstrip()
#             # Escape HTML characters in code content
#             code_content = escape_html(code_content)
#             # Wrap the code with <pre> and <code>
#             parts[i] = f'<pre><code class="{language}">{code_content}</code></pre>'

#     # Reassemble the parts into the final HTML, removing extra newlines after code blocks
#     # text = ''.join(parts).replace('</pre>\n\n', '</pre>\n')
#     # return text
#     # Reassemble the parts into the final HTML
#     return ''.join(parts)   

# Check and update the global rate limit.
def check_global_rate_limit(max_requests_per_minute, global_request_count, rate_limit_reset_time):
    # Bypass rate limit check if max_requests_per_minute is set to 0
    if max_requests_per_minute == 0:
        return False, global_request_count, rate_limit_reset_time

    current_time = datetime.datetime.now()

    # Reset the rate limit counter if a minute has passed
    if current_time >= rate_limit_reset_time:
        global_request_count = 0
        rate_limit_reset_time = current_time + datetime.timedelta(minutes=1)

    # Check if the global request count exceeds the limit
    if global_request_count >= max_requests_per_minute:
        return True, global_request_count, rate_limit_reset_time  # Rate limit exceeded

    # Increment the request count as the rate limit has not been exceeded
    global_request_count += 1
    return False, global_request_count, rate_limit_reset_time

# logging functionalities
def log_message(chat_log_file, chat_log_max_size, message_type, user_id, message, chat_logging_enabled=True):
    if not chat_logging_enabled:
        return

    # Check if the current log file size exceeds the maximum size (now in bytes)
    if os.path.exists(chat_log_file) and os.path.getsize(chat_log_file) >= chat_log_max_size:
        rotate_log_file(chat_log_file)

    # Now proceed with logging
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(chat_log_file, 'a', encoding='utf-8') as log_file:
        log_file.write(f"{timestamp} - {message_type}({user_id}): {message}\n")

# rotate the log file
def rotate_log_file(log_file_path):
    # Rename the existing log file by adding a timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_log_file_path = f"{log_file_path}_{timestamp}"

    # Rename the current log file to the archive file name
    os.rename(log_file_path, archive_log_file_path)
