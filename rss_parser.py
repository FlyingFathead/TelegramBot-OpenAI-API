
# rss_parser.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

from datetime import datetime, timezone
from dateutil import parser as date_parser

import feedparser
import requests
import sys
import os
import json
import logging
import traceback
import pytz
import subprocess
import re
import time
import threading
import shutil

# Set default values for max days old and max entries to display
DEFAULT_MAX_DAYS_OLD = 7
DEFAULT_MAX_ENTRIES = 20

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# print term width horizontal line
def print_horizontal_line(character='-'):
    terminal_width = shutil.get_terminal_size().columns
    line = character * terminal_width
    logging.info(line)

# Get the time since publication
def get_time_elapsed(published_time):
    current_time = datetime.now(pytz.UTC)
    time_difference = current_time - published_time

    minutes = int(time_difference.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes}m"
    elif minutes < 1440:  # Less than a day
        hours = minutes // 60
        return f"{hours}h"
    else:
        days = minutes // 1440
        return f"{days}d"

# # get the time since publication
# def get_time_elapsed(published_time):
#     current_time = datetime.now(pytz.UTC)
#     time_difference = current_time - published_time

#     minutes = int(time_difference.total_seconds() // 60)
#     if minutes < 60:
#         return f"{minutes}m"
#     else:
#         hours = minutes // 60
#         return f"{hours}h"

#
# ))> weather
#

def get_foreca_dump():
    logging.info('Getting data dump from Foreca.')
    # Set the regular expressions to match and extract content
    remove_everything_until = r'Suomen sää juuri nyt'
    remove_everything_after = r'MTV Sää'

    # Execute the lynx command and capture the output
    command = ['lynx', '--dump', '-nolist', 'https://www.foreca.fi/']
    output = subprocess.check_output(command, universal_newlines=True)

    # Trim the output based on the specified regular expressions
    trimmed_output = re.search(
        rf'{remove_everything_until}(.*?){remove_everything_after}', 
        output, 
        re.DOTALL
    )

    # Print the trimmed output if markers are found
    if trimmed_output:
        print_horizontal_line()
        logging.info(trimmed_output.group(1))
        print_horizontal_line()
        return trimmed_output.group(1)
    else:
        error_message = "[ERROR!] Start or stop marker not found in the output."
        logging.error(error_message)
        return error_message

def get_weather(city):
    logging.info('Getting `ansiweather` weather.')
    result = subprocess.run(['ansiweather', '-l', city, '-d', 'true', '-H', 'true'], capture_output=True, text=True)
    output = result.stdout.strip()

    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    output = ansi_escape.sub('', output)

    return output

#
# ))> news sources
#

def get_most_read():
    if os.path.isfile('data_uutiset.txt'):
        with open('data_uutiset.txt', 'r') as file:
            return file.read()
    else:
        return ""

#
# ))> bbc
#

