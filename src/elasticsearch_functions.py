# elasticsearch_functions.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Import necessary libraries
import subprocess
import re
import asyncio
import datetime
import logging
from functools import partial

from rss_parser import get_defcon_status
from news_sources import SOURCES
from news_webpage_parser import fetch_news
from web_search import RetrievalError, SOURCE_INSTRUCTIONS

# from bs4 import BeautifulSoup

# here we can run our separate helper functions according to elasticsearch's matches

async def unconfigured_rss_action(context, update, chat_history):
    # The legacy demonstration token has no publisher or feed URL.
    return chat_history + [{"role": "system", "content": "No feed is configured for this RSS action. "
                            "Ask which publisher or section the user wants."}]


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

async def defcon_action(context, update, chat_history):
    result = await asyncio.to_thread(get_defcon_status)
    if result["type"] != "text":
        return chat_history + [{"role": "system", "content": "DEFCON status lookup failed. "
                                "Tell the user the source could not be retrieved."}]
    return chat_history + [{"role": "user", "content": result["content"]}]


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


# Function to fetch name days
async def get_name_days():
    try:
        # URL of the page you want to dump
        url = "https://almanakka.helsinki.fi/"
        
        # Use lynx to dump the page content
        result = subprocess.run(['lynx', '--dump', url], capture_output=True, text=True, check=True)
        page_content = result.stdout
        
        # Extract the date (search for the pattern dd.mm.yyyy)
        date_pattern = r"\b\d{1,2}\.\d{1,2}\.\d{4}\b"  # Matches dates like 20.9.2024 or 2.9.2024
        date_match = re.search(date_pattern, page_content)
        
        if date_match:
            date_str_extracted = date_match.group(0)
            # Parse the date string into a datetime object
            extracted_date = datetime.datetime.strptime(date_str_extracted, '%d.%m.%Y').date()
            today = datetime.date.today()
            if extracted_date == today:
                date_str = f"Päivämäärä: {date_str_extracted}\n"
            else:
                date_str = f"Päivämäärä: {date_str_extracted} (Huom: Päivämäärä ei ole tämän päivän päivämäärä!)\n"
                logging.warning(f"Extracted date {extracted_date} does not match today's date {today}.")
        else:
            date_str = "Päivämäärää ei löydy.\n"
            logging.warning("Date not found on the page.")
    
        # Extract name days for different languages with the updated labels
        languages = {
            'Suomi': 'Suomenkielinen nimipäivä',
            'Ruotsi': 'Ruotsinkielinen nimipäivä',
            'Saame': 'Saamenkielinen nimipäivä',
            'Ortodoksinen': 'Ortodoksinen nimipäivä'
        }
    
        name_days_list = []
        for lang, label in languages.items():
            start_index = page_content.find(f"{lang}:")
            if start_index != -1:
                end_index = page_content.find("\n", start_index)
                names_line = page_content[start_index:end_index].strip()
                if ': ' in names_line:
                    names_only = names_line.split(': ', 1)[1]
                    name_days_list.append(f"{label}: {names_only}")
                else:
                    name_days_list.append(f"{label}: Nimiä ei löydy.")
            else:
                name_days_list.append(f"{label}: Nimiä ei löydy.")
    
        name_days_str = "\n".join(name_days_list)
    
        # Combine date and name days
        entries_summary = f"{date_str}{name_days_str}"
    
        # Add logging statement to output the entries_summary
        logging.info(f"Name days fetched:\n{entries_summary}")

        # Return the result in a dictionary
        return {'type': 'text', 'html': entries_summary}
    
    except subprocess.CalledProcessError as e:
        logging.error(f"Error occurred while using lynx: {e}")
        return {'type': 'error', 'message': f"Error occurred while using lynx: {e}"}
    except Exception as e:
        logging.error(f"An error occurred in get_name_days: {e}")
        return {'type': 'error', 'message': str(e)}

# Function to execute get_name_days and send result to user
async def execute_get_name_days(context, update, chat_history_with_system_message):
    logging.info("Executing get_name_days")
    
    try:
        # Fetch the name days
        result = await get_name_days()
    
        # Check if fetch was successful
        if result['type'] == 'text':
            entries_summary = result['html']
        else:
            entries_summary = "Nimipäivien haku epäonnistui! Voit myös käydä osoitteessa: https://almanakka.helsinki.fi"
    
        # Variable with the text to prepend
        prepend_text = "Suomalaiset nimipäivät, haettu osoitteesta: https://almanakka.helsinki.fi/\n\n"
    
        # Combine the prepend text with the entries summary
        full_message = prepend_text + entries_summary
    
        # Sanitize the content
        full_message = sanitize_html(full_message)
    
        # Prepare the system message
        system_message = {
            "role": "system",
            "content": full_message
        }
    
        # Append this execution notice to the chat history or context
        chat_history_with_es_context = chat_history_with_system_message + [system_message]
    
        # Optionally, send the result back to the user (uncomment if needed)
        # await context.bot.send_message(chat_id=update.effective_chat.id, text=full_message)
    
        return chat_history_with_es_context
    
    except Exception as e:
        logging.error(f"Error in execute_get_name_days: {e}")
        # Provide fallback message
        error_message = "Nimipäivien haku epäonnistui! Voit myös käydä osoitteessa: https://almanakka.helsinki.fi"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        return chat_history_with_system_message

#
# > mapping action token to function
#

async def news_action(name, context, update, chat_history, *, bot=None, sources=None):
    try:
        result = await fetch_news(name, bot)
    except RetrievalError as exc:
        return chat_history + [{"role": "system", "content": f"News retrieval failed. {exc}. "
                               "Tell the user the failure explicitly in their language."}]
    if sources is not None:
        sources.update(result.sources)
    return chat_history + [
        {"role": "system", "content": SOURCE_INSTRUCTIONS},
        {"role": "user", "content": result.context()},
    ]


news_actions = {f"<[{name}]>": partial(news_action, name) for name in SOURCES}
action_token_functions = {
    "<[fetch_rss]>": unconfigured_rss_action,
    "<[function_x_token]>": function_x,
    **{token: action for token, action in news_actions.items()
       if token.startswith(("<[get_bbc_", "<[get_cnn_"))},
    "<[get_defcon_status]>": defcon_action,
    **news_actions,
    "<[get_name_days]>": execute_get_name_days,
}
