# api_get_openrouteservice.py

import os
import httpx
import logging
import json
import openai

# Function to retrieve the OpenRouteService API key
def get_openrouteservice_api_key():
    api_key = os.getenv('OPENROUTESERVICE_API_KEY')
    if not api_key:
        logging.error("OpenRouteService API key not set.")
        return None
    return api_key

# Async function to get geographic coordinates from an address
async def geocode_address(address, api_key):
    base_url = 'https://api.openrouteservice.org/geocode/search'
    params = {
        'api_key': api_key,
        'text': address
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            # Assumes the first feature is the most relevant match
            geometry = data['features'][0]['geometry']
            return geometry['coordinates']
        else:
            logging.error(f"Geocoding error: {response.text}")
            return None

# async function to get directions
async def get_route(start_coords, end_coords, profile="driving-car", format="json"):
    api_key = get_openrouteservice_api_key()
    if not api_key:
        return "OpenRouteService API key not set."

    base_url = f'https://api.openrouteservice.org/v2/directions/{profile}/{format}'
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json',
    }
    body = {
        'coordinates': [start_coords, end_coords],  # Correct format for coordinates
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(base_url, headers=headers, json=body)

        if response.status_code == 200:
            route_data = response.json()
            logging.info(f"API Response: {response.json()}")
            directions = format_route(route_data)
            return directions
        else:
            error_message = f"Failed to get directions. API error cause: {response.text}"
            logging.error(error_message)
            return error_message
        
# Function to format the routing data into a user-friendly message
def format_route(data):
    # Assuming 'routes' is the correct key and contains the expected data
    if 'routes' in data and len(data['routes']) > 0:
        # Assuming the first route and its first segment are what we're interested in
        steps = data['routes'][0]['segments'][0]['steps']
        instructions = [step['instruction'] for step in steps]
        return ' '.join(instructions)
    else:
        logging.error("Missing 'routes', 'segments', or 'steps' in API response.")
        return "Error: API response is missing required information."

# Function that wraps the geocoding of two addresses and getting the route between them
async def get_directions_from_addresses(start_address, end_address, profile="driving-car"):
    api_key = get_openrouteservice_api_key()
    if not api_key:
        return "OpenRouteService API key not set."

    start_coords = await geocode_address(start_address, api_key)
    end_coords = await geocode_address(end_address, api_key)
    
    if start_coords and end_coords:
        return await get_route(start_coords, end_coords, profile)
    else:
        return "Could not geocode one or both of the addresses. Please ask the user to clarify."

# Format the directions information and translate it if necessary.
async def format_and_translate_directions(bot, user_request, directions_info):
    # System message to instruct the model
    format_translate_system_message = {
        "role": "system",
        "content": "Format the incoming data into a human readable format. Translate if needed (depending on user's language) and format the data into a digestible Telegram message with emoji symbols and HTML parse mode tags. Use i.e. <b>Directions</b> etc. Respond in user's original language!"
    }

    # Prepare chat history with the user's request, system message, and directions info
    chat_history = [
        {"role": "user", "content": user_request},
        format_translate_system_message,
        {"role": "assistant", "content": directions_info}
    ]

    # Prepare the payload for the OpenAI API
    payload = {
        "model": bot.model,
        "messages": chat_history,
        "temperature": 0.5
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai.api_key}"
    }

    # Make the API request
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.openai.com/v1/chat/completions",
                                     data=json.dumps(payload),
                                     headers=headers,
                                     timeout=bot.timeout)
        response_json = response.json()

    # Extract the formatted and potentially translated response
    if response.status_code == 200 and 'choices' in response_json:
        translated_reply = response_json['choices'][0]['message']['content'].strip()
        bot_token_count = bot.count_tokens(translated_reply)  # Count the tokens in the translated reply
        bot.total_token_usage += bot_token_count  # Add to the total token usage
        bot.write_total_token_usage(bot.total_token_usage)  # Update the total token usage file
        logging.info(f"Sent this directions report to user: {translated_reply}")
        return translated_reply
    else:
        logging.error("Error in formatting and translating directions data.")
        return directions_info  # Return the original directions info in case of error
