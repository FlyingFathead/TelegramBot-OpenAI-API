# custom_functions.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# you can add your own custom bot functionalities via OpenAI's API function calls with this.

import logging

# from elasticsearch_handler import search_es  # Import the Elasticsearch search function

async def observe_chat():
    # Log observation or perform any silent monitoring if needed
    logging.info("Bot is currently observing the chat.")
    return "Observing"  # Or simply return None

# optional elasticsearch implementation
""" async def search_elasticsearch(query):
    # Call the Elasticsearch search function and return results
    return search_es(query) """

custom_functions = [
    {
        'name': 'get_weather',
        'description': '[Use only if weather is asked for a certain location!] Fetches weather data from OpenWeatherMap API for a given city, including current, hourly, and daily forecasts and sunrise/sunset times. Use the 3hour option for upcoming weather. fetch ONLY if user asks.',
        'parameters': {
            'type': 'object',
            'properties': {
                'city_name': {
                    'type': 'string',
                    'description': 'Name of the city to fetch the weather for'
                },
                'forecast_type': {
                    'type': 'string',
                    'description': 'Type of weather data, "current" for current weather+sunrise sunset data, "3hour" for all upcoming weather/forecast inquiries'
                },
                'language': {
                    'type': 'string',
                    'description': 'Language for weather descriptions (e.g., en, fi)'
                }
            }
        }
    }
    # ... other functions ...
]

""" # location info
custom_functions.append({
    'name': 'get_location_info',
    'description': 'Provides information and maps for a specific latitude and longitude.',
    'parameters': {
        'type': 'object',
        'properties': {
            'latitude': {
                'type': 'number',
                'description': 'Latitude of the location'
            },
            'longitude': {
                'type': 'number',
                'description': 'Longitude of the location'
            }
        }
    }
}) """

# here's a template on what other stuff you might want to add to your bot
unused_functions_template = [
    {
        'name': 'observe_chat',
        'description': '[Use at your own discernment] Observe the chat passively without making a response. Use this if you wish to remain silent. Use especially if someone wishes you to be quiet.',
        'parameters': {
            'type': 'object',
            'properties': {}  # No parameters needed for this function
        }
    },
    {
        'name': 'search_elasticsearch',
        'description': 'Search the backend with ElasticSearch',
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'Elasticsearch keyword(s)'
                }
            }
        }
    }
]