# modules.py
import json
import datetime
from transformers import GPT2Tokenizer
import re

# count tokens
def count_tokens(text, tokenizer):
    return len(tokenizer.encode(text))

# read total token usage
def read_total_token_usage(token_usage_file):
    try:
        with open(token_usage_file, 'r') as file:
            data = json.load(file)
        current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        # Return the usage for the current date, or 0 if not present
        return data.get(current_date, 0)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is invalid, return 0
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

# convert markdowns to html
def escape_html(text):
    # Escape HTML special characters
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

def markdown_to_html(text):
    # Split the text into code blocks and other parts
    parts = re.split(r'(```.*?```)', text, flags=re.DOTALL)
    for i, part in enumerate(parts):
        # Only process non-code blocks
        if not part.startswith('```'):
            part = escape_html(part)
            part = re.sub(r'`(.*?)`', r'<code>\1</code>', part)
            part = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', part)
            part = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', part)
            part = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', part)
            part = re.sub(r'\[(.*?)\]\((https?://\S+)\)', r'<a href="\2">\1</a>', part)
            parts[i] = part
        else:
            # For code blocks, extract the language hint (if any)
            language_match = re.match(r'```(\w+)\s', part)
            language = language_match.group(1) if language_match else ''
            # Remove the language hint and backticks from the actual code
            code_content = re.sub(r'```(\w+)?\s', '', part, count=1)
            code_content = code_content.rstrip('`').rstrip()
            # Escape HTML characters in code content
            code_content = escape_html(code_content)
            # Wrap the code with <pre> and <code>
            parts[i] = f'<pre><code class="{language}">{code_content}</code></pre>'

    # Reassemble the parts into the final HTML, removing extra newlines after code blocks
    # text = ''.join(parts).replace('</pre>\n\n', '</pre>\n')
    # return text
    # Reassemble the parts into the final HTML
    return ''.join(parts)   

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