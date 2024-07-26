# elasticsearch_functions.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Import necessary libraries
import re
import asyncio
import logging
import feedparser  # Make sure to install feedparser: pip install feedparser
from rss_parser import (
    get_bbc_business,
    get_bbc_science_environment,
    get_bbc_top_stories,
    get_cnn_us_news,
    get_defcon_status,
    get_hs_etusivu,
    get_hs_uusimmat,
    get_il_urheilu,
    get_is_digitoday,
    get_is_horoskoopit,
    get_is_tuoreimmat,
    get_is_taloussanomat,
    get_is_tiede,
    get_is_ulkomaat,
    get_yle_latest_news,
    get_yle_kotimaa,    
    get_yle_main_news,
    get_yle_most_read,
    get_yle_uusimaa
)  # Import the functions

# from bs4 import BeautifulSoup

# here we can run our separate helper functions according to elasticsearch's matches

# rss feed test
async def fetch_rss_feed(context, update, feed_url):
    # Fetch and parse the RSS feed
    feed = feedparser.parse(feed_url)
    entries_summary = "\n".join([entry.title + ": " + entry.link for entry in feed.entries[:5]])  # Example: Get top 5 entries
    
    # Send the feed summary back to the user
    await context.bot.send_message(chat_id=update.effective_chat.id, text=entries_summary)

# rss // fetch and format
async def fetch_and_format_rss_feed(feed_url):
    # Fetch the RSS feed
    feed = feedparser.parse(feed_url)
    
    # Format the entries for model consumption, focusing on titles and possibly summaries
    formatted_entries = [{"title": entry.title, "summary": entry.summary} for entry in feed.entries[:5]]
    
    # Return formatted data
    return formatted_entries

# rss // update context
async def update_context_with_rss(context, update, es_context, chat_history_with_system_message):
    # Specify the RSS feed URL - this would be dynamic based on your requirements
    feed_url = "http://example.com/rss"
    
    # Fetch and format the latest entries
    rss_data = await fetch_and_format_rss_feed(feed_url)
    
    # Incorporate the RSS data into the chat history or context
    # Here, we add the RSS data as a system message; adjust the structure as needed for your model
    rss_context_entry = {"role": "system", "content": f"Latest RSS Feed Data: {rss_data}"}
    chat_history_with_es_context = [rss_context_entry] + chat_history_with_system_message
    
    return chat_history_with_es_context

# Function definition
async def function_x(context, update, chat_history_with_system_message):
    logging.info("Executing function_x")
    
    # Your function's internal logic here...
    await asyncio.sleep(1)  # Simulating an I/O-bound task with async sleep

    # Message to be appended to the context
    execution_message = "Function X executed."
    
    # Append this execution notice to the chat history or context
    chat_history_with_es_context = chat_history_with_system_message + [{"role": "system", "content": execution_message}]
    
    # Optionally send a confirmation message back to the user (can be omitted if not needed)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=execution_message)
    
    # Return the updated chat history/context for further use
    return chat_history_with_es_context

# Generic function to fetch, format, and send RSS feeds
async def fetch_and_send_rss(context, update, feed_function, feed_name, chat_history_with_system_message, language):
    logging.info(f"Fetching {feed_name} RSS feed")

    # Fetch the RSS feed
    rss_result = feed_function()

    # Initialize entries_summary
    entries_summary = ""

    # Extract the relevant content from the RSS result
    if rss_result['type'] == 'text':
        entries_summary = rss_result['html']
    else:
        if language == 'fi':
            entries_summary = f"{feed_name}-uutissyötteen haku epäonnistui! Sori!"
        elif language == 'en':
            entries_summary = f"{feed_name} feed fetch failed! Sorry!"
        else:
            entries_summary = f"{feed_name} feed fetch failed!"

    # Sanitize the HTML content
    entries_summary = sanitize_html(entries_summary)

    # Prepare the execution message based on language
    if language == 'fi':
        # execution_message = f"Tässä {feed_name}:\n\n{entries_summary}"
        execution_message = f"{entries_summary}"
    elif language == 'en':
        # execution_message = f"Here are the latest news from {feed_name}:\n\n{entries_summary}"
        execution_message = f"{entries_summary}"
    else:
        execution_message = entries_summary

    # Split the message if it's too long
    messages = split_message(execution_message, max_length=4000)

    # Send each part of the message
    for part in messages:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=part, parse_mode='HTML')

    # Append this execution notice to the chat history or context
    chat_history_with_es_context = chat_history_with_system_message + [{"role": "system", "content": execution_message}]

    # Return the updated chat history/context for further use
    return chat_history_with_es_context

#
# > mapping action token to function
#

