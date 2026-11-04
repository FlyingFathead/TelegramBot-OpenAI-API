# api_get_website_dump.py

import urllib.parse
from api_get_duckduckgo_search import _run_lynx_dump
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
        logging.warning("Domain restrictions are NOT in use. All domains are allowed.")
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
        error_message = f"Error: Cannot browse the address, not allowed for URL: {url}"
        logging.error(error_message)
        return error_message

    try:
        # Lynx performs the network request and produces the page dump.
        content = await asyncio.wait_for(_run_lynx_dump(url, request_timeout=15), timeout=15)
        content = re.sub(r'[^\S\n]+', ' ', content).strip()
        content = re.sub(r'\n{3,}', '\n\n', content)
        enc = tiktoken.encoding_for_model("gpt-4o")
        tokens = enc.encode(content, disallowed_special=())
        return enc.decode(tokens[:max_tokens]) if len(tokens) > max_tokens else content

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
