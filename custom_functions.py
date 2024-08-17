# custom_functions.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# you can add your own custom bot functionalities via OpenAI's API function calls with this.

import logging

# from api_get_openrouteservice import get_route, get_directions_from_addresses
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
        'description': '[Use if the user asks for weather, time, date, sunrise/sunset, moon phase, weather alerts, air quality etc info on a specific location!] Fetches weather data from OpenWeatherMap API and WeatherAPI for a given city, including current and 3-hour forecasts. Translate if needed. USE THIS TO FETCH LOCAL TIMES AT A LOCATION.',
        'parameters': {
            'type': 'object',
            'properties': {
                'city_name': {
                    'type': 'string',
                    'description': 'Name of the city to fetch the weather for (gets the current weather, 3-hour forecast, local sunrise and sunset info in the same request)'
                },
                'country': {
                    'type': 'string',
                    'description': 'Name of the country where the city is located, ask the user if unsure'
                }
            },
            'required': ['city_name', 'country']  # Specify that both city_name and country are required
        }
    }
    # ... other functions ...
]

custom_functions.append({
    'name': 'get_duckduckgo_search',
    'description': '[Use when the user requests for internet search results and if Perplexity API is too murky.] Fetches the first page search results from the first place DuckDuckGo for a given query. This function uses the Lynx browser to scrape the DuckDuckGo HTML results page.',
    'parameters': {
        'type': 'object',
        'properties': {
            'search_query': {
                'type': 'string',
                'description': 'The search query to fetch results for.'
            }
        },
        'required': ['search_query']  # Mark 'search_query' as a required property
    }
})

custom_functions.append({
    'name': 'get_website_dump',
    'description': '[Use to fetch information from a specific website.] Fetches the content of a website using the lynx --dump command and returns the plain text output.',
    'parameters': {
        'type': 'object',
        'properties': {
            'url': {
                'type': 'string',
                'description': 'The URL of the website to fetch content from.'
            }
        },
        'required': ['url']
    }
})

custom_functions.append({
        'name': 'get_directions_from_addresses',
        'description': '[Use when user requests for directions] Provides directions between two addresses using the OpenRouteService API.',
        'parameters': {
            'type': 'object',
            'properties': {
                'start_address': {
                    'type': 'string',
                    'description': 'Starting address of the route'
                },
                'end_address': {
                    'type': 'string',
                    'description': 'Ending address of the route'
                },
                'profile': {
                    'type': 'string',
                    'description': 'Transportation profile (e.g., driving-car, cycling-regular)',
                    'default': 'driving-car'  # Provide a default value if not specified
                }
            },
            'required': ['start_address', 'end_address']  # Mark required properties
        }
    }
)

# Update the custom_functions list with the new Perplexity API function
custom_functions.append({
    'name': 'query_perplexity',
    'description': '[Use for dynamic inquiries, current real-time events and/or fact-checking. ALWAYS USE TO FACT CHECK WHENEVER UNSURE, i.e. if user asks for something factual or current!] This queries the Perplexity.ai API using the pplx-70b-online model to answer and fact-check up-to-date information. Always form your question in English and as if you were the user! Pass the question directly as if you were asking a person. Use for checking real-time data.',
    'parameters': {
        'type': 'object',
        'properties': {
            'question': {
                'type': 'string',
                'description': 'The question or statement to fact-check or inquire about, do not refer to perplexity, ask the question directly, IN ENGLISH. ALWAYS ASK IN ENGLISH.'
            }
        }
    }
})

# AlphaVantage stock price check
custom_functions.append({
    'name': 'get_stock_price',
    'description': '[Use if the user asks for stock prices or financial data.] Fetches real-time stock price data from Yahoo! Finance API using either a direct stock symbol or a search keyword.',
    'parameters': {
        'type': 'object',
        'properties': {
            'symbol': {
                'type': 'string',
                'description': 'Direct stock symbol to fetch the stock price for.'
            },
            'search': {
                'type': 'string',
                'description': 'Search keyword to find the stock symbol.'
            }
        },
        'required': ['symbol', 'search']  # Specify that at least one of symbol or search is required
    }
})

