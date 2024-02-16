# api_get_openweathermap.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 
# >>> this weather fetcher module version: v0.44
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

# async def get_weather(city_name, forecast_type='current', exclude='', units='metric', lang='fi'):
# Correct structure for get_weather function
async def get_weather(city_name, forecast_type='current', country=None, exclude='', units='metric', lang='fi'):
    api_key = os.getenv('OPENWEATHERMAP_API_KEY')
    if not api_key:
        logging.error("[WARNING] OpenWeatherMap API key not set. You need to set the 'OPENWEATHERMAP_API_KEY' environment variable to use OpenWeatherMap API functionalities!")
        return "OpenWeatherMap API key not set."

    logging.info(f"Fetching weather data for city: {city_name}, forecast type: {forecast_type}, Country: {country}")

    if not city_name or city_name.lower() in ["defaultcity", ""]:
        return "Please ask the user to provide a valid city name."    

    base_url = 'http://api.openweathermap.org/data/2.5/'

    # Attempt to retrieve coordinates for all forecast types, except when direct city name usage is necessary
    if forecast_type in ['current', '3hour']:

        lat, lon, country = await get_coordinates(city_name, country=country)
        if lat is None or lon is None or country is None:
            logging.info("Failed to retrieve coordinates or country.")
            return "Unable to retrieve coordinates or country for the specified location. Ask the user for clarification."

        if forecast_type == 'current':
            url = f"{base_url}weather?lat={lat}&lon={lon}&appid={api_key}&units={units}&lang={lang}"
        elif forecast_type == '3hour':
            # Modify to use coordinates for 3-hour forecast if supported by your API plan
            # Note: OpenWeatherMap does not directly support '3hour' with these parameters; this is for illustration.
            # You might need to use the '/forecast' endpoint with city and country for a 3-hour forecast.
            url = f"{base_url}forecast?lat={lat}&lon={lon}&appid={api_key}&units={units}&lang={lang}"
    else:
        # For other types of forecasts or when coordinates are not required or available
        query = f"{city_name},{country}" if country else city_name
        url = f"{base_url}forecast?q={query}&appid={api_key}&units={units}&lang={lang}"

    # paid subscription forecast types
    # elif forecast_type == 'hourly':
        # url = f"{base_url}onecall?lat={lat}&lon={lon}&exclude=current,minutely,daily&appid={api_key}&units={units}&lang={lang}"
    # elif forecast_type == 'daily':
        # url = f"{base_url}onecall?lat={lat}&lon={lon}&exclude=current,minutely,hourly&appid={api_key}&units={units}&lang={lang}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        logging.info(f"Received response with status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logging.info(f"OpenWeatherMap API response data: {data}")

            if forecast_type == 'current':
                
                # Include additional details from the response
                if 'weather' in data and 'main' in data:
                    weather_description = data['weather'][0]['description']
                    temperature = data['main']['temp']
                    feels_like = data['main']['feels_like']
                    temp_min = data['main']['temp_min']
                    temp_max = data['main']['temp_max']
                    pressure = data['main']['pressure']
                    humidity = data['main']['humidity']
                    wind_speed = data['wind']['speed']
                    wind_direction = data['wind']['deg']
                    visibility = data.get('visibility', 'N/A')
                    wind_direction_deg = data['wind']['deg']
                    wind_direction_cardinal = degrees_to_cardinal(wind_direction_deg)
                    snow_1h = data.get('snow', {}).get('1h', 'N/A')

                    # Obtain the timezone of the location
                    tf = TimezoneFinder()
                    timezone_str = tf.timezone_at(lat=lat, lng=lon)  # get timezone using the coordinates
                    local_timezone = pytz.timezone(timezone_str)

                    # Format sunrise and sunset times
                    # sunrise_time = datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M')
                    # sunset_time = datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M')
                                                            
                    # Convert timestamps to datetime objects
                    sunrise_time_utc = datetime.datetime.utcfromtimestamp(data['sys']['sunrise'])
                    sunset_time_utc = datetime.datetime.utcfromtimestamp(data['sys']['sunset'])

                    # Add tzinfo and convert to local timezone
                    sunrise_time_local = sunrise_time_utc.replace(tzinfo=pytz.utc).astimezone(local_timezone)
                    sunset_time_local = sunset_time_utc.replace(tzinfo=pytz.utc).astimezone(local_timezone)

                    # Format to strings (only time, no date)
                    sunrise_time_utc_str = sunrise_time_utc.strftime('%H:%M')
                    sunset_time_utc_str = sunset_time_utc.strftime('%H:%M')
                    sunrise_time_local_str = sunrise_time_local.strftime('%H:%M')
                    sunset_time_local_str = sunset_time_local.strftime('%H:%M')

                    # Convert temperatures from Celsius to Fahrenheit
                    temp_fahrenheit = (temperature * 9/5) + 32
                    feels_like_fahrenheit = (feels_like * 9/5) + 32
                    temp_min_fahrenheit = (temp_min * 9/5) + 32
                    temp_max_fahrenheit = (temp_max * 9/5) + 32

                    # Extract the country code from the API response
                    country_code = data['sys']['country']  # This extracts 'CA' for Canada

                    # Directly use `country_code` for the `country_info` variable
                    country_info = f"Country: {country_code}"

                    coordinates_info = f"lat: {lat}, lon: {lon}"

                    detailed_weather_info = (
                        f"Sää paikassa {city_name}: {data['weather'][0]['description']}, "
                        f"Lämpötila: {data['main']['temp']}°C / {temp_fahrenheit:.1f}°F (Tuntuu kuin: {data['main']['feels_like']}°C / {feels_like_fahrenheit:.1f}°F), "
                        f"Minimi: {data['main']['temp_min']}°C / {temp_min_fahrenheit:.1f}°F, Maksimi: {data['main']['temp_max']}°C / {temp_max_fahrenheit:.1f}°F,"
                        f"Ilmanpaine: {data['main']['pressure']} hPa, Ilmankosteus: {data['main']['humidity']}%, "
                        f"Tuulen nopeus: {data['wind']['speed']} m/s, Tuulen suunta: {data['wind']['deg']} astetta ({wind_direction_cardinal})"
                        f"Tuulenpuuskat: {data['wind'].get('gust', 'N/A')} m/s, "
                        f"Näkyvyys: {data.get('visibility', 'N/A')} metriä, "
                        f"Lumisade (viimeisen 1h aikana): {data.get('snow', {}).get('1h', 'N/A')} mm, "
                        f"Pilvisyys: {data['clouds']['all']}%, "
                        f"Auringonnousu (UTC): {sunrise_time_utc_str} (paikallinen aika): {sunrise_time_local_str}, "
                        f"Auringonlasku (UTC): {sunset_time_utc_str} (paikallinen aika): {sunset_time_local_str}"
                        f"Koordinaatit: {coordinates_info} (Maa: {country_info})"
                    )
                    logging.info(f"Formatted weather data being sent to the model: {detailed_weather_info}")
                    return detailed_weather_info
                else:
                    logging.error(f"Failed to fetch weather data: {response.text}")
                    return "Säädataa ei löytynyt."
            
            # 3-hour forecast data
            elif forecast_type == '3hour':
                if 'list' in data:
                    forecasts = data['list']
                    formatted_forecasts = []

                    tf = TimezoneFinder()
                    # Define local_timezone outside the for loop
                    # Ensure that you have valid latitude and longitude values
                    lat = data['city']['coord']['lat']
                    lon = data['city']['coord']['lon']
                    timezone_str = tf.timezone_at(lat=lat, lng=lon)
                    local_timezone = pytz.timezone(timezone_str) if timezone_str else pytz.utc
                    
                    for forecast_data in forecasts[:5]:  # Adjust the range as needed
                        # different formats;
                        # time = datetime.fromtimestamp(forecast_data['dt']).strftime('%Y-%m-%d %H:%M:%S')
                        # time = datetime.fromtimestamp(forecast_data['dt']).strftime('%d.%m.%Y klo %H:%M')                                                
                        time = datetime.datetime.utcfromtimestamp(forecast_data['dt']).strftime('%Y-%m-%d %H:%M:%S')

                        # Convert UTC time to local time
                        utc_time = datetime.datetime.utcfromtimestamp(forecast_data['dt'])
                        local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(local_timezone)
                        local_time_str = local_time.strftime('%Y-%m-%d %H:%M:%S')
                        utc_time_str = utc_time.strftime('%Y-%m-%d %H:%M:%S')

                        temp = forecast_data['main']['temp']

                        # fahrenheit conversion
                        temp_celsius = forecast_data['main']['temp']
                        temp_fahrenheit = (temp_celsius * 9/5) + 32  # Convert to Fahrenheit                        
                        
                        description = forecast_data['weather'][0]['description']
                        wind_speed = forecast_data['wind']['speed']
                        humidity = forecast_data['main']['humidity']
                        pressure = forecast_data['main']['pressure']
                        clouds = forecast_data['clouds']['all']
                        rain = forecast_data.get('rain', {}).get('3h', 'N/A')  # '3h' key for 3-hour rain volume

                        formatted_forecasts.append(
                            f"- {local_time_str} (Local time) / {utc_time_str} (UTC): Lämpötila: {temp}°C / {temp_fahrenheit:.1f}°F, {description.capitalize()}, Tuuli: {wind_speed} m/s, "
                            f"Ilmanpaine: {pressure} hPa, Ilmankosteus: {humidity}%, Pilvisyys: {clouds}%, "
                            f"Sade (viimeisen 3h aikana): {rain} mm"
                        )

                    final_forecast = f"Kolmen tunnin sääennuste, {city_name}:\n" + "\n".join(formatted_forecasts)
                    logging.info(f"Formatted 3-hour forecast data being sent: {final_forecast}")
                    return final_forecast
                else:
                    logging.error(f"Failed to fetch weather data: {response.text}")
                    return "En saanut haettua kolmen tunnin sääennustetta."

            # hourly forecast // not available in free plan
            elif forecast_type == 'hourly':
                # Process hourly forecast data
                if 'hourly' in data:
                    hourly_forecasts = data['hourly']
                    # Format and return the first few hours as an example
                    formatted_hourly_forecasts = []
                    for hour_data in hourly_forecasts[:5]:  # Example: Get first 5 hours data
                        # time = datetime.fromtimestamp(hour_data['dt']).strftime('%Y-%m-%d %H:%M:%S') # system time conversion
                        time = datetime.datetime.utcfromtimestamp(hour_data['dt']).strftime('%Y-%m-%d %H:%M:%S')
                        temp = hour_data['temp']
                        description = hour_data['weather'][0]['description']
                        formatted_hourly_forecasts.append(f"{time} (UTC): {temp}°C, {description}")
                    return "Lähituntien sääennuste:\n" + "\n".join(formatted_hourly_forecasts)
                else:
                    logging.error(f"Failed to fetch weather data: {response.text}")
                    return "Lähituntien sääennustetta ei saatavilla."

            # daily forecast // not available in OpenWeatherMapAPI's free plan
            elif forecast_type == 'daily':
                # Process daily forecast data
                if 'daily' in data:
                    daily_forecasts = data['daily']
                    # Format and return the first few days as an example
                    formatted_daily_forecasts = []
                    for day_data in daily_forecasts[:3]:  # Example: Get first 3 days data
                        date = datetime.datetime.fromtimestamp(day_data['dt']).strftime('%Y-%m-%d')
                        min_temp = day_data['temp']['min']
                        max_temp = day_data['temp']['max']
                        description = day_data['weather'][0]['description']
                        formatted_daily_forecasts.append(f"{date}: Min {min_temp}°C, Max {max_temp}°C, {description}")
                    return "Lähipäivien sääennuste:\n" + "\n".join(formatted_daily_forecasts)
                else:
                    logging.error(f"Failed to fetch weather data: {response.text}")
                    return "Lähipäivien sääennustetta ei saatavilla."

        else:
            logging.info(f"Failed to fetch weather data: {response.text}")            
            return "Sori, juuri nyt ei onnistunut säätietojen haku OpenWeatherMapin kautta!"

