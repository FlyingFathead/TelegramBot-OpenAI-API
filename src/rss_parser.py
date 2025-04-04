
# rss_parser.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

from datetime import datetime, timezone
from dateutil import parser as date_parser
from bs4 import BeautifulSoup

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
# logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

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
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/teasers/etusivu.xml', 'etusivun uutiset', max_days_old, max_entries)

def get_hs_uusimmat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/tuoreimmat.xml', 'uusimmat uutiset', max_days_old, max_entries)

def get_hs_kotimaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/suomi.xml', 'kotimaan uutiset', max_days_old, max_entries)

def get_hs_ulkomaat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/maailma.xml', 'ulkomaan uutiset', max_days_old, max_entries)

def get_hs_talous(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/talous.xml', 'talousuutiset', max_days_old, max_entries)

def get_hs_politiikka(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/politiikka.xml', 'politiikan uutiset', max_days_old, max_entries)

def get_hs_helsinki(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/helsinki.xml', 'Helsingin uutiset', max_days_old, max_entries)

def get_hs_urheilu(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/urheilu.xml', 'urheilu-uutiset', max_days_old, max_entries)

def get_hs_kulttuuri(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/kulttuuri.xml', 'kulttuuriuutiset', max_days_old, max_entries)

def get_hs_paakirjoitukset(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/paakirjoitukset.xml', 'pääkirjoitukset', max_days_old, max_entries)

def get_hs_lastenuutiset(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/lastenuutiset.xml', 'lasten uutiset', max_days_old, max_entries)

def get_hs_ruoka(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/ruoka.xml', 'ruoka', max_days_old, max_entries)

def get_hs_elama(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/elama.xml', 'elämä', max_days_old, max_entries)

def get_hs_tiede(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/tiede.xml', 'tiedeuutiset', max_days_old, max_entries)

def get_hs_kuukausiliite(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_hs_rss_feed('http://www.hs.fi/rss/kuukausiliite.xml', 'kuukausiliite', max_days_old, max_entries)

# Fetch and process RSS feed for HS
def fetch_and_process_hs_rss_feed(url, category_name, max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Ensure max_days_old and max_entries are integers
        max_days_old = int(max_days_old)
        max_entries = int(max_entries)

        # Fetch the RSS feed
        response = requests.get(url)

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Define possible date formats
        date_formats = ["%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S GMT"]

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
            pub_date = None
            for date_format in date_formats:
                try:
                    pub_date = datetime.strptime(item['pubDate'], date_format)
                    pub_date = pub_date.replace(tzinfo=pytz.UTC)
                    break
                except ValueError:
                    continue
            if pub_date is None:
                logging.error(f"Failed to parse date: {item['pubDate']}")
                continue

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
        items_string_out = f'Tässä hs.fi:n {category_name}:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching hs.fi {category_name} news: {e}")
        return {
            'type': 'text',
            'content': f"Sori! En päässyt käsiksi hs.fi:n {category_name}-uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': f"Sori! En päässyt käsiksi hs.fi:n {category_name}-uutisvirtaan. Mönkään meni! Pahoitteluni!"
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

# Fetch and process RSS feed for IS.fi
def fetch_and_process_is_rss_feed(url, category_name, max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Ensure max_days_old and max_entries are integers
        max_days_old = int(max_days_old)
        max_entries = int(max_entries)

        # Fetch the RSS feed
        response = requests.get(url)

        # Parse the RSS feed
        feed = feedparser.parse(response.content)

        # Define possible date formats
        date_formats = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"]

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
            pub_date = None
            for date_format in date_formats:
                try:
                    pub_date = datetime.strptime(item['pubDate'], date_format)
                    pub_date = pub_date.replace(tzinfo=pytz.UTC)
                    break
                except ValueError:
                    continue
            if pub_date is None:
                logging.error(f"Failed to parse date: {item['pubDate']}")
                continue

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
        items_string_out = f'Tässä IS.fi:n {category_name}:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching IS.fi {category_name} news: {e}")
        return {
            'type': 'text',
            'content': f"Sori! En päässyt käsiksi IS.fi:n {category_name}-uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': f"Sori! En päässyt käsiksi IS.fi:n {category_name}-uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }

# is.fi // tuoreimmat uutiset
def get_is_tuoreimmat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/tuoreimmat.xml', 'tuoreimmat uutiset', max_days_old, max_entries)

# is.fi // kotimaan uutiset
def get_is_kotimaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/kotimaa.xml', 'kotimaan uutiset', max_days_old, max_entries)

# is.fi // politiikka
def get_is_politiikka(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/politiikka.xml', 'politiikan uutiset', max_days_old, max_entries)

# is.fi // taloussanomat
def get_is_taloussanomat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/taloussanomat.xml', 'taloussanomat', max_days_old, max_entries)

# is.fi // ulkomaat
def get_is_ulkomaat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/ulkomaat.xml', 'ulkomaan uutiset', max_days_old, max_entries)

# is.fi // pääkirjoitus
def get_is_paakirjoitus(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/paakirjoitus.xml', 'pääkirjoitus', max_days_old, max_entries)

# is.fi // viihde
def get_is_viihde(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/viihde.xml', 'viihde', max_days_old, max_entries)

# is.fi // TV & elokuva
def get_is_tv_ja_elokuvat(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/tv-ja-elokuvat.xml', 'TV & elokuva', max_days_old, max_entries)

# is.fi // musiikki
def get_is_musiikki(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/musiikki.xml', 'musiikki', max_days_old, max_entries)

# is.fi // kuninkaalliset
def get_is_kuninkaalliset(max_days_old=1000, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/kuninkaalliset.xml', 'kuninkaalliset', max_days_old, max_entries)

# is.fi // horoskooppi
def get_is_horoskoopit(max_days_old=30, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/horoskooppi.xml', 'horoskoopit', max_days_old, max_entries)

# is.fi // urheilu
def get_is_urheilu(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/urheilu.xml', 'urheilu', max_days_old, max_entries)

# is.fi // jääkiekko
def get_is_jaakiekko(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/jaakiekko.xml', 'jääkiekko', max_days_old, max_entries)

# is.fi // tiede
def get_is_tiede(max_days_old=1000, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/tiede.xml', 'tiedeuutiset', max_days_old, max_entries)

# is.fi // jalkapallo
def get_is_jalkapallo(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/jalkapallo.xml', 'jalkapallo', max_days_old, max_entries)

# is.fi // ralli
def get_is_ralli(max_days_old=1000, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/ralli.xml', 'ralli', max_days_old, max_entries)

# is.fi // yleisurheilu
def get_is_yleisurheilu(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/yleisurheilu.xml', 'yleisurheilu', max_days_old, max_entries)

# is.fi // hiihto
def get_is_hiihto(max_days_old=1000, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/hiihtolajit.xml', 'hiihto', max_days_old, max_entries)

# is.fi // formula 1
def get_is_formula1(max_days_old=1000, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/formula1.xml', 'formula 1', max_days_old, max_entries)

# is.fi // ravit
def get_is_ravit(max_days_old=1000, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/ravit.xml', 'ravit', max_days_old, max_entries)

# is.fi // digitoday
def get_is_digitoday(max_days_old=1000, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/digitoday.xml', 'digitoday', max_days_old, max_entries)

# is.fi // esports
def get_is_esports(max_days_old=1000, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/digitoday/esports.xml', 'esports', max_days_old, max_entries)

# is.fi // autot
def get_is_autot(max_days_old=1000, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/autot.xml', 'autot', max_days_old, max_entries)

# is.fi // me naiset
def get_is_menaiset(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/menaiset.xml', 'me naiset', max_days_old, max_entries)

# is.fi // hyvä olo
def get_is_hyvaolo(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/hyvaolo.xml', 'hyvä olo', max_days_old, max_entries)

# is.fi // ruokala
def get_is_ruokala(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/ruokala.xml', 'ruokala', max_days_old, max_entries)

# is.fi // asuminen
def get_is_asuminen(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/asuminen.xml', 'asuminen', max_days_old, max_entries)

# is.fi // matkat
def get_is_matkat(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/matkat.xml', 'matkat', max_days_old, max_entries)

# is.fi // perhe
def get_is_perhe(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_is_rss_feed('https://www.is.fi/rss/perhe.xml', 'perhe', max_days_old, max_entries)

# #
# # )> YLE
# #

# overall rss fetcher for yle news
def fetch_and_process_yle_rss_feed(url, category_name, max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    try:
        # Ensure max_days_old and max_entries are integers
        max_days_old = int(max_days_old)
        max_entries = int(max_entries)

        # Fetch the RSS feed
        response = requests.get(url)

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
        items_string_out = f'Tässä yle.fi:n {category_name}:\n\n' + items_string

        print_horizontal_line()
        logging.info(items_string_out)
        print_horizontal_line()

        return {
            'type': 'text',
            'content': items_string_out,
            'html': f'<ul>{items_string_out}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching yle.fi {category_name} news: {e}")
        return {
            'type': 'text',
            'content': f"Sori! En päässyt käsiksi yle.fi:n {category_name}-uutisvirtaan. Mönkään meni! Pahoitteluni!",
            'html': f"Sori! En päässyt käsiksi yle.fi:n {category_name}-uutisvirtaan. Mönkään meni! Pahoitteluni!"
        }
    
def get_yle_latest_news(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET', 'tuoreimmat uutiset', max_days_old, max_entries)

def get_yle_main_news(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss', 'pääuutiset', max_days_old, max_entries)

def get_yle_most_read(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/mostRead/YLE_UUTISET.rss', 'luetuimmat uutiset', max_days_old, max_entries)

def get_yle_kotimaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-34837', 'kotimaan uutiset', max_days_old, max_entries)

def get_yle_kulttuuri(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-150067', 'kulttuuriuutiset', max_days_old, max_entries)

def get_yle_liikenne(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-12', 'liikenneuutiset', max_days_old, max_entries)

def get_yle_luonto(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-35354', 'luontouutiset', max_days_old, max_entries)

def get_yle_media(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-35057', 'mediauutiset', max_days_old, max_entries)

def get_yle_nakokulmat(max_days_old=365, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-35381', 'näkökulmat-uutiset', max_days_old, max_entries)

def get_yle_terveys(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-35138', 'terveysuutiset', max_days_old, max_entries)

def get_yle_tiede(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-819', 'tiedeuutiset', max_days_old, max_entries)

def get_yle_ulkomaat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-34953', 'ulkomaan uutiset', max_days_old, max_entries)

def get_yle_urheilu(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_URHEILU', 'urheilu-uutiset', max_days_old, max_entries)

def get_yle_viihde(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-36066', 'viihdeuutiset', max_days_old, max_entries)

#
# > yle.fi regional news
#


def get_yle_etela_karjala(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-141372', 'Etelä-Karjalan uutiset', max_days_old, max_entries)

def get_yle_etela_pohjanmaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-146311',
        'Etelä-Pohjanmaan uutiset', max_days_old, max_entries
    )

def get_yle_etela_savo(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-141852',
        'Etelä-Savon uutiset', max_days_old, max_entries
    )

def get_yle_kainuu(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-141399',
        'Kainuun uutiset',
        max_days_old,
        max_entries
    )

def get_yle_kanta_hame(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-138727',
        'Kanta-Hämeen uutiset',
        max_days_old,
        max_entries
    )

def get_yle_keski_pohjanmaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-135629',
        'Keski-Pohjanmaan uutiset', 
        max_days_old, 
        max_entries
    )

def get_yle_keski_suomi(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-148148',
        'Keski-Suomen uutiset', 
        max_days_old, 
        max_entries
    )

def get_yle_kymenlaakso(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-131408',
        'Kymenlaakson uutiset', 
        max_days_old, 
        max_entries
    )

def get_yle_lappi(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-139752',
        'Lapin uutiset', 
        max_days_old, 
        max_entries
    )

def get_yle_pirkanmaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-146831',
        'Pirkanmaan uutiset', max_days_old, max_entries
    )

def get_yle_pohjanmaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-148149',
        'Pohjanmaan uutiset', max_days_old, max_entries
    )

def get_yle_pohjois_karjala(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-141936',
        'Pohjois-Karjalan uutiset', max_days_old, max_entries
    )

def get_yle_pohjois_pohjanmaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-148154',
        'Pohjois-Pohjanmaan uutiset', max_days_old, max_entries
    )

def get_yle_pohjois_savo(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-141764',
        'Pohjois-Savon uutiset', max_days_old, max_entries
    )

def get_yle_paijat_hame(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-141401',
        'Päijät-Hämeen uutiset', max_days_old, max_entries
    )

def get_yle_satakunta(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-139772',
        'Satakunnan uutiset', max_days_old, max_entries
    )

def get_yle_uusimaa(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed('https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-147345', 'Uudenmaan uutiset (YLE Uusimaa)', max_days_old, max_entries)

def get_yle_varsinais_suomi(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET&concepts=18-135507',
        'Varsinais-Suomen uutiset', max_days_old, max_entries
    )

def get_yle_selkouutiset(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_SELKOUUTISET',
        'Selkouutiset', max_days_old, max_entries
    )

def get_yle_news(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_NEWS',
        'Yle News', max_days_old, max_entries
    )

def get_yle_sapmi(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_SAPMI',
        'Yle Sápmi', max_days_old, max_entries
    )

def get_yle_novosti(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_NOVOSTI',
        'Novosti Yle', max_days_old, max_entries
    )

def get_yle_karjalakse(max_days_old=1000, max_entries=DEFAULT_MAX_ENTRIES):
    return fetch_and_process_yle_rss_feed(
        'https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_KARJALAKSE',
        'karjalakse-uutiset',
        max_days_old,
        max_entries
    )

#
# > others
#

# get DEFCON status
def get_defcon_status():
    try:
        url = "https://www.defconlevel.com/current-level.php"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        defcon_level = soup.find("div", class_="header-defcon-level").get_text(strip=True)
        description_tag = soup.find("div", class_="header-subtext")
        description = description_tag.get_text(strip=True) if description_tag else "No description available"

        # Clean the defcon level text
        defcon_level = ' '.join(defcon_level.split()[:7])  # limit to first few words to avoid extra text

        status_string = f"Current DEFCON Level: {defcon_level}\nDescription: {description}"

        current_time = datetime.now(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S %Z")
        log_message = f"🚨 Fetched current DEFCON status from defconlevel.com 🚨 at {current_time}"

        logging.info(status_string)
        logging.info(log_message)

        return {
            'type': 'text',
            'content': f"{status_string}\n{log_message}",
            'html': f'<ul>{status_string}<br>{log_message}</ul>'
        }
    except Exception as e:
        logging.error(f"Error fetching DEFCON status: {e}")
        return {
            'type': 'text',
            'content': "Sori! En päässyt käsiksi DEFCON-tilaan. Mönkään meni! Pahoitteluni!",
            'html': "Sori! En päässyt käsiksi DEFCON-tilaan. Mönkään meni! Pahoitteluni!"
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
    elif command == 'defcon':
        get_defcon_status()
    else:
        logging.error("Invalid command specified.")
        sys.exit(1)


# # is.fi // horoskoopit
# def get_is_horoskoopit(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
#     try:
#         # RSS url
#         rss_source_url = 'https://www.is.fi/rss/menaiset/horoskooppi.xml'

#         # Fetch the RSS feed
#         response = requests.get(rss_source_url)

#         # Parse the RSS feed
#         feed = feedparser.parse(response.content)

#         # Extract the headlines, descriptions, links, and pubDates if they exist
#         items = []
#         for entry in feed.entries:
#             item = {
#                 'title': entry.title,
#                 'description': entry.description,
#                 'link': entry.link
#             }
#             if hasattr(entry, 'published'):
#                 item['pubDate'] = entry.published
#             items.append(item)

#         # Format the items with titles, descriptions, and elapsed time if pubDate exists
#         formatted_items = []
#         current_time = datetime.now(pytz.UTC)
#         for item in items:
#             if 'pubDate' in item:
#                 pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
#                 pub_date = pub_date.replace(tzinfo=timezone.utc)
#                 if (current_time - pub_date).days <= max_days_old:
#                     time_elapsed = get_time_elapsed(pub_date)
#                     formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                     formatted_items.append(formatted_item)
#             else:
#                 formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                 formatted_items.append(formatted_item)

#             if len(formatted_items) >= max_entries:
#                 break

#         # Join the formatted items into a string with each item on a new line
#         items_string = '\n'.join(formatted_items)
#         items_string_out = 'Tässä tuoreimmat horoskoopit <a href="https://is.fi/">is.fi</a>:stä:\n\n' + items_string

#         print_horizontal_line()
#         logging.info(f'Fetched data from: {rss_source_url}')
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
#             'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
#             'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
#         }

# # is.fi // tiedeuutiset
# def get_is_tiede(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
#     try:
#         # Fetch the RSS feed
#         response = requests.get('https://www.is.fi/rss/tiede.xml')

#         # Parse the RSS feed
#         feed = feedparser.parse(response.content)

#         # Extract the headlines, descriptions, links, and pubDates if they exist
#         items = []
#         current_time = datetime.now(pytz.UTC)
#         for entry in feed.entries:
#             item = {
#                 'title': entry.title,
#                 'description': entry.description,
#                 'link': entry.link
#             }
#             if hasattr(entry, 'published'):
#                 item['pubDate'] = entry.published
#             items.append(item)

#         # Format the items with titles, descriptions, and elapsed time if pubDate exists
#         formatted_items = []
#         for item in items:
#             if 'pubDate' in item:
#                 pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
#                 pub_date = pub_date.replace(tzinfo=timezone.utc)
#                 if (current_time - pub_date).days <= max_days_old:
#                     time_elapsed = get_time_elapsed(pub_date)
#                     formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                     formatted_items.append(formatted_item)
#             else:
#                 formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                 formatted_items.append(formatted_item)

#             if len(formatted_items) >= max_entries:
#                 break

#         # Join the formatted items into a string with each item on a new line
#         items_string = '\n'.join(formatted_items)
#         items_string_out = 'Tässä tuoreimmat tiedeuutiset Ilta-Sanomista (is.fi):\n\n' + items_string

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
#             'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
#             'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
#         }

# # hae iltasanomat.fi / digitoday-uutiset
# def get_is_digitoday(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
#     try:
#         # Fetch the RSS feed
#         response = requests.get('https://www.is.fi/rss/digitoday.xml')

#         # Parse the RSS feed
#         feed = feedparser.parse(response.content)

#         # Extract the headlines, descriptions, links, and pubDates if they exist
#         items = []
#         for entry in feed.entries:
#             item = {
#                 'title': entry.title,
#                 'description': entry.description,
#                 'link': entry.link
#             }
#             if hasattr(entry, 'published'):
#                 item['pubDate'] = entry.published
#             items.append(item)

#         # Filter items based on max_days_old
#         current_time = datetime.now(pytz.UTC)
#         filtered_items = []
#         for item in items:
#             if 'pubDate' in item:
#                 pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
#                 pub_date = pub_date.replace(tzinfo=timezone.utc)
#                 if (current_time - pub_date).days <= max_days_old:
#                     time_elapsed = get_time_elapsed(pub_date)
#                     formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                     filtered_items.append(formatted_item)
#             else:
#                 formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                 filtered_items.append(formatted_item)

#             if len(filtered_items) >= max_entries:
#                 break

#         # Join the filtered items into a string with each item on a new line
#         items_string = '\n'.join(filtered_items)
#         items_string_out = 'Tässä tuoreimmat uutiset Ilta-Sanomien (is.fi) Digitoday-osiosta:\n\n' + items_string

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
#             'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
#             'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
#         }

# # is.fi / taloussanomat
# def get_is_taloussanomat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
#     try:
#         # Fetch the RSS feed
#         response = requests.get('https://www.is.fi/rss/taloussanomat.xml')

#         # Parse the RSS feed
#         feed = feedparser.parse(response.content)

#         # Extract the headlines, descriptions, links, and pubDates if they exist
#         items = []
#         current_time = datetime.now(pytz.UTC)
#         for entry in feed.entries:
#             item = {
#                 'title': entry.title,
#                 'description': entry.description,
#                 'link': entry.link
#             }
#             if hasattr(entry, 'published'):
#                 item['pubDate'] = entry.published
#             items.append(item)

#         # Format the items with titles, descriptions, and elapsed time if pubDate exists
#         formatted_items = []
#         for item in items:
#             if 'pubDate' in item:
#                 pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
#                 pub_date = pub_date.replace(tzinfo=timezone.utc)
#                 if (current_time - pub_date).days <= max_days_old:
#                     time_elapsed = get_time_elapsed(pub_date)
#                     formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                     formatted_items.append(formatted_item)
#             else:
#                 formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                 formatted_items.append(formatted_item)

#             if len(formatted_items) >= max_entries:
#                 break

#         # Join the formatted items into a string with each item on a new line
#         items_string = '\n'.join(formatted_items)
#         items_string_out = 'Tässä tuoreimmat Ilta-Sanomien (is.fi) talousuutiset:\n\n' + items_string

#         print_horizontal_line()
#         logging.info(items_string_out)
#         print_horizontal_line()

#         return {
#             'type': 'text',
#             'content': items_string_out,
#             'html': f'<ul>{items_string_out}</ul>'
#         }
#     except Exception as e:
#         logging.error(f"Error fetching Iltasanomat/Taloussanomat news: {e}")
#         return {
#             'type': 'text',
#             'content': "Sori! En päässyt käsiksi IS:n/Taloussanomien uutisvirtaan. Mönkään meni! Pahoitteluni!",
#             'html': "Sori! En päässyt käsiksi IS:n/Taloussanomien uutisvirtaan. Mönkään meni! Pahoitteluni!"
#         }
    
# # is.fi // tuoreimmat
# def get_is_tuoreimmat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
#     try:
#         # Fetch the RSS feed
#         response = requests.get('https://www.is.fi/rss/tuoreimmat.xml')

#         # Parse the RSS feed
#         feed = feedparser.parse(response.content)

#         # Extract the headlines, descriptions, links, and pubDates
#         items = [{'title': entry.title, 'description': entry.description, 'link': entry.link, 'pubDate': entry.published}
#                  for entry in feed.entries]

#         # Format the items with titles, descriptions, and elapsed time
#         formatted_items = []
#         current_time = datetime.now(pytz.UTC)
#         for item in items:
#             pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
#             pub_date = pub_date.replace(tzinfo=timezone.utc)
#             if (current_time - pub_date).days <= max_days_old:
#                 time_elapsed = get_time_elapsed(pub_date)
#                 formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                 formatted_items.append(formatted_item)
            
#             if len(formatted_items) >= max_entries:
#                 break

#         # Join the formatted items into a string with each item on a new line
#         items_string = '\n'.join(formatted_items)
#         items_string_out = 'Tässä tuoreimmat uutiset Ilta-Sanomista (is.fi):\n\n' + items_string

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
#             'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
#             'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
#         }

# # is.fi // ulkomaat
# def get_is_ulkomaat(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
#     try:
#         # Fetch the RSS feed
#         response = requests.get('https://www.is.fi/rss/ulkomaat.xml')

#         # Parse the RSS feed
#         feed = feedparser.parse(response.content)

#         # Extract the headlines, descriptions, links, and pubDates if they exist
#         items = []
#         for entry in feed.entries:
#             item = {
#                 'title': entry.title,
#                 'description': entry.description,
#                 'link': entry.link
#             }
#             if hasattr(entry, 'published'):
#                 item['pubDate'] = entry.published
#             items.append(item)

#         # Format the items with titles, descriptions, and elapsed time if pubDate exists
#         formatted_items = []
#         current_time = datetime.now(pytz.UTC)
#         for item in items:
#             if 'pubDate' in item:
#                 pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
#                 pub_date = pub_date.replace(tzinfo=timezone.utc)
#                 if (current_time - pub_date).days <= max_days_old:
#                     time_elapsed = get_time_elapsed(pub_date)
#                     formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                     formatted_items.append(formatted_item)
#             else:
#                 formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                 formatted_items.append(formatted_item)
            
#             if len(formatted_items) >= max_entries:
#                 break

#         # Join the formatted items into a string with each item on a new line
#         items_string = '\n'.join(formatted_items)
#         items_string_out = 'Tässä tuoreimmat ulkomaanuutiset Ilta-Sanomista (is.fi):\n\n' + items_string

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
#             'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
#             'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
#         }

# # hae iltasanomat.fi / viihde-uutiset
# def get_is_viihde(max_days_old=DEFAULT_MAX_DAYS_OLD, max_entries=DEFAULT_MAX_ENTRIES):
#     try:
#         # Fetch the RSS feed
#         response = requests.get('https://www.is.fi/rss/viihde.xml')

#         # Parse the RSS feed
#         feed = feedparser.parse(response.content)

#         # Extract the headlines, descriptions, links, and pubDates if they exist
#         items = []
#         for entry in feed.entries:
#             item = {
#                 'title': entry.title,
#                 'description': entry.description,
#                 'link': entry.link
#             }
#             if hasattr(entry, 'published'):
#                 item['pubDate'] = entry.published
#             items.append(item)

#         # Filter items based on max_days_old
#         current_time = datetime.now(pytz.UTC)
#         filtered_items = []
#         for item in items:
#             if 'pubDate' in item:
#                 pub_date = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
#                 pub_date = pub_date.replace(tzinfo=timezone.utc)
#                 if (current_time - pub_date).days <= max_days_old:
#                     time_elapsed = get_time_elapsed(pub_date)
#                     formatted_item = f'<p><i>({time_elapsed})</i> <a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                     filtered_items.append(formatted_item)
#             else:
#                 formatted_item = f'<p><a href="{item["link"]}">{item["title"]}</a>: {item["description"]}</p>'
#                 filtered_items.append(formatted_item)

#             if len(filtered_items) >= max_entries:
#                 break

#         # Join the filtered items into a string with each item on a new line
#         items_string = '\n'.join(filtered_items)
#         items_string_out = 'Tässä tuoreimmat uutiset Ilta-Sanomien (is.fi) Viihde-osiosta:\n\n' + items_string

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
#             'content': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!",
#             'html': "Sori! En päässyt käsiksi IS:n uutisvirtaan. Mönkään meni! Pahoitteluni!"
#         }
    
