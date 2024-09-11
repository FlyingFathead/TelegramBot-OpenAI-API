# api_get_duckduckgo_search.py

import httpx
import json
import asyncio
import logging
from urllib.parse import quote, unquote_plus
import datetime
import re
import openai  # Add the OpenAI module to make the API request
import configparser  # Add configparser to read from config.ini

# Configure logging
logger = logging.getLogger(__name__)

# Load the configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Retrieve values from config.ini
model_name = config.get('DEFAULT', 'Model', fallback='gpt-4')
temperature = config.getfloat('DEFAULT', 'Temperature', fallback=0.7)
timeout = config.getint('DEFAULT', 'Timeout', fallback=60)
max_tokens = config.getint('DEFAULT', 'MaxTokens', fallback=2048)
enable_agentic_browsing = config.getboolean('DuckDuckGo', 'EnableAgenticBrowsing', fallback=False)
enable_content_size_limit = config.getboolean('DuckDuckGo', 'EnableContentSizeLimit', fallback=False)
max_content_size = config.getint('DuckDuckGo', 'MaxContentSize', fallback=10000)  # Maximum content size in characters

# Print term width horizontal line
def print_horizontal_line(length=50, character='-'):
    line = character * length
    logger.info(line)

# Main DuckDuckGo search function
async def get_duckduckgo_search(search_terms, user_message):
    try:
        # Check if agentic browsing is enabled before doing anything else
        if not enable_agentic_browsing:
            logger.info("Agentic browsing is disabled. Returning basic DuckDuckGo results without sub-agent processing.")
            
            # Perform the DuckDuckGo search and return the raw results without involving sub-agent
            formatted_query = quote(search_terms)
            search_url = f"https://duckduckgo.com/html/?q={formatted_query}"

            # Using asyncio subprocess to run lynx dump
            process = await asyncio.create_subprocess_exec(
                "lynx", "--dump", search_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_message = stderr.decode('utf-8').strip()
                logger.error(f"Error: {error_message}")
                return f"Error: {error_message}"

            response_text = stdout.decode('utf-8')
            cleaned_text = parse_duckduckgo(response_text)  # Clean the text by removing DuckDuckGo links

            # Initialize a set to keep track of the links we've seen
            seen_links = set()
            unique_links = []
            
            lines = cleaned_text.split('\n')
            for line in lines:
                if 'http' in line:
                    link = 'http' + line.split('http')[1].split(' ')[0]
                    if link not in seen_links:
                        seen_links.add(link)
                        unique_links.append(line)
                else:
                    unique_links.append(line)
            
            unique_text = '\n'.join(unique_links)
            logger.info(unique_text)

            # Directly return the DuckDuckGo search results as formatted text
            return format_for_telegram_html(unique_text)

        # Continue if agentic browsing is enabled
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print_horizontal_line()
        logger.info(f"[{timestamp}] Agentic browsing-enabled DuckDuckGo searching: {search_terms}")
        print_horizontal_line()

        formatted_query = quote(search_terms)
        search_url = f"https://duckduckgo.com/html/?q={formatted_query}"

        # Using asyncio subprocess to run lynx dump
        process = await asyncio.create_subprocess_exec(
            "lynx", "--dump", search_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode('utf-8').strip()
            logger.error(f"Error: {error_message}")
            return f"Error: {error_message}"

        response_text = stdout.decode('utf-8')
        cleaned_text = parse_duckduckgo(response_text)  # Clean the text by removing DuckDuckGo links

        # Initialize a set to keep track of the links we've seen
        seen_links = set()
        unique_links = []
        
        lines = cleaned_text.split('\n')
        for line in lines:
            if 'http' in line:
                link = 'http' + line.split('http')[1].split(' ')[0]
                if link not in seen_links:
                    seen_links.add(link)
                    unique_links.append(line)
            else:
                unique_links.append(line)
        
        unique_text = '\n'.join(unique_links)
        logger.info(unique_text)
        print_horizontal_line()

        # Call the sub-agent to further process results, only if agentic browsing is enabled
        sub_agent_result = await sub_agent_openai_call(user_message, search_terms, unique_text)

        # Failsafe: if sub-agent result is empty, return the DuckDuckGo results instead
        if not sub_agent_result.strip():
            logger.warning("Sub-agent returned empty. Falling back to DuckDuckGo results.")
            return format_for_telegram_html(unique_text)

        return sub_agent_result

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Error: {str(e)}"

# OpenAI sub-agent call handler
async def sub_agent_openai_call(user_message, search_terms, search_results, retries=3, timeout=30):
    """
    Pass the user's message, search terms, and DuckDuckGo results to the OpenAI API sub-agent for further processing.
    Includes retry logic to handle failures.
    """
    attempt = 0
    while attempt < retries:
        try:
            logger.info(f"Sub-agent attempt {attempt + 1}: Preparing to send API request to OpenAI.")

            # Prepare the system message for the sub-agent
            system_message = {
                "role": "system",
                "content": f"The user's input was: {user_message}\n"
                           f"The search term used was: {search_terms}\n"
                           f"The DuckDuckGo search results are:\n{search_results}\n"
                           "You may call the `visit_webpage` function if you need to visit a webpage for further details."
            }

            # Define the available functions
            functions = [
                {
                    "name": "visit_webpage",
                    "description": "Fetch the contents of a webpage for further analysis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL of the webpage to visit."
                            }
                        },
                        "required": ["url"]
                    }
                }
            ]

            # Payload for the API request
            payload = {
                "model": model_name,  # Use the model from config.ini
                "messages": [system_message],
                "functions": functions,  # Add the functions to the payload
                "function_call": "auto",  # Let the model decide if/when to call the function
                "temperature": temperature,  # Use temperature from config.ini
                "max_tokens": max_tokens  # Use max_tokens from config.ini
            }

            # Make the API request using httpx
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai.api_key}"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=timeout
                )

            response_json = response.json()
            logger.info(f"Sub-agent API request completed. Response: {response_json}")

            # Check if OpenAI returned a function call
            if 'function_call' in response_json['choices'][0]['message']:
                function_call = response_json['choices'][0]['message']['function_call']
                function_name = function_call['name']
                logger.info(f"Sub-agent requested function call: {function_name}")

                # Handle the custom function calls
                if function_name == 'visit_webpage':
                    # Extract the arguments from the function call
                    arguments = json.loads(function_call.get('arguments', '{}'))
                    url = arguments.get('url', '')

                    logger.info(f"Function 'visit_webpage' called with arguments: {arguments}")

                    # Attempt to fetch content from the provided URL
                    if url:
                        try:
                            logger.info(f"Attempting to fetch content from URL: {url}")
                            page_content = await fetch_link_content(url)
                            
                            # Check if the content is empty or invalid
                            if not page_content or not page_content.strip():
                                logger.error(f"Empty content fetched from {url}. Returning DuckDuckGo results.")
                                return format_for_telegram_html(search_results)

                            logger.info(f"Fetched content from {url}, content length: {len(page_content)} characters")
                            return f"Sub-agent fetched the following content from {url}:\n\n{page_content}"

                        except Exception as e:
                            logger.error(f"Error while fetching content from {url}: {str(e)}. Returning DuckDuckGo results.")
                            return format_for_telegram_html(search_results)
                    else:
                        logger.error("No valid URL provided by sub-agent. Returning DuckDuckGo results.")
                        return format_for_telegram_html(search_results)

            # If no function call, return the sub-agent's reply as is
            agent_reply = response_json['choices'][0]['message']['content']
            logger.info(f"Sub-agent reply: {agent_reply}")
            return format_for_telegram_html(agent_reply)

        except Exception as e:
            logger.error(f"Attempt {attempt + 1}: Error during sub-agent API request - {str(e)}")
            attempt += 1
            await asyncio.sleep(2)  # Optional delay between retries

    logger.error(f"All {retries} attempts failed. Returning DuckDuckGo search results.")
    return format_for_telegram_html(search_results)

