# url_handler.py
# v0.60.1
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import time
import logging
import re
import asyncio
import json

# Toggle this to use the full description or a snippet.
USE_SNIPPET_FOR_DESCRIPTION = False

# If we're using a snippet of the description, maximum number of lines to include
DESCRIPTION_MAX_LINES = 30

# Configure logging
logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Helper function to format duration from seconds to H:M:S
def format_duration(duration):
    if not duration:
        return 'No duration available'
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    else:
        return f"{minutes}m {seconds}s"

# i.e. for youtube videos
async def fetch_youtube_details(url, max_retries=3, base_delay=5):
    command = ["yt-dlp", "--user-agent",
               "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
               "--dump-json", url]

    for attempt in range(max_retries):
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if stderr and process.returncode != 0:
            logger.warning(f"Attempt {attempt + 1} failed: {stderr.decode()}")
            if attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying after {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("All retry attempts failed.")
        else:
            try:
                video_details = json.loads(stdout.decode())
                duration_formatted = format_duration(video_details.get('duration'))                

                if USE_SNIPPET_FOR_DESCRIPTION:
                    # Get the snippet if the flag is set to True.
                    description_text = get_description_snippet(video_details.get('description', 'No description available'))
                else:
                    # Use the full description if the flag is set to False.
                    description_text = video_details.get('description', 'No description available')

                filtered_details = {
                    'title': video_details.get('title', 'No title available'),
                    # 'duration': video_details.get('duration', 'No duration available'),
                    'duration': duration_formatted,                    
                    'channel': video_details.get('uploader', 'No channel information available'),
                    'upload_date': video_details.get('upload_date', 'No upload date available'),
                    'views': video_details.get('view_count', 'No views available'),
                    'likes': video_details.get('like_count', 'No likes available'),
                    'average_rating': video_details.get('average_rating', 'No rating available'),
                    'comment_count': video_details.get('comment_count', 'No comment count available'),
                    'channel_id': video_details.get('channel_id', 'No channel ID available'),
                    'video_id': video_details.get('id', 'No video ID available'),
                    'tags': video_details.get('tags', ['No tags available']),
                    'description': description_text,
                }

                logger.info(f"Fetched YouTube details successfully for URL: {url}")
                return filtered_details
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from yt-dlp output: {e}")
                return None
    return None

# Helper function to get up to n lines from the description
def get_description_snippet(description, max_lines=DESCRIPTION_MAX_LINES):
    lines = description.split('\n')
    snippet = '\n'.join(lines[:max_lines])
    return snippet

# Regular expression for extracting the YouTube video ID
YOUTUBE_REGEX = (
    r'(https?://)?(www\.)?'
    '(youtube|youtu|youtube-nocookie)\.(com|be)/'
    '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

def extract_youtube_video_id(url):
    match = re.match(YOUTUBE_REGEX, url)
    if not match:
        raise ValueError("Invalid YouTube URL")
    return match.group(6)

# for parsing types of urls
async def process_url_message(message_text):
    urls = re.findall(r'(https?://\S+)', message_text)
    context_messages = []

    for url in urls:
        if not re.match(YOUTUBE_REGEX, url):
            logger.info(f"Skipping non-YouTube URL: {url}")
            continue

        try:
            # At this point, we're sure it's a YouTube URL, so we process it.
            video_id = extract_youtube_video_id(url)
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"Processing YouTube URL: {youtube_url}")
            details = await fetch_youtube_details(youtube_url)
            if details:
                description_snippet = get_description_snippet(details['description'], DESCRIPTION_MAX_LINES)
                context_message = (
                    f"[INFO] Details for the URL: {youtube_url}\n"
                    f"Title: {details['title']}\n"
                    f"Duration: {details['duration']}\n"
                    f"Channel: {details['channel']}\n"
                    f"Upload date: {details['upload_date']}\n"
                    f"Views: {details['views']}\n"
                    f"Likes: {details['likes']}\n"
                    f"Rating: {details['average_rating']}\n"
                    f"Comments: {details['comment_count']}\n"
                    f"Tags: {', '.join(details['tags'])}\n"
                    f"Description: {description_snippet}\n"
                    # f"[ If user didn't request anything special about the URL, PASS THEM I.E. THE ABOVEMENTIONED INFORMATION. ]\n"
                )
                context_messages.append(context_message)
                logger.info(f"Added context message: {context_message}")
            else:
                logger.warning(f"No details fetched for YouTube URL: {youtube_url}")
        except ValueError as e:
            logger.error(f"Invalid YouTube URL encountered: {url} - {str(e)}")
        except Exception as e:
            logger.error(f"Failed to process YouTube URL {youtube_url}: {str(e)}")
    
    return context_messages
