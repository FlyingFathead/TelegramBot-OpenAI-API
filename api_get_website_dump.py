# api_get_website_dump.py

import urllib.parse
import subprocess
import logging
import tiktoken  # for token counting
import sys
import asyncio
import re

# Configuration
USE_DOMAIN_RESTRICTIONS = False  # Flag to enable or disable domain restriction logic
ALLOW_ONLY = True  # If True, only allowed domains are permitted. If False, only disallowed domains are blocked.

ALLOWED_DOMAINS = [
    '*.fi',        # Allow all .fi domains
    'google.com',  # Allow google.com and all subdomains
    'openai.com',  # Allow openai.com and all subdomains
]

DISALLOWED_DOMAINS = [
    # Add specific domains or patterns you want to disallow, if any
]

# check if the domain is allowed or not
def is_domain_allowed(url):
    if not USE_DOMAIN_RESTRICTIONS:
        return True  # If restrictions are not used, allow all domains

    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc

    if ALLOW_ONLY:
        # In "allow only" mode, allow only domains in ALLOWED_DOMAINS
        for allowed in ALLOWED_DOMAINS:
            if re.fullmatch(allowed.replace('*', '.*'), domain):
                return True
        logging.warning(f"Domain not allowed: {domain}")
        return False
    else:
        # In "disallow only" mode, disallow only domains in DISALLOWED_DOMAINS
        for disallowed in DISALLOWED_DOMAINS:
            if re.fullmatch(disallowed.replace('*', '.*'), domain):
                logging.warning(f"Disallowed domain: {domain}")
                return False
        return True  # Allow all other domains if not disallowed

# get the website dump
async def get_website_dump(url, max_tokens=10000):
    """
    Fetches the content of a website using lynx --dump and returns it as a string.
    Ensures the content doesn't exceed the specified max token count.
    Cleans up unnecessary content and retains meaningful newlines.
    """

    # Check if the domain is allowed
    if not is_domain_allowed(url):
        error_message = f"Error: Domain not allowed for URL: {url}"
        logging.error(error_message)
        return error_message

    try:
        # Execute the lynx command to fetch the website content
        result = subprocess.run(['lynx', '--dump', url], capture_output=True, text=True, timeout=15)

        # Check if the command was successful
        if result.returncode == 0:
            content = result.stdout

            # Filter out non-informative content using regex
            # content = re.sub(r'\[.*?\]|\(BUTTON\)|\s{2,}', ' ', content)  # Remove links, buttons, and excessive spaces

            # Replace multiple spaces and tabs with a single space
            content = re.sub(r'\s+', ' ', content)

            # Keep meaningful newlines (keep single newlines, avoid empty lines)
            content = re.sub(r'\s*\n\s*', '\n', content)  # Clean up newlines
            content = re.sub(r'\n{2,}', '\n', content)  # Ensure no multiple consecutive newlines

            # Use the correct encoding for GPT-4o
            enc = tiktoken.encoding_for_model("gpt-4o")  # Load the appropriate tokenizer for GPT-4o
            tokens = enc.encode(content)

            # Log the fetched content and token count
            logging.info(f"Upon user's request, fetched content from: {url}")
            logging.info(f"Token count: {len(tokens)}")

            # If the token count exceeds the max_tokens, truncate the content
            if len(tokens) > max_tokens:
                # Trim tokens to fit within the max_tokens
                tokens = tokens[:max_tokens]
                # Decode the trimmed tokens back to text
                content = enc.decode(tokens)
                logging.info(f"Content truncated to {max_tokens} tokens.")

            return content.strip()
        else:
            error_message = f"Error: Unable to fetch content from {url}. Return code: {result.returncode}"
            logging.error(error_message)
            return error_message

    except subprocess.TimeoutExpired:
        error_message = f"Error: Timed out while trying to fetch content from {url}."
        logging.error(error_message)
        return error_message

    except Exception as e:
        error_message = f"Error: An exception occurred while fetching content from {url}: {str(e)}"
        logging.error(error_message)
        return error_message

# Tester to run the script directly
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python api_get_website_dump.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    
    # Set up basic logging to console
    logging.basicConfig(level=logging.INFO)

    # Run the function and print the result
    result = asyncio.run(get_website_dump(url))
    print(result)