# Fetch content from a link using lynx or requests
async def fetch_link_content(link):
    if not link:
        logger.error("No valid link provided to fetch content from.")
        return "Error: No valid link provided."

    logger.info(f"Starting to fetch content from link: {link}")
    
    try:
        # Starting subprocess execution
        logger.info(f"Running lynx dump command for link: {link}")
        process = await asyncio.create_subprocess_exec(
            "lynx", "--dump", link,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Collecting stdout and stderr
        stdout, stderr = await process.communicate()

        # Log process return code
        logger.info(f"Lynx process completed with return code: {process.returncode}")

        if process.returncode != 0:
            error_message = stderr.decode('utf-8').strip()
            logger.error(f"Error during lynx execution: {error_message}")
            
            # Fail fast here and return original search results
            return f"Error: Unable to access {link}. Fallback to search results."
        
        # Decoding the response text from stdout
        page_content = stdout.decode('utf-8')
        logger.info(f"Lynx dump output received. Content length: {len(page_content)} characters")

        # **Filter out binary content like base64 image data**
        if "data:image/" in page_content:
            logger.warning("Binary image data detected, skipping this content.")
            return "[Binary image data detected, content skipped.]"

        # Limiting the content size if enabled
        if enable_content_size_limit and len(page_content) > max_content_size:
            logger.info(f"Limiting page content to {max_content_size} characters.")
            page_content = page_content[:max_content_size] + "\n\n[Content truncated due to size limit.]"

        formatted_content = format_for_telegram_html(page_content)
        logger.info(f"Formatted content ready for return, final content length: {len(formatted_content)} characters")

        return formatted_content

    except Exception as e:
        logger.error(f"Exception occurred during fetch_link_content: {str(e)}")
        return f"Error: Failed to fetch content from {link}. Details: {str(e)}"

# Clean DuckDuckGo search results
def parse_duckduckgo(text):
    # General URL pattern to capture all URLs
    url_pattern = r'(http[s]?://[^\s]+)'
    cleaned_text = text

    # Replace DuckDuckGo obfuscated links with original ones
    duckduckgo_pattern = r'(https://duckduckgo\.com/l/\?uddg=[^\s]+)'
    matches = re.findall(duckduckgo_pattern, text)
    for match in matches:
        cleaned_url = match.split('&rut=')[0]
        original_url = unquote_plus(cleaned_url.split('uddg=')[1])
        cleaned_text = cleaned_text.replace(match, original_url)

    # Further clean up to remove empty lines and unnecessary spaces
    lines = cleaned_text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]  # Removes empty lines and strips whitespace

    # Process and format lines with URLs, excluding DuckDuckGo links
    concise_lines = []
    for line in cleaned_lines:
        url_match = re.search(url_pattern, line)
        if url_match:
            url = url_match.group(0)  # Extract the URL
            # Exclude any URLs that contain 'duckduckgo.com'
            if 'duckduckgo.com' not in url:
                title = line.replace(url, '').strip()  # Remove the URL from the line to get the title
                concise_line = f"{title} - {url}" if title else url  # Format: Title - URL
                concise_lines.append(concise_line)
        else:
            concise_lines.append(line)  # For lines without URLs

    return format_for_telegram_html('\n'.join(concise_lines))