# bbc.co.uk // top stories
def get_bbc_business(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('http://feeds.bbci.co.uk/news/business/rss.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Filter and format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S GMT")
            pub_date = pub_date.replace(tzinfo=pytz.timezone('GMT'))
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Latest business news from bbc.co.uk (BBC News Business):\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching bbc.co.uk news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi bbc.co.uk:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi bbc.co.uk:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# bbc // science & environment
def get_bbc_science_environment(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('http://feeds.bbci.co.uk/news/science_and_environment/rss.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Filter and format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S GMT")
            pub_date = pub_date.replace(tzinfo=pytz.timezone('GMT'))
            if (current_time - pub_date).days <= max_days_old:
                formatted_date = pub_date.strftime("%b %d")
                formatted_item = f'<p><i>({formatted_date})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä bbc.co.uk:n tuoreimmat tiede- ja ympäristöuutiset.\n(BBC News: Science & Environment):\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching bbc.co.uk news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi bbc.co.uk:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi bbc.co.uk:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }
    
# bbc.co.uk // top stories
def get_bbc_top_stories(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('http://feeds.bbci.co.uk/news/rss.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Filter and format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S GMT")
            pub_date = pub_date.replace(tzinfo=pytz.timezone('GMT'))
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä BBC:n tämän hetken pääuutisaiheet (BBC News, bbc.co.uk):\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching bbc.co.uk news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi bbc.co.uk:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi bbc.co.uk:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

#
# )> cnn.com
#

# cnn // U.S. News
# CNN news parsing
def get_cnn_us_news(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('http://rss.cnn.com/rss/edition_us.rss')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Check if there are any entries in the feed
        if not feed.entries:
            raise ValueError("The feed is empty")

        # Format the items with titles and dates
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for entry in feed.entries:
            # Skip if title and link are not available
            if not all(hasattr(entry, attr) for attr in ['title', 'link']):
                continue

            title = entry.title
            link = entry.link

            if hasattr(entry, 'published'):
                pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %Z")
                pub_date = pub_date.replace(tzinfo=pytz.UTC)
                if (current_time - pub_date).days <= max_days_old:
                    formatted_date = pub_date.strftime("%b %d")
                    formatted_item = f'<p><i>({formatted_date})</i> <a href="{link}">{title}</a></p>'
                    formatted_items.append(formatted_item)
            
            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä CNN:n (cnn.com) tuoreimmat uutiset USA:sta:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching cnn.com news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi cnn.com:in uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi cnn.com:in uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# cnn // world edition
def get_cnn_world_edition(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('http://rss.cnn.com/rss/edition_world.rss')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Format the items with titles and dates
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for entry in feed.entries:
            # Skip if title and link are not available
            if not all(hasattr(entry, attr) for attr in ['title', 'link']):
                continue
            
            title = entry.title
            link = entry.link
            
            if hasattr(entry, 'published'):
                pub_date = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %Z")
                pub_date = pub_date.replace(tzinfo=pytz.UTC)
                if (current_time - pub_date).days <= max_days_old:
                    formatted_date = pub_date.strftime("%b %d")
                    formatted_item = f'<p><i>({formatted_date})</i> <a href="{link}">{title}</a></p>'
                    formatted_items.append(formatted_item)
            else:
                formatted_item = f'<p><a href="{link}">{title}</a></p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä CNN:n (cnn.com) uutiset maailmalta:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching cnn.com news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi cnn.com:in uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi cnn.com:in uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

#
# )> hs.fi
#

# hs.fi // etusivu
def get_hs_etusivu(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('http://www.hs.fi/rss/teasers/etusivu.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title,
                  'description': getattr(entry, 'description', None),
                  'link': entry.link,
                  'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions (if available), and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S GMT")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                if item['description']:
                    formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                else:
                    formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a></p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä etusivun uutiset hs.fi:stä:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching Helsingin Sanomat news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi HS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi HS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# # hs.fi // etusivu
# def get_hs_etusivu():
#     try:
#         # Fetch the RSS feed
#         response = requests.get('http://www.hs.fi/rss/teasers/etusivu.xml')

#         # Parse the RSS feed
#         feed = feedparser.parse(response.content)

#         # Extract the headlines, descriptions, links, and pubDates
#         items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
#                  for entry in feed.entries]

#         # Format the items with titles, descriptions, and elapsed time
#         formatted_items = []
#         for item in items:
#             pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
#             time_elapsed = get_time_elapsed(pub_date)
#             formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a></p>'
#             formatted_items.append(formatted_item)

#         # Join the formatted items into a string with each item on a new line
#         items_string = '\n'.join(formatted_items)
#         items_string_out = 'Tässä etusivun uutiset hs.fi:stä:\n\n' + items_string

#         print_horizontal_line()
#         logging.info(items_string_out)
#         print_horizontal_line()

#         return {
#             'type': 'text',
#             'content': items_string_out,
#             'html': f'<ul>{items_string_out}</ul>'
#         }
#     except Exception as e:
#         logging.error(f"Error fetching Iltasanomat news: {e}")
#         return {
#             'type': 'text',
#             'content': "Sori! En päässyt käsiksi HS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
#             'html': "Sori! En päässyt käsiksi HS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
#         }


# hs.fi // uusimmat
def get_hs_uusimmat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('http://www.hs.fi/rss/tuoreimmat.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title,
                  'description': getattr(entry, 'description', 'No description available'),
                  'link': entry.link,
                  'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S GMT")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä tuoreimmat uutiset hs.fi:stä:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching Helsingin Sanomat news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi HS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi HS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

#
# )> il.fi
#

# il.fi // uutiset
def get_il_uutiset(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://www.iltalehti.fi/rss/uutiset.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a></p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä tuoreimmat uutiset <a href="https://is.fi/">il.fi</a>:stä:<br>' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching Iltasanomat news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi il.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi il.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }
    
# il.fi // urheilu
def get_il_urheilu(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://www.iltalehti.fi/rss/urheilu.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a></p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä tuoreimmat urheilu-uutiset <a href="https://il.fi/">il.fi</a>:stä:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching il.fi/urheilu news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi il.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi il.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

#
# )> is.fi
#

# is.fi // horoskoopit
def get_is_horoskoopit(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # RSS url
        rss_source_url = 'https://www.is.fi/rss/menaiset/horoskooppi.xml'

        # Fetch the RSS feed
        response = requests.get(rss_source_url)

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates if they exist
        items = []
        for entry in feed.entries:
            item = {
                'title': entry.title,
                'description': entry.description,
                'link': entry.link
            }
            if hasattr(entry, 'published'):
                item['pubDate'] = entry.published
            items.append(item)

        # Format the items with titles, descriptions, and elapsed time if pubDate exists
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            if 'pubDate' in item:
                pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
                pub_date = pub_date.replace(tzinfo=timezone.utc)
                if (current_time - pub_date).days <= max_days_old:
                    time_elapsed = get_time_elapsed(pub_date)
                    formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                    formatted_items.append(formatted_item)
            else:
                formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä tuoreimmat horoskoopit <a href="https://is.fi/">is.fi</a>:stä:\n\n' + items_string

        print_horizontal_line()
        logging.info(f'Fetched data from: {rss_source_url}')
        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching Iltasanomat news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# is.fi // tiedeuutiset
def get_is_tiede(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://www.is.fi/rss/tiede.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates if they exist
        items = []
        current_time = datetime.now(pytz.UTC)
        for entry in feed.entries:
            item = {
                'title': entry.title,
                'description': entry.description,
                'link': entry.link
            }
            if hasattr(entry, 'published'):
                item['pubDate'] = entry.published
            items.append(item)

        # Format the items with titles, descriptions, and elapsed time if pubDate exists
        formatted_items = []
        for item in items:
            if 'pubDate' in item:
                pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
                pub_date = pub_date.replace(tzinfo=timezone.utc)
                if (current_time - pub_date).days <= max_days_old:
                    time_elapsed = get_time_elapsed(pub_date)
                    formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                    formatted_items.append(formatted_item)
            else:
                formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä tuoreimmat tiedeuutiset Ilta-Sanomista (is.fi):\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching Iltasanomat news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# hae iltasanomat.fi / digitoday-uutiset
def get_is_digitoday(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://www.is.fi/rss/digitoday.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates if they exist
        items = []
        for entry in feed.entries:
            item = {
                'title': entry.title,
                'description': entry.description,
                'link': entry.link
            }
            if hasattr(entry, 'published'):
                item['pubDate'] = entry.published
            items.append(item)

        # Filter items based on max_days_old
        current_time = datetime.now(pytz.UTC)
        filtered_items = []
        for item in items:
            if 'pubDate' in item:
                pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
                pub_date = pub_date.replace(tzinfo=timezone.utc)
                if (current_time - pub_date).days <= max_days_old:
                    time_elapsed = get_time_elapsed(pub_date)
                    formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                    filtered_items.append(formatted_item)
            else:
                formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                filtered_items.append(formatted_item)

            if len(filtered_items) >= max_entries:
                break

        # Join the filtered items into a string with each item on a new line
        items_string = '\n'.join(filtered_items)
        items_string_out = 'Tässä tuoreimmat uutiset Ilta-Sanomien (is.fi) Digitoday-osiosta:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching Iltasanomat news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# is.fi / taloussanomat
def get_is_taloussanomat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://www.is.fi/rss/taloussanomat.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates if they exist
        items = []
        current_time = datetime.now(pytz.UTC)
        for entry in feed.entries:
            item = {
                'title': entry.title,
                'description': entry.description,
                'link': entry.link
            }
            if hasattr(entry, 'published'):
                item['pubDate'] = entry.published
            items.append(item)

        # Format the items with titles, descriptions, and elapsed time if pubDate exists
        formatted_items = []
        for item in items:
            if 'pubDate' in item:
                pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
                pub_date = pub_date.replace(tzinfo=timezone.utc)
                if (current_time - pub_date).days <= max_days_old:
                    time_elapsed = get_time_elapsed(pub_date)
                    formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                    formatted_items.append(formatted_item)
            else:
                formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)

            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä tuoreimmat Ilta-Sanomien (is.fi) talousuutiset:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching Iltasanomat/Taloussanomat news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi IS:n/Taloussanomien uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi IS:n/Taloussanomien uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }
    
# is.fi // tuoreimmat
def get_is_tuoreimmat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://www.is.fi/rss/tuoreimmat.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
            pub_date = pub_date.replace(tzinfo=timezone.utc)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)
            
            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä tuoreimmat uutiset Ilta-Sanomista (is.fi):\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching Iltasanomat news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# is.fi // ulkomaat
def get_is_ulkomaat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://www.is.fi/rss/ulkomaat.xml')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates if they exist
        items = []
        for entry in feed.entries:
            item = {
                'title': entry.title,
                'description': entry.description,
                'link': entry.link
            }
            if hasattr(entry, 'published'):
                item['pubDate'] = entry.published
            items.append(item)

        # Format the items with titles, descriptions, and elapsed time if pubDate exists
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            if 'pubDate' in item:
                pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
                pub_date = pub_date.replace(tzinfo=timezone.utc)
                if (current_time - pub_date).days <= max_days_old:
                    time_elapsed = get_time_elapsed(pub_date)
                    formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                    formatted_items.append(formatted_item)
            else:
                formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)
            
            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä tuoreimmat ulkomaanuutiset Ilta-Sanomista (is.fi):\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching Iltasanomat news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

#
# )> YLE
#

# yle.fi // tuoreimmat
def get_yle_latest_news(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)
            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä yle.fi:n tuoreimmat uutiset:\n\n + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching yle.fi news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }
    
# yle.fi // pääuutiset
def get_yle_main_news(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)
            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä yle.fi:n pääuutiset:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching yle.fi news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# yle.fi // luetuimmat
def get_yle_most_read(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://feeds.yle.fi/uutiset/v1/mostRead/YLE_UUTISET.rss')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)
            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä <a href="https://yle.fi/">yle.fi</a>:n tämän hetken luetuimmat uutiset:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching yle.fi news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }
    
# yle.fi // kotimaa
def get_yle_kotimaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-34837')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)
            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä <a href="https://yle.fi/">yle.fi</a>:n kotimaan uutiset RSS-syötteestä:<br>' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching yle.fi news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# yle.fi // ulkomaat
def get_yle_ulkomaat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-34953')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)
            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä <a href="https://yle.fi/">yle.fi</a>:n ulkomaanuutiset RSS-syötteestä:<br>' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching yle.fi news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# yle.fi // uusimaa
def get_yle_uusimaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Fetch the RSS feed
        response = requests.get('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-147345')

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the headlines, descriptions, links, and pubDates
        items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the items with titles, descriptions, and elapsed time
        formatted_items = []
        current_time = datetime.now(pytz.UTC)
        for item in items:
            pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
            pub_date = pub_date.replace(tzinfo=pytz.UTC)
            if (current_time - pub_date).days <= max_days_old:
                time_elapsed = get_time_elapsed(pub_date)
                formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
                formatted_items.append(formatted_item)
            if len(formatted_items) >= max_entries:
                break

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Tässä yle.fi:n Uudenmaan uutiset (YLE Uusimaa):\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching yle.fi news: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi yle.fi:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# Function to fetch the three-day weather forecast for Helsinki from the BBC weather RSS feed
def get_bbc_helsinki_forecast():
    url = 'https://weather-broker-cdn.api.bbci.co.uk/en/forecast/rss/3day/2643123'

    try:
        # Fetch the RSS feed
        response = requests.get(url)

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Extract the forecast items
        items = [{'title': entry.title, 'description': entry.description, 'pubDate': entry.published}
                 for entry in feed.entries]

        # Format the forecast items with titles, descriptions, and elapsed time
        formatted_items = []
        for item in items:
            pub_date = date_parser.parse(item['pubDate'])
            pub_date = pub_date.replace(tzinfo=timezone.utc)  # Set the timezone info to UTC
            time_elapsed = get_time_elapsed(pub_date)
            formatted_item = f'<p><i>({time_elapsed})</i> {item["title"]}: {item["description"]}</p>'
            formatted_items.append(formatted_item)

        # Join the formatted items into a string with each item on a new line
        items_string = '\n'.join(formatted_items)
        items_string_out = 'Here is the three-day weather forecast for Helsinki from BBC:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching Helsinki weather forecast: {e}")
        return {
            'type': 'text',
            'content': "Sorry! Failed to fetch Helsinki weather forecast. Apologies for the inconvenience!",
            'html': "Sorry! Failed to fetch Helsinki weather forecast. Apologies for the inconvenience!"
        }

# testing for the main unit
if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("No command provided. Please specify a command.")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == 'foreca':
        get_foreca_dump()
    elif command == 'weather':
        if len(sys.argv) < 3:
            logging.error("Please specify a city for the weather command.")
            sys.exit(1)
        city = sys.argv[2]
        print(get_weather(city))
    elif command == 'bbc':
        if len(sys.argv) < 3:
            logging.error("Please specify a BBC category (business, science_environment, top_stories).")
            sys.exit(1)
        category = sys.argv[2].lower()
        if category == 'business':
            get_bbc_business()
        elif category == 'science_environment':
            get_bbc_science_environment()
        elif category == 'top_stories':
            get_bbc_top_stories()
        else:
            logging.error("Invalid BBC category specified.")
            sys.exit(1)
    elif command == 'cnn':
        if len(sys.argv) < 3:
            logging.error("Please specify a CNN category (us_news, world_edition).")
            sys.exit(1)
        category = sys.argv[2].lower()
        if category == 'us_news':
            get_cnn_us_news()
        elif category == 'world_edition':
            get_cnn_world_edition()
        else:
            logging.error("Invalid CNN category specified.")
            sys.exit(1)
    elif command == 'hs':
        if len(sys.argv) < 3:
            logging.error("Please specify an HS category (etusivu, uusimmat).")
            sys.exit(1)
        category = sys.argv[2].lower()
        if category == 'etusivu':
            get_hs_etusivu()
        elif category == 'uusimmat':
            get_hs_uusimmat()
        else:
            logging.error("Invalid HS category specified.")
            sys.exit(1)
    elif command == 'il':
        if len(sys.argv) < 3:
            logging.error("Please specify an IL category (uutiset, urheilu).")
            sys.exit(1)
        category = sys.argv[2].lower()
        if category == 'uutiset':
            get_il_uutiset()
        elif category == 'urheilu':
            get_il_urheilu()
        else:
            logging.error("Invalid IL category specified.")
            sys.exit(1)
    elif command == 'is':
        if len(sys.argv) < 3:
            logging.error("Please specify an IS category (horoskoopit, tiede, digitoday, taloussanomat, tuoreimmat, ulkomaat).")
            sys.exit(1)
        category = sys.argv[2].lower()
        if category == 'horoskoopit':
            get_is_horoskoopit()
        elif category == 'tiede':
            get_is_tiede()
        elif category == 'digitoday':
            get_is_digitoday()
        elif category == 'taloussanomat':
            get_is_taloussanomat()
        elif category == 'tuoreimmat':
            get_is_tuoreimmat()
        elif category == 'ulkomaat':
            get_is_ulkomaat()
        else:
            logging.error("Invalid IS category specified.")
            sys.exit(1)
    elif command == 'yle':
        if len(sys.argv) < 3:
            logging.error("Please specify a YLE category (latest_news, main_news, most_read, kotimaa, ulkomaat, uusimaa).")
            sys.exit(1)
        category = sys.argv[2].lower()
        if category == 'latest_news':
            get_yle_latest_news()
        elif category == 'main_news':
            get_yle_main_news()
        elif category == 'most_read':
            get_yle_most_read()
        elif category == 'kotimaa':
            get_yle_kotimaa()
        elif category == 'ulkomaat':
            get_yle_ulkomaat()
        elif category == 'uusimaa':
            get_yle_uusimaa()
        else:
            logging.error("Invalid YLE category specified.")
            sys.exit(1)
    elif command == 'bbc_helsinki_forecast':
        get_bbc_helsinki_forecast()
    else:
        logging.error("Invalid command specified.")
        sys.exit(1)