# # jul 26 / 2024
# custom_functions.append({
#     'name': 'get_rss_feed',
#     'description': '[Use to fetch news from various RSS feeds.] Fetches news from specified RSS feed based on feed key.',
#     'parameters': {
#         'type': 'object',
#         'properties': {
#             'feed_key': {
#                 'type': 'string',
#                 'description': 'The key identifying which RSS feed to fetch (e.g.: `is_tuoreimmat` = newest from Ilta-Sanomat).'
#             }
#         },
#         'required': ['feed_key']
#     }
# })

# get date / time
# custom_functions.append({
#     'name': 'get_global_time',
#     'description': '[Use this ALWAYS when the user asks for their current date and time, use UTC if no area specified.] Runs the `date` command in Linux with specified cmdline options.',
#     'parameters': {
#         'type': 'object',
#         'properties': {
#             'command_options': {
#                 'type': 'string',
#                 'description': 'The `date` command line options to fetch the current time (e.g., "+%Y-%m-%d %H:%M:%S %Z", "--utc")'
#             }
#         },
#         'required': ['command_options']
#     }
# })


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Below are API function call features that can be enabled if and when needed.
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#
# > convert timezone according to coordinates
#
""" custom_functions.append({
    'name': 'get_local_time',
    'description': 'Fetches the current local time for a specified city or location.',
    'parameters': {
        'type': 'object',
        'properties': {
            'location_name': {
                'type': 'string',
                'description': 'Name of the location to fetch the local time for.'
            }
        },
        'required': ['location_name']
    }
}) """

#
# > get map image from maptiler (for maptiler's paid plan only)
#
"""
custom_functions.append({
    'name': 'get_map',
    'description': 'Generates a static map image for a given location, identified either by direct coordinates or an address.',
    'parameters': {
        'type': 'object',
        'properties': {
            'address': {
                'type': 'string',
                'description': 'Address of the location to fetch the map for. If provided, the service will first resolve the address to coordinates.'
            },
            'latitude': {
                'type': 'number',
                'description': 'Latitude of the location, required if address is not provided.'
            },
            'longitude': {
                'type': 'number',
                'description': 'Longitude of the location, required if address is not provided.'
            },
            'zoom': {
                'type': 'number',
                'description': 'Zoom level of the resulting map image.',
                'default': 12  # Example default value
            },
            'width': {
                'type': 'number',
                'description': 'Width of the map image in pixels.',
                'default': 400  # Example default value
            },
            'height': {
                'type': 'number',
                'description': 'Height of the map image in pixels.',
                'default': 300  # Example default value
            },
            'mapId': {
                'type': 'string',
                'description': 'Identifier of the map style to use for the image.',
                'default': 'streets'  # Default map style
            }
        },
        'required': []  # Note: Either 'address' or both 'latitude' and 'longitude' should be provided, you'll need to handle this logic in your function implementation.
    }
}) """

#
# > others; for reference
#
""" # location info
custom_functions.append({
    'name': 'get_location_info_from_coordinates',
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

""" # this is for searching between coordinates
custom_functions.append({
    'name': 'get_route',
    'description': 'Provides directions between two points using the OpenRouteService API.',
    'parameters': {
        'type': 'object',
        'properties': {
            'start_coords': {
                'type': 'string',
                'description': 'Starting coordinates of the route'
            },
            'end_coords': {
                'type': 'string',
                'description': 'Ending coordinates of the route'
            },
            'profile': {
                'type': 'string',
                'description': 'Transportation profile (e.g., driving-car, cycling-regular)'
            },
            'format': {
                'type': 'string',
                'description': 'Format of the route information (e.g., json)'
            }
        }
    }
}) """

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Below's a template on what other stuff you might want to add to your bot
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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