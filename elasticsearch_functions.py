# elasticsearch_functions.py

# Import necessary libraries
import asyncio
import logging
import feedparser  # Make sure to install feedparser: pip install feedparser

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

# Mapping tokens to functions
action_token_functions = {
    "<[fetch_rss]>": lambda context, update: fetch_rss_feed(context, update, "http://example.com/rss"),  # Example RSS feed URL
    "<[function_x_token]>": function_x,
}

# In this setup:
# 
# - `fetch_rss_feed` is a generic function that takes a feed URL and fetches the top 5 entries, sending a summary back to the user.
# - The `action_token_functions` dictionary includes a token `<[fetch_rss]>` mapped to a lambda function that calls `fetch_rss_feed` with a predefined URL. You can extend this by making the URL dynamic based on the Elasticsearch context.
# - When the token `<[fetch_rss]>` is detected in the Elasticsearch context, `fetch_rss_feed` is executed, fetching and relaying RSS feed data to the user.
# 
# This modular approach allows you to expand your bot's capabilities flexibly, adding new tokens and functions as needed to enhance user interaction based on the context provided by Elasticsearch.