# Mapping tokens to functions
action_token_functions = {
    "<[fetch_rss]>": lambda context, update: fetch_rss_feed(context, update, "http://example.com/rss"),  # Example RSS feed URL
    "<[function_x_token]>": function_x,
    "<[get_bbc_business]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_bbc_business, "BBC News Business (bbc.co.uk)", chat_history_with_system_message, 'en'),
    "<[get_bbc_science_environment]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_bbc_science_environment, "BBC News Science & Environment (bbc.co.uk)", chat_history_with_system_message, 'en'),
    "<[get_bbc_top_stories]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_bbc_top_stories, "BBC News, Top Stories (bbc.co.uk)", chat_history_with_system_message, 'en'),
    "<[get_cnn_us_news]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_cnn_us_news, "CNN News, U.S. (cnn.com)", chat_history_with_system_message, 'en'),
    "<[get_defcon_status]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_defcon_status, "Current DEFCON Status", chat_history_with_system_message, 'en'),    
    "<[get_is_digitoday]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_is_digitoday, "Ilta-Sanomat (is.fi) Digitoday-uutiset", chat_history_with_system_message, 'fi'),
    "<[get_hs_etusivu]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_hs_etusivu, "Helsingin Sanomat (hs.fi) etusivun uutiset", chat_history_with_system_message, 'fi'),    
    "<[get_hs_uusimmat]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_hs_uusimmat, "Helsingin Sanomat (hs.fi) uusimmat uutiset", chat_history_with_system_message, 'fi'),
    "<[get_il_urheilu]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_il_urheilu, "Iltalehti (il.fi) urheilu-uutiset", chat_history_with_system_message, 'fi'),    
    "<[get_is_horoskoopit]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_is_horoskoopit, "Ilta-Sanomat (is.fi) horoskoopit", chat_history_with_system_message, 'fi'),
    "<[get_is_tiede]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_is_tiede, "Ilta-Sanomat (is.fi) tiedeuutiset", chat_history_with_system_message, 'fi'),
    "<[get_is_tuoreimmat]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_is_tuoreimmat, "Ilta-Sanomat (is.fi), tuoreimmat uutiset", chat_history_with_system_message, 'fi'),
    "<[get_is_taloussanomat]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_is_taloussanomat, "Taloussanomat (is.fi/taloussanomat) tuoreimmat", chat_history_with_system_message, 'fi'),
    "<[get_is_ulkomaat]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_is_ulkomaat, "Ilta-Sanomat (is.fi) ulkomaat", chat_history_with_system_message, 'fi'),    
    "<[get_yle_kotimaa]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_yle_kotimaa, "YLE (yle.fi) kotimaan uutiset", chat_history_with_system_message, 'fi'),
    "<[get_yle_latest_news]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_yle_latest_news, "YLE (yle.fi) tuoreimmat uutiset", chat_history_with_system_message, 'fi'),
    "<[get_yle_main_news]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_yle_main_news, "YLE (yle.fi) pääuutiset", chat_history_with_system_message, 'fi'),
    "<[get_yle_most_read]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_yle_most_read, "YLE (yle.fi) luetuimmat", chat_history_with_system_message, 'fi'),
    "<[get_yle_uusimaa]>": lambda context, update, chat_history_with_system_message: fetch_and_send_rss(context, update, get_yle_uusimaa, "YLE (yle.fi) Uusimaa", chat_history_with_system_message, 'fi'),
}

#
# > tools to fix the output
#

def sanitize_html(content):
    # Use regex to remove unsupported HTML tags
    # List of supported tags by Telegram
    supported_tags = ['b', 'i', 'a', 'code', 'pre', 'strong', 'em', 'u', 'ins', 's', 'strike', 'del']
    
    # Function to remove tags not in the supported list
    def remove_unsupported_tags(match):
        tag = match.group(1)
        if tag not in supported_tags:
            return ''
        return match.group(0)
    
    # Remove all unsupported tags
    content = re.sub(r'</?([a-zA-Z0-9]+).*?>', remove_unsupported_tags, content)
    
    return content

def split_message(message, max_length=4000):
    # Split message into chunks of max_length or less, ending at a sentence boundary or newline
    def chunk_text(text):
        while len(text) > max_length:
            split_index = text.rfind('\n', 0, max_length)
            if split_index == -1:
                split_index = text.rfind('. ', 0, max_length)
                if split_index == -1:
                    split_index = max_length
            yield text[:split_index + 1].strip()
            text = text[split_index + 1:].strip()
        yield text

    return list(chunk_text(message))

# In this setup:
# 
# - `fetch_rss_feed` is a generic function that takes a feed URL and fetches the top 5 entries, sending a summary back to the user.
# - The `action_token_functions` dictionary includes a token `<[fetch_rss]>` mapped to a lambda function that calls `fetch_rss_feed` with a predefined URL. You can extend this by making the URL dynamic based on the Elasticsearch context.
# - When the token `<[fetch_rss]>` is detected in the Elasticsearch context, `fetch_rss_feed` is executed, fetching and relaying RSS feed data to the user.
# 
# This modular approach allows you to expand your bot's capabilities flexibly, adding new tokens and functions as needed to enhance user interaction based on the context provided by Elasticsearch.

# (old)

# # Function to fetch and send "IS tuoreimmat" RSS feed
# async def fetch_and_send_is_tuoreimmat(context, update):
#     logging.info("Fetching IS tuoreimmat RSS feed")
    
#     # Fetch the "IS tuoreimmat" RSS feed
#     rss_result = get_is_tuoreimmat()
    
#     # Extract the relevant content from the RSS result
#     if rss_result['type'] == 'text':
#         entries_summary = rss_result['content']
#     else:
#         entries_summary = "Tuoreimpien uutisten haku Ilta-Sanomien RSS-feedistä epäonnistui, sori!"
    
#     # Send the entries summary to the user
#     await context.bot.send_message(chat_id=update.effective_chat.id, text=entries_summary)