# Format for Telegram HTML
def format_for_telegram_html(text):
    """
    Formats text to be Telegram-compliant, removing <br> tags and converting special characters,
    but preserving valid HTML tags like <a>, <b>, <i>, etc.
    """
    # Remove <br> tags completely (instead of converting to newlines)
    text = re.sub(r"<br\s*/?>", "", text)

    # Escape special characters, but leave valid HTML tags intact
    # Handles &, <, and >, but preserves valid HTML tags like <a>, <b>, <i>
    def escape_non_html_entities(match):
        char = match.group(0)
        if char == "&":
            return "&amp;"
        return char

    # Escape & but do not touch valid HTML tags
    text = re.sub(r"[&](?!#?\w+;)", escape_non_html_entities, text)

    # Remove extra newlines (more than 2 newlines in a row)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text

# # Format for Telegram HTML
# def format_for_telegram_html(text):
#     """
#     Formats text to be Telegram-compliant, escaping special characters and converting basic HTML
#     tags like <br> to newline characters.
#     """
#     text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")

#     # Escape special characters
#     replacements = {
#         "&": "&amp;",
#         "<": "&lt;",
#         ">": "&gt;",
#         '"': "&quot;",
#         "'": "&#39;"
#     }

#     for key, value in replacements.items():
#         text = text.replace(key, value)

#     # Remove multiple newlines
#     text = re.sub(r"\n{3,}", "\n\n", text)

#     return text

# import asyncio
# import logging
# from urllib.parse import quote, unquote_plus
# import datetime
# import shutil
# import re

# # Configure logging
# logger = logging.getLogger(__name__)

# # Print term width horizontal line
# def print_horizontal_line(length=50, character='-'):
#     line = character * length
#     logger.info(line)

# async def get_duckduckgo_search(search_terms):
#     try:
#         timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         print_horizontal_line()
#         logger.info(f"[{timestamp}] DuckDuckGo searching: {search_terms}")
#         print_horizontal_line()

#         formatted_query = quote(search_terms)
#         search_url = f"https://duckduckgo.com/html/?q={formatted_query}"

#         # Using asyncio subprocess to run lynx dump
#         process = await asyncio.create_subprocess_exec(
#             "lynx", "--dump", search_url,
#             stdout=asyncio.subprocess.PIPE,
#             stderr=asyncio.subprocess.PIPE
#         )
#         stdout, stderr = await process.communicate()

#         if process.returncode != 0:
#             error_message = stderr.decode('utf-8').strip()
#             logger.error(f"Error: {error_message}")
#             return f"Error: {error_message}"

#         response_text = stdout.decode('utf-8')
#         cleaned_text = parse_duckduckgo(response_text)  # Clean the text by removing DuckDuckGo links

#         # Initialize a set to keep track of the links we've seen
#         seen_links = set()
#         unique_links = []
        
#         lines = cleaned_text.split('\n')
#         for line in lines:
#             if 'http' in line:
#                 link = 'http' + line.split('http')[1].split(' ')[0]
#                 if link not in seen_links:
#                     seen_links.add(link)
#                     unique_links.append(line)
#             else:
#                 unique_links.append(line)
        
#         unique_text = '\n'.join(unique_links)
#         logger.info(unique_text)
#         print_horizontal_line()

#         return unique_text

#     except Exception as e:
#         logger.error(f"Error: {str(e)}")
#         return f"Error: {str(e)}"

# # # === old method ===
# # def parse_duckduckgo(text):
# #     duckduckgo_pattern = r'(https://duckduckgo\.com/l/\?uddg=[^\s]+)'
# #     matches = re.findall(duckduckgo_pattern, text)
# #     cleaned_text = text
# #     for match in matches:
# #         cleaned_url = match.split('&rut=')[0]
# #         original_url = unquote_plus(cleaned_url.split('uddg=')[1])
# #         cleaned_text = cleaned_text.replace(match, original_url)
# #     return cleaned_text

# # if __name__ == "__main__":
# #     if len(sys.argv) > 1:
# #         search_term = ' '.join(sys.argv[1:])
# #         asyncio.run(get_duckduckgo_search(search_term))
# #     else:
# #         print("Please provide a search term.")
