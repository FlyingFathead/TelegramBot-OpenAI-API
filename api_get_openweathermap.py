# api_get_openweathermap.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 
# >>> this weather fetcher module version: v0.46 (25-May-2024)
#
# This API functionality requires both OpenWeatherMap and MapTiler API keys.
# You can get both from the corresponding service providers.
# Once you have the API keys, add them to your environment variables:
# export OPENWEATHERMAP_API_KEY="<your API key>"
# export MAPTILER_API_KEY="<your API key>"

import datetime
import json
import httpx
import os
import logging
import openai

import datetime
from timezonefinder import TimezoneFinder
import pytz

# Stuff we want to get via WeatherAPI:
from api_get_weatherapi import get_moon_phase, get_timezone, get_daily_forecast, get_current_weather_via_weatherapi

# get the combined weather
async def get_weather(city_name, country, exclude='', units='metric', lang='fi'):
    api_key = os.getenv('OPENWEATHERMAP_API_KEY')
    if not api_key:
        logging.error("[WARNING] OpenWeatherMap API key not set. You need to set the 'OPENWEATHERMAP_API_KEY' environment variable to use OpenWeatherMap API functionalities!")
        return "OpenWeatherMap API key not set."

    logging.info(f"Fetching weather data for city: {city_name}, Country: {country}")

    if not city_name or not country or city_name.lower() in ["defaultcity", ""]:
        return "Please provide a valid city name and country."

    base_url = 'http://api.openweathermap.org/data/2.5/'

    lat, lon, country = await get_coordinates(city_name, country=country)
    if lat is None or lon is None or country is None:
        logging.info("Failed to retrieve coordinates or country.")
        return "[Unable to retrieve coordinates or country for the specified location. Ask the user for clarification.]"

    current_weather_url = f"{base_url}weather?lat={lat}&lon={lon}&appid={api_key}&units={units}&lang={lang}"
    forecast_url = f"{base_url}forecast?lat={lat}&lon={lon}&appid={api_key}&units={units}&lang={lang}"

    async with httpx.AsyncClient() as client:
        current_weather_response = await client.get(current_weather_url)
        forecast_response = await client.get(forecast_url)

        logging.info(f"Current weather response status: {current_weather_response.status_code}")
        logging.info(f"Forecast response status: {forecast_response.status_code}")

        if current_weather_response.status_code == 200 and forecast_response.status_code == 200:
            current_weather_data = current_weather_response.json()
            forecast_data = forecast_response.json()
            moon_phase_data = await get_moon_phase(lat, lon)
            daily_forecast_data = await get_daily_forecast(f"{lat},{lon}")
            current_weather_data_from_weatherapi = await get_current_weather_via_weatherapi(f"{lat},{lon}")
            return await combine_weather_data(city_name, country, lat, lon, current_weather_data, forecast_data, moon_phase_data, daily_forecast_data, current_weather_data_from_weatherapi)
        else:
            logging.error(f"Failed to fetch weather data: {current_weather_response.text} / {forecast_response.text}")
            return "[Inform the user that data fetching from OpenWeatherMap API failed, current information could not be fetched. Reply in the user's language.]"

