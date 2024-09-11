# api_get_duckduckgo_search.py

import asyncio
import logging
from urllib.parse import quote, unquote_plus
import datetime
import shutil
import re

# Configure logging
logger = logging.getLogger(__name__)

# Print term width horizontal line
def print_horizontal_line(length=50, character='-'):
    line = character * length
    logger.info(line)

async def get_duckduckgo_search(search_terms):
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

        return unique_text

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Error: {str(e)}"

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

    # Optional: Further processing to condense the information
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

# # === old method ===
# def parse_duckduckgo(text):
#     duckduckgo_pattern = r'(https://duckduckgo\.com/l/\?uddg=[^\s]+)'
#     matches = re.findall(duckduckgo_pattern, text)
#     cleaned_text = text
#     for match in matches:
#         cleaned_url = match.split('&rut=')[0]
#         original_url = unquote_plus(cleaned_url.split('uddg=')[1])
#         cleaned_text = cleaned_text.replace(match, original_url)
#     return cleaned_text

# if __name__ == "__main__":
#     if len(sys.argv) > 1:
#         search_term = ' '.join(sys.argv[1:])
#         asyncio.run(get_duckduckgo_search(search_term))
#     else:
#         print("Please provide a search term.")
