# api_get_duckduckgo_search.py

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
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print_horizontal_line()
        logger.info(f"[{timestamp}] DuckDuckGo searching: {search_terms}")
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

        # Check if agentic browsing is enabled
        if enable_agentic_browsing:
            # Send to sub-agent (OpenAI API) for further processing
            sub_agent_result = await sub_agent_openai_call(user_message, search_terms, unique_text)
            return sub_agent_result
        else:
            logger.info("Agentic browsing is disabled. Returning DuckDuckGo search results only.")
            return unique_text

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Error: {str(e)}"

# Function to clean up and parse the DuckDuckGo results
def parse_duckduckgo(text):
    duckduckgo_pattern = r'(https://duckduckgo\.com/l/\?uddg=[^\s]+)'
    matches = re.findall(duckduckgo_pattern, text)
    cleaned_text = text
    for match in matches:
        cleaned_url = match.split('&rut=')[0]
        original_url = unquote_plus(cleaned_url.split('uddg=')[1])
        cleaned_text = cleaned_text.replace(match, original_url)

    # Further clean up to remove empty lines and unnecessary spaces
    lines = cleaned_text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]  # Removes empty lines and strips whitespace

    concise_lines = []
    for line in cleaned_lines:
        if 'http' in line:
            url = line.split(' ')[0]  # Assumes URL is the first part of the line
            title = ' '.join(line.split(' ')[1:])  # The rest is title
            concise_line = f"{title} - {url}"  # Format: Title - URL
            concise_lines.append(concise_line)
        else:
            concise_lines.append(line)  # For lines without URLs

    return '\n'.join(concise_lines)

# OpenAI sub-agent call
async def sub_agent_openai_call(user_message, search_terms, search_results):
    """
    Pass the user's message, search terms, and DuckDuckGo results to the OpenAI API sub-agent for further processing.
    """
    try:
        # System message for sub-agent
        system_message = {
            "role": "system",
            "content": f"The user's input was: {user_message}\n"
                       f"The search term used was: {search_terms}\n"
                       f"The DuckDuckGo search results are:\n{search_results}\n"
                       "INSTRUCTIONS: Choose a webpage to visit for more information (list the linked URLs like `lynx --dump` does), "
                       "or respond with '0' if you think these results are enough to provide the needed information."
        }

        # OpenAI API request to the sub-agent
        response = openai.ChatCompletion.create(
            model=model_name,  # Use the model from config.ini
            messages=[system_message],
            temperature=temperature,  # Use temperature from config.ini
            max_tokens=max_tokens,  # Use max_tokens from config.ini
            timeout=timeout  # Use timeout from config.ini
        )

        # Extract the sub-agent's response
        agent_reply = response['choices'][0]['message']['content']

        if agent_reply == "0":
            return f"Sub-agent determined no further browsing needed.\nSearch results:\n{search_results}"
        else:
            # If agent chose a link, fetch its content
            chosen_link = extract_link_from_results(search_results, agent_reply)
            page_content = await fetch_link_content(chosen_link)
            return f"Sub-agent browsed link {agent_reply} and fetched this content:\n{page_content}"

    except Exception as e:
        logger.error(f"Error in sub-agent call: {str(e)}")
        return f"Error in sub-agent call: {str(e)}"

# Extract a link from the search results based on the number
def extract_link_from_results(search_results, link_number):
    lines = search_results.split('\n')
    link = ''
    for line in lines:
        if 'http' in line and str(link_number) in line:
            link = line.split('http')[1].split(' ')[0]
            break
    return 'http' + link

# Fetch content from a link using lynx or requests
async def fetch_link_content(link):
    logger.info(f"Fetching content from link: {link}")
    process = await asyncio.create_subprocess_exec(
        "lynx", "--dump", link,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_message = stderr.decode('utf-8').strip()
        logger.error(f"Error: {error_message}")
        return f"Error: {error_message}"

    page_content = stdout.decode('utf-8')

    # Limit the content size if enabled
    if enable_content_size_limit and len(page_content) > max_content_size:
        logger.info(f"Limiting page content to {max_content_size} characters.")
        page_content = page_content[:max_content_size] + "\n\n[Content truncated due to size limit.]"

    return page_content

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

# def parse_duckduckgo(text):
#     duckduckgo_pattern = r'(https://duckduckgo\.com/l/\?uddg=[^\s]+)'
#     matches = re.findall(duckduckgo_pattern, text)
#     cleaned_text = text
#     for match in matches:
#         cleaned_url = match.split('&rut=')[0]
#         original_url = unquote_plus(cleaned_url.split('uddg=')[1])
#         cleaned_text = cleaned_text.replace(match, original_url)

#     # Further clean up to remove empty lines and unnecessary spaces
#     lines = cleaned_text.split('\n')
#     cleaned_lines = [line.strip() for line in lines if line.strip()]  # Removes empty lines and strips whitespace

#     # Optional: Further processing to condense the information
#     concise_lines = []
#     for line in cleaned_lines:
#         if 'http' in line:
#             url = line.split(' ')[0]  # Assumes URL is the first part of the line
#             title = ' '.join(line.split(' ')[1:])  # The rest is title
#             concise_line = f"{title} - {url}"  # Format: Title - URL
#             concise_lines.append(concise_line)
#         else:
#             concise_lines.append(line)  # For lines without URLs

#     return '\n'.join(concise_lines)

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