# get coordinates
async def get_coordinates(city_name, country=None):
    lat = lon = None
    resolved_country = None

    logging.info(f"Coordinates for {city_name}, {country}: Latitude: {lat}, Longitude: {lon}")
    api_key = os.getenv('MAPTILER_API_KEY')
    if not api_key:
        logging.info("[WARNING] MapTiler API key not set. You need to set the 'MAPTILER_API_KEY' environment variable in order to be able to use coordinate lookups, i.e. for weather data!")
        return None, None, None

    query = f"{city_name}"
    if country:
        query += f", {country}"
    geocode_url = f"https://api.maptiler.com/geocoding/{query}.json?key={api_key}"
    logging.info(f"Making API request to URL: {geocode_url}")

    async with httpx.AsyncClient() as client:
        response = await client.get(geocode_url)
        logging.info(f"Received response with status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logging.info(f"Response data: {data}")
            if data['features']:
                feature = data['features'][0]
                lat = feature['geometry']['coordinates'][1]
                lon = feature['geometry']['coordinates'][0]
                resolved_country = feature['properties'].get('country_code', 'Country not available')
                logging.info(f"Coordinates for {city_name}, {resolved_country}: Latitude: {lat}, Longitude: {lon}")
                return lat, lon, resolved_country
            else:
                logging.error("No features found in the geocoding response.")
                return None, None, None
        else:
            logging.error(f"Failed to fetch coordinates: {response.text}")
            return None, None, None

# the function below can be implemented to use for POI lookups
async def get_location_info_from_coordinates(latitude, longitude):
    logging.info(f"Fetching location information for coordinates: Latitude: {latitude}, Longitude: {longitude}")    
    # Retrieve MapTiler API key from environment variables
    api_key = os.getenv('MAPTILER_API_KEY')
    if not api_key:
        logging.info("[WARNING] MapTiler API key not set. You need to set the 'MAPTILER_API_KEY' environment variable for this function to work!")        
        return "MapTiler API key not set."

    # Construct the API request URL for reverse geocoding
    reverse_geocode_url = f"https://api.maptiler.com/geocoding/{longitude},{latitude}.json?key={api_key}"
    logging.info(f"Making API request to URL: {reverse_geocode_url}")    

    async with httpx.AsyncClient() as client:
        response = await client.get(reverse_geocode_url)
        logging.info(f"Received response with status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logging.info(f"Response data: {data}")            
            # Process the response data to extract useful information
            # For example, you might extract the nearest city name, points of interest, etc.
            # Return this information
            return data
        else:
            logging.info(f"Failed to fetch location information: {response.text}")            
            return "Failed to fetch location information."
    
# Format and return detailed weather information along with location data
def format_weather_response(city_name, country, weather_info):
    # Example of how you might construct the message with location and weather data
    location_info = f"[{city_name}, {country}]\n\n"
    return f"{location_info} {weather_info}"

# wind direction from degrees to cardinal
def degrees_to_cardinal(d):
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    ix = int((d + 11.25)/22.5 - 0.02)  # Subtract a small epsilon to correct edge case at North (360 degrees)
    return dirs[ix % 16]

# combined weather data
async def combine_weather_data(city_name, country, lat, lon, current_weather_data, forecast_data, moon_phase_data, daily_forecast_data, current_weather_data_from_weatherapi):
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=lat, lng=lon)  # get timezone using the coordinates
    local_timezone = pytz.timezone(timezone_str)

    # Current weather details from OpenWeatherMap
    weather_description = current_weather_data['weather'][0]['description']
    temperature = current_weather_data['main']['temp']
    feels_like = current_weather_data['main']['feels_like']
    temp_min = current_weather_data['main']['temp_min']
    temp_max = current_weather_data['main']['temp_max']
    pressure = current_weather_data['main']['pressure']
    humidity = current_weather_data['main']['humidity']
    wind_speed = current_weather_data['wind']['speed']
    wind_direction = current_weather_data['wind']['deg']
    wind_direction_cardinal = degrees_to_cardinal(wind_direction)
    visibility = current_weather_data.get('visibility', 'N/A')
    snow_1h = current_weather_data.get('snow', {}).get('1h', 'N/A')

    # UV index from WeatherAPI
    uv_index = current_weather_data_from_weatherapi['uv_index']

    sunrise_time_utc = datetime.datetime.utcfromtimestamp(current_weather_data['sys']['sunrise'])
    sunset_time_utc = datetime.datetime.utcfromtimestamp(current_weather_data['sys']['sunset'])
    sunrise_time_local = sunrise_time_utc.replace(tzinfo=pytz.utc).astimezone(local_timezone)
    sunset_time_local = sunset_time_utc.replace(tzinfo=pytz.utc).astimezone(local_timezone)
    sunrise_time_local_str = sunrise_time_local.strftime('%H:%M')
    sunset_time_local_str = sunset_time_local.strftime('%H:%M')

    temp_fahrenheit = (temperature * 9/5) + 32
    feels_like_fahrenheit = (feels_like * 9/5) + 32
    temp_min_fahrenheit = (temp_min * 9/5) + 32
    temp_max_fahrenheit = (temp_max * 9/5) + 32

    country_code = current_weather_data['sys']['country']
    country_info = f"Country: {country_code}"
    coordinates_info = f"lat: {lat}, lon: {lon}"

    # Get current UTC and local times
    current_time_utc = datetime.datetime.utcnow()
    current_time_local = current_time_utc.replace(tzinfo=pytz.utc).astimezone(local_timezone)
    current_time_utc_str = current_time_utc.strftime('%Y-%m-%d %H:%M:%S')
    current_time_local_str = current_time_local.strftime('%Y-%m-%d %H:%M:%S')

    detailed_weather_info = (
        f"Sää paikassa {city_name}, {country_code} (UTC: {current_time_utc_str}, Paikallinen aika: {current_time_local_str}): {weather_description}, "
        f"Lämpötila: {temperature}°C / {temp_fahrenheit:.1f}°F (Tuntuu kuin: {feels_like}°C / {feels_like_fahrenheit:.1f}°F), "
        f"Minimi: {temp_min}°C / {temp_min_fahrenheit:.1f}°F, Maksimi: {temp_max}°C / {temp_max_fahrenheit:.1f}°F, "
        f"Ilmanpaine: {pressure} hPa, Ilmankosteus: {humidity}%, "
        f"Tuulen nopeus: {wind_speed} m/s, Tuulen suunta: {wind_direction} astetta ({wind_direction_cardinal}), "
        f"Näkyvyys: {visibility} metriä, "
        f"Lumisade (viimeisen 1h aikana): {snow_1h} mm, "
        f"Auringonnousu: {sunrise_time_local_str}, "
        f"Auringonlasku: {sunset_time_local_str}, "
        f"Koordinaatit: {coordinates_info} (Maa: {country_info}), "
        f"Kuun vaihe: {moon_phase_data}, "
        f"UV-indeksi: {uv_index}"  # Include UV index in the detailed weather info
    )

    # Include additional WeatherAPI data (daily forecast, air quality, and alerts)
    if daily_forecast_data:
        air_quality_data = daily_forecast_data['air_quality']
        alerts = daily_forecast_data['alerts']

        air_quality_info = "\nIlmanlaatu:\n" + "\n".join(
            [f"{key}: {value}" for key, value in air_quality_data.items()]
        )

        alerts_info = "\nSäävaroitukset:\n" + (
            "\n".join(
                [f"Alert: {alert['headline']}\nDescription: {alert['desc']}\nInstructions: {alert['instruction']}\n"
                 for alert in alerts['alert']]
            ) if 'alert' in alerts and alerts['alert'] else "No weather alerts."
        )

        detailed_weather_info += f"\n{air_quality_info}\n{alerts_info}"

    # 3-hour forecast details
    forecasts = forecast_data['list']
    formatted_forecasts = []
    
    for forecast_data in forecasts[:5]:  # Adjust the range as needed
        utc_time = datetime.datetime.utcfromtimestamp(forecast_data['dt'])
        local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(local_timezone)
        local_time_str = local_time.strftime('%Y-%m-%d %H:%M:%S')
        utc_time_str = utc_time.strftime('%Y-%m-%d %H:%M:%S')

        temp = forecast_data['main']['temp']
        temp_fahrenheit = (temp * 9/5) + 32
        description = forecast_data['weather'][0]['description']
        wind_speed = forecast_data['wind']['speed']
        humidity = forecast_data['main']['humidity']
        pressure = forecast_data['main']['pressure']
        clouds = forecast_data['clouds']['all']
        rain = forecast_data.get('rain', {}).get('3h', 'N/A')

        formatted_forecasts.append(
            f"- {city_name}: {local_time_str} (Local time, 24hr format) / {utc_time_str} (UTC, 24hr format): Lämpötila: {temp}°C / {temp_fahrenheit:.1f}°F, {description.capitalize()}, Tuuli: {wind_speed} m/s, "
            f"Ilmanpaine: {pressure} hPa, Ilmankosteus: {humidity}%, Pilvisyys: {clouds}%, "
            f"Sade (viimeisen 3h aikana): {rain} mm"
        )

    final_forecast = f"Kolmen tunnin sääennuste, {city_name}:\n" + "\n".join(formatted_forecasts)

    combined_info = f"{detailed_weather_info}\n\n{final_forecast}"
    logging.info(f"Formatted combined weather data being sent: {combined_info}")
    return combined_info

# Format the weather information and translate it if necessary.        
async def format_and_translate_weather(bot, user_request, weather_info):
    
    # System message to instruct the model
    format_translate_system_message = {
        "role": "system",
        "content": "Translate if needed (depending on user's language) and format the data into a digestable Telegram message with emoji symbols and html parsemode tags. Use i.e. <b>type</b> etc. Respond in user's original language, DO NOT OMIT DETAILS! INCLUDE THE COUNTRY INFO IF AVAILABLE."
    }

    # Prepare chat history with the user's request, system message, and weather info
    chat_history = [
        {"role": "user", "content": user_request},
        format_translate_system_message,
        {"role": "assistant", "content": weather_info}
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
        logging.info(f"Sent this weather report to user: {translated_reply}")
        return translated_reply
    else:
        logging.error("Error in formatting and translating weather data.")
        return weather_info  # Return the original weather info in case of error
    