# get coordinates
async def get_coordinates(city_name, country=None):
    # Initialize lat, lon, and country with None to ensure they are defined
    lat = lon = None
    resolved_country = None  # This will hold the country information extracted from the response

    logging.info(f"Coordinates for {city_name}, {country}: Latitude: {lat}, Longitude: {lon}")
    # Retrieve MapTiler API key from environment variables
    api_key = os.getenv('MAPTILER_API_KEY')
    if not api_key:
        logging.info("[WARNING] MapTiler API key not set. You need to set the 'MAPTILER_API_KEY' environment variable in order to be able to use coordinate lookups, i.e. for weather data!")        
        return None, None, None

    # Construct the API request URL with potential country parameter
    query = f"{city_name}"
    if country:
        query += f", {country}"  # Append country to the query if specified
    geocode_url = f"https://api.maptiler.com/geocoding/{query}.json?key={api_key}"
    logging.info(f"Making API request to URL: {geocode_url}")    

    async with httpx.AsyncClient() as client:
        response = await client.get(geocode_url)
        logging.info(f"Received response with status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logging.info(f"Response data: {data}")            
            # Attempt to extract latitude and longitude from the response
            if data['features']:
                feature = data['features'][0]
                lat = feature['geometry']['coordinates'][1]
                lon = feature['geometry']['coordinates'][0]
                resolved_country = feature['properties'].get('country', 'Country not available')
                logging.info(f"Coordinates for {city_name}, {resolved_country}: Latitude: {lat}, Longitude: {lon}")
                return lat, lon, resolved_country
            else:
                logging.error("No features found in the geocoding response.")
                return None, None, None
        else:
            logging.error(f"Failed to fetch coordinates: {response.text}")            
            return None, None, None

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

