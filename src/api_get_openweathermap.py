# api_get_openweathermap.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 
# >>> weather fetcher module version: v0.75053
# >>> (Updated Oct 8 2024)
#
# This API functionality requires both OpenWeatherMap and MapTiler API keys.
# You can get both from the corresponding service providers.
# Once you have the API keys, add them to your environment variables:
# export OPENWEATHERMAP_API_KEY="<your API key>"
# export MAPTILER_API_KEY="<your API key>"

# Import the NWS data fetching function
from api_get_nws_weather import get_nws_forecast, get_nws_alerts
from config_paths import NWS_USER_AGENT, NWS_RETRIES, NWS_RETRY_DELAY, FETCH_NWS_FORECAST, FETCH_NWS_ALERTS, NWS_ELIGIBLE_COUNTRIES, NWS_ONLY_ELIGIBLE_COUNTRIES

# linter annotation (use only if you use the v2 method of `get_coordinates`)
# from typing import Optional, Tuple

# date & time utils
import datetime as dt
from dateutil import parser
from timezonefinder import TimezoneFinder
import pytz

import json
import httpx
import os
import logging
import openai

# Stuff we want to get via WeatherAPI:
from api_get_weatherapi import get_moon_phase, get_timezone, get_daily_forecast, get_current_weather_via_weatherapi, get_astronomy_data

# Import the additional data fetching function for Finland
from api_get_additional_weather_data import get_additional_data_dump

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

    lat, lon, resolved_country = await get_coordinates(city_name, country=country)
    if lat is None or lon is None or resolved_country is None:
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
            astronomy_data = await get_astronomy_data(lat, lon)  # Fetch astronomy data

            # Fetch additional data for Finland
            additional_data = ""
            if resolved_country.lower() == "fi":  # Case-insensitive check
                logging.info("Fetching additional weather data for Finland.")
                additional_data = await get_additional_data_dump()
                logging.info(f"Additional data fetched: {additional_data}")

            # // (old method)
            # combined_data = await combine_weather_data(city_name, resolved_country, lat, lon, current_weather_data, forecast_data, moon_phase_data, daily_forecast_data, current_weather_data_from_weatherapi, astronomy_data, additional_data)
            # return combined_data

            # Check if NWS should only be used for eligible countries
            if NWS_ONLY_ELIGIBLE_COUNTRIES and resolved_country.upper() not in NWS_ELIGIBLE_COUNTRIES:
                logging.info(f"NOTE: NWS data will not be fetched as {resolved_country.upper()} is not in the eligible country list.")
                nws_forecast = None
                nws_forecast_hourly = None
                nws_alerts = None
            else:
                # Ensure that NWS API requests are made only if eligible
                try:
                    logging.info("Fetching NWS data.")
                    nws_data = await get_nws_forecast(lat, lon)
                    if nws_data:
                        logging.info("NWS data fetched successfully.")
                        nws_forecast = nws_data.get('nws_forecast')
                        nws_forecast_hourly = nws_data.get('nws_forecast_hourly')
                    else:
                        logging.warning("Failed to fetch NWS data.")
                        nws_forecast = None
                        nws_forecast_hourly = None

                    # Fetch NWS alerts data only if the forecast is successful
                    logging.info("Fetching NWS alerts data.")
                    nws_alerts = await get_nws_alerts(lat, lon)
                    if nws_alerts:
                        logging.info(f"Fetched {len(nws_alerts)} active NWS alerts.")
                    else:
                        logging.info("No active NWS alerts found.")
                except Exception as e:
                    logging.error(f"Error fetching NWS data: {e}")
                    nws_forecast = None
                    nws_forecast_hourly = None
                    nws_alerts = None

            # combine the weather data
            combined_data = await combine_weather_data(
                city_name, resolved_country, lat, lon,
                current_weather_data, forecast_data, moon_phase_data,
                daily_forecast_data, current_weather_data_from_weatherapi,
                astronomy_data, additional_data, nws_forecast, nws_forecast_hourly
            )
            return combined_data        

        else:
            logging.error(f"Failed to fetch weather data: {current_weather_response.text} / {forecast_response.text}")
            return "[Inform the user that data fetching the weather data failed, current information could not be fetched. Reply in the user's language.]"

# # get coordinates (method 2; might introduce complexity; needs `Typing`)
# async def get_coordinates(city_name: str, country: Optional[str] = None) -> Tuple[Optional[float], Optional[float], Optional[str]]:
#     lat: Optional[float] = None
#     lon: Optional[float] = None
#     resolved_country: Optional[str] = None

#     logging.info(f"Coordinates for {city_name}, {country}: Latitude: {lat}, Longitude: {lon}")
#     api_key = os.getenv('MAPTILER_API_KEY')
    
#     if not api_key:
#         logging.info("[WARNING] MapTiler API key not set. You need to set the 'MAPTILER_API_KEY' environment variable to use coordinate lookups!")
#         return None, None, None

#     query = f"{city_name}"
#     if country:
#         query += f", {country}"
        
#     geocode_url = f"https://api.maptiler.com/geocoding/{query}.json?key={api_key}"
#     logging.info(f"Making API request to URL: {geocode_url}")

#     async with httpx.AsyncClient() as client:
#         response = await client.get(geocode_url)
#         logging.info(f"Received response with status code: {response.status_code}")

#         if response.status_code == 200:
#             data = response.json()
#             logging.info(f"Response data: {data}")

#             if data.get('features'):
#                 feature = data['features'][0]
#                 lat = feature['geometry']['coordinates'][1]
#                 lon = feature['geometry']['coordinates'][0]
#                 resolved_country = feature['properties'].get('country_code', 'Unknown')
#                 logging.info(f"Coordinates for {city_name}, {resolved_country}: Latitude: {lat}, Longitude: {lon}")
#                 return lat, lon, resolved_country
#             else:
#                 logging.error("No features found in the geocoding response.")
#                 return None, None, None
#         else:
#             logging.error(f"Failed to fetch coordinates: {response.text}")
#             return None, None, None

# # // (old method for country lookup)
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

# Function to convert 12-hour AM/PM time to 24-hour time
def convert_to_24_hour(time_str, timezone_str):
    try:
        dt_time = dt.datetime.strptime(time_str, '%I:%M %p')
        local_timezone = pytz.timezone(timezone_str)
        local_time = local_timezone.localize(dt_time)
        formatted_time = local_time.strftime('%H:%M')
        logging.info(f"Converted time {time_str} to {formatted_time} in timezone {timezone_str}")
        return formatted_time
    except Exception as e:
        logging.error(f"Error converting time string {time_str}: {e}")
        return "Invalid time"

# combined weather data
# async def combine_weather_data(city_name, country, lat, lon, current_weather_data, forecast_data, moon_phase_data, daily_forecast_data, current_weather_data_from_weatherapi, astronomy_data, additional_data):
# Define the combine_weather_data function with NWS integration
async def combine_weather_data(city_name, resolved_country, lat, lon, current_weather_data, forecast_data, moon_phase_data, daily_forecast_data, current_weather_data_from_weatherapi, astronomy_data, additional_data, nws_forecast, nws_forecast_hourly):
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=lat, lng=lon)
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

    # Data to get from WeatherAPI, with checks for missing data
    if current_weather_data_from_weatherapi:
        uv_index = current_weather_data_from_weatherapi.get('uv_index', 'N/A')
        visibility_wapi = current_weather_data_from_weatherapi.get('visibility', 'N/A')
        condition_wapi = current_weather_data_from_weatherapi.get('condition', 'N/A')
    else:
        uv_index = 'N/A'
        visibility_wapi = 'N/A'
        condition_wapi = 'N/A'

    # Daily forecast data, with default values if not available
    if daily_forecast_data:
        air_quality_data = daily_forecast_data['air_quality']
        alerts = daily_forecast_data['alerts']
        forecast_date = daily_forecast_data['date']
        forecast_temperature = daily_forecast_data['temperature']
        forecast_condition = daily_forecast_data['condition']
        forecast_wind = daily_forecast_data['wind']
        forecast_precipitation = daily_forecast_data['precipitation']
        forecast_uv_index = daily_forecast_data['uv_index']
    else:
        air_quality_data = {}
        alerts = {}
        forecast_date = 'N/A'
        forecast_temperature = 'N/A'
        forecast_condition = 'N/A'
        forecast_wind = 'N/A'
        forecast_precipitation = 'N/A'
        forecast_uv_index = 'N/A'

    # Astronomy data
    moonrise_time = convert_to_24_hour(astronomy_data['moonrise'], timezone_str)
    moonset_time = convert_to_24_hour(astronomy_data['moonset'], timezone_str)
    moon_illumination = astronomy_data['moon_illumination']

    sunrise_time_utc = dt.datetime.utcfromtimestamp(current_weather_data['sys']['sunrise'])
    sunset_time_utc = dt.datetime.utcfromtimestamp(current_weather_data['sys']['sunset'])
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
    current_time_utc = dt.datetime.utcnow()
    current_time_local = current_time_utc.replace(tzinfo=pytz.utc).astimezone(local_timezone)
    current_time_utc_str = current_time_utc.strftime('%Y-%m-%d %H:%M:%S')
    current_time_local_str = current_time_local.strftime('%Y-%m-%d %H:%M:%S')

    detailed_weather_info = (
        f"Sää paikassa {city_name}, {country_code} (UTC: {current_time_utc_str}, Paikallinen aika: {current_time_local_str}): {weather_description}, "
        f"Lämpötila: {temperature}°C / {temp_fahrenheit:.1f}°F (Tuntuu kuin: {feels_like}°C / {feels_like_fahrenheit:.1f}°F), "
        f"Minimi: {temp_min}°C / {temp_min_fahrenheit:.1f}°F, Maksimi: {temp_max}°C / {temp_max_fahrenheit:.1f}°F, "
        f"Ilmanpaine: {pressure} hPa, Ilmankosteus: {humidity}%, "
        f"Tuulen nopeus: {wind_speed} m/s, Tuulen suunta: {wind_direction} astetta ({wind_direction_cardinal}), "
        f"Näkyvyys: {visibility} metriä [OpenWeatherMap] | {visibility_wapi} km [WeatherAPI], "
        f"Lumisade (viimeisen 1h aikana): {snow_1h} mm, "
        f"Auringonnousu: {sunrise_time_local_str}, "
        f"Auringonlasku: {sunset_time_local_str}, "
        f"Koordinaatit: {coordinates_info} (Maa: {country_info}), "
        f"Kuun vaihe: {moon_phase_data}, "
        f"UV-indeksi [WeatherAPI]: {uv_index}, "
        f"Sääolosuhteet [WeatherAPI]: {condition_wapi}, "
        f"Kuu nousee klo (paikallista aikaa): {moonrise_time}, "
        f"Kuu laskee klo (paikallista aikaa): {moonset_time}, "
        f"Kuun valaistus: {moon_illumination}%, "
        f"Ennuste päivälle {forecast_date}: {forecast_condition}, Lämpötila: {forecast_temperature}°C, Tuuli: {forecast_wind} km/h, Sademäärä: {forecast_precipitation} mm, UV-indeksi: {forecast_uv_index}"
    )

    # Include additional WeatherAPI data (daily forecast, air quality, and alerts)
    if daily_forecast_data:
        air_quality_data = daily_forecast_data['air_quality']
        alerts = daily_forecast_data['alerts']

        air_quality_info = "\n(Ilmanlaatu: " + " / ".join(
            [f"{key}: {value}" for key, value in air_quality_data.items()]
        ) + ")"

        # air_quality_info = "\nIlmanlaatu:\n" + "\n".join(
        #     [f"{key}: {value}" for key, value in air_quality_data.items()]
        # )

        alerts_info = "\nSäävaroitukset:\n" + (
            "\n".join(
                [f"Alert: {alert['headline']}\nDescription: {alert['desc']}\nInstructions: {alert['instruction']}\n"
                 for alert in alerts['alert']]
            ) if 'alert' in alerts and alerts['alert'] else "No weather alerts according to OpenWeatherMap. NOTE: Please see other sources (i.e. NWS) to be sure."
        )

        detailed_weather_info += f"\n{air_quality_info}\n{alerts_info}"

    # 3-hour forecast details
    forecasts = forecast_data['list']
    formatted_forecasts = []
    
    for forecast_data in forecasts[:5]:  # Adjust the range as needed
        utc_time = dt.datetime.utcfromtimestamp(forecast_data['dt'])
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

    additional_info_to_add = (
        "NOTE: TRANSLATE AND FORMAT THIS DATA FOR THE USER AS APPROPRIATE. Use emojis where suitable to enhance the readability and engagement of the weather report. "
        "For example, use 🌞 for sunny, 🌧️ for rain, ⛅ for partly cloudy, etc and include a relevant and concise overview of what was asked."
    )

    combined_info = f"{detailed_weather_info}\n\n{final_forecast}"

    # Append NWS data (Forecasts)
    if nws_forecast:
        nws_forecast_info = ""
        nws_periods = nws_forecast.get('properties', {}).get('periods', [])
        if nws_periods:
            nws_forecast_info += "🌦️ <b>NWS Forecast (weather.gov):</b>\n"
            for period in nws_periods[:3]:  # Limit to next 3 periods
                name = period.get('name', 'N/A')
                temperature = period.get('temperature', 'N/A')
                temperature_unit = period.get('temperatureUnit', 'N/A')
                wind_speed = period.get('windSpeed', 'N/A')
                wind_direction = period.get('windDirection', 'N/A')
                short_forecast = period.get('shortForecast', 'N/A')
                nws_forecast_info += f"{name}: {short_forecast}, {temperature}°{temperature_unit}, Wind: {wind_speed} {wind_direction}\n"
        else:
            nws_forecast_info += "🌦️ <b>NWS Forecast (weather.gov):</b> Ei saatavilla.\n"

        if nws_forecast_hourly:
            nws_hourly_forecast_info = ""
            nws_hourly_periods = nws_forecast_hourly.get('properties', {}).get('periods', [])
            if nws_hourly_periods:
                nws_hourly_forecast_info += "⏰ <b>NWS Hourly Forecast:</b>\n"
                for period in nws_hourly_periods[:3]:  # Limit to next 3 hourly forecasts
                    start_time = period.get('startTime', 'N/A')
                    temperature = period.get('temperature', 'N/A')
                    temperature_unit = period.get('temperatureUnit', 'N/A')
                    wind_speed = period.get('windSpeed', 'N/A')
                    wind_direction = period.get('windDirection', 'N/A')
                    short_forecast = period.get('shortForecast', 'N/A')
                    nws_hourly_forecast_info += f"{start_time}: {short_forecast}, {temperature}°{temperature_unit}, Wind: {wind_speed} {wind_direction}\n"
            else:
                nws_hourly_forecast_info += "⏰ <b>NWS Hourly Forecast:</b> Ei saatavilla.\n"
        else:
            nws_hourly_forecast_info = "⏰ <b>NWS Hourly Forecast:</b> Ei saatavilla.\n"

        combined_info += f"\n{nws_forecast_info}\n{nws_hourly_forecast_info}"

    # Append NWS data (Forecasts) only for eligible countries
    if not NWS_ONLY_ELIGIBLE_COUNTRIES or resolved_country.upper() in NWS_ELIGIBLE_COUNTRIES:
        
        # Append NWS Forecasts
        if nws_forecast:
            nws_forecast_info = ""
            nws_periods = nws_forecast.get('properties', {}).get('periods', [])
            if nws_periods:
                nws_forecast_info += "🌦️ <b>NWS Forecast (weather.gov):</b>\n"
                for period in nws_periods[:3]:  # Limit to next 3 periods
                    name = period.get('name', 'N/A')
                    temperature = period.get('temperature', 'N/A')
                    temperature_unit = period.get('temperatureUnit', 'N/A')
                    wind_speed = period.get('windSpeed', 'N/A')
                    wind_direction = period.get('windDirection', 'N/A')
                    short_forecast = period.get('shortForecast', 'N/A')
                    nws_forecast_info += f"{name}: {short_forecast}, {temperature}°{temperature_unit}, Wind: {wind_speed} {wind_direction}\n"
            else:
                nws_forecast_info += "🌦️ <b>NWS Forecast (weather.gov):</b> Ei saatavilla.\n"

            if nws_forecast_hourly:
                nws_hourly_forecast_info = ""
                nws_hourly_periods = nws_forecast_hourly.get('properties', {}).get('periods', [])
                if nws_hourly_periods:
                    nws_hourly_forecast_info += "⏰ <b>NWS Hourly Forecast:</b>\n"
                    for period in nws_hourly_periods[:3]:  # Limit to next 3 hourly forecasts
                        start_time = period.get('startTime', 'N/A')
                        temperature = period.get('temperature', 'N/A')
                        temperature_unit = period.get('temperatureUnit', 'N/A')
                        wind_speed = period.get('windSpeed', 'N/A')
                        wind_direction = period.get('windDirection', 'N/A')
                        short_forecast = period.get('shortForecast', 'N/A')
                        nws_hourly_forecast_info += f"{start_time}: {short_forecast}, {temperature}°{temperature_unit}, Wind: {wind_speed} {wind_direction}\n"
                else:
                    nws_hourly_forecast_info += "⏰ <b>NWS Hourly Forecast:</b> Ei saatavilla.\n"
            else:
                nws_hourly_forecast_info = "⏰ <b>NWS Hourly Forecast:</b> Ei saatavilla.\n"

            combined_info += f"\n{nws_forecast_info}\n{nws_hourly_forecast_info}"

        # Fetch and append NWS Alerts
        try:
            # Round coordinates to 4 decimal places to comply with NWS API
            lat_rounded = round(lat, 4)
            lon_rounded = round(lon, 4)
            alerts_url = f"https://api.weather.gov/alerts/active?point={lat_rounded},{lon_rounded}"
            async with httpx.AsyncClient(follow_redirects=True) as client:
                alerts_response = await client.get(alerts_url, headers={'User-Agent': NWS_USER_AGENT})
                alerts_response.raise_for_status()
                alerts_data = alerts_response.json()
        except httpx.HTTPStatusError as e:
            logging.error(f"NWS Alerts HTTP error: {e.response.status_code} - {e.response.text}")
            alerts_data = None
        except Exception as e:
            logging.error(f"Error fetching NWS alerts: {e}")
            alerts_data = None

        alerts_info = ""
        if alerts_data and 'features' in alerts_data and alerts_data['features']:
            alerts_info += "[HUOM! HUOMIOI NÄMÄ! TAKE THESE INTO ACCOUNT!!! MENTION THESE TO THE USER IF THERE ARE WEATHER ALERTS -- INCLUDE ALL THE DETAILS. WHAT, WHEN, WHERE, WHAT SEVERITY, ETC.]\n🚨 <b>ONGOING ALERTS FROM THE U.S. NWS (weather.gov):</b>\n"
            for idx, alert in enumerate(alerts_data['features'], start=1):
                properties = alert.get('properties', {})
                
                event = properties.get('event', 'EVENT').upper()
                headline = properties.get('headline', 'HEADLINE')
                description = properties.get('description', 'No further details available')  # Fetching the detailed description            
                instruction = properties.get('instruction', 'INSTRUCTION')
                severity = properties.get('severity', 'Unknown').capitalize()
                certainty = properties.get('certainty', 'Unknown').capitalize()
                urgency = properties.get('urgency', 'Unknown').capitalize()
                area_desc = properties.get('areaDesc', 'N/A')
                effective = properties.get('effective', 'N/A')
                expires = properties.get('expires', 'N/A')
                
                alerts_info += (
                    f"{idx}. ⚠️ <b>{event}</b>\n"
                    f"<b>Vaara:</b> {headline}\n"
                    f"<b>Kuvaus:</b> {description}\n"  # Adding the detailed description                
                    f"<b>Ohjeet:</b> {instruction}\n"
                    f"<b>Alue:</b> {area_desc}\n"
                    f"<b>Vakavuus:</b> {severity}\n"
                    f"<b>Varmuus:</b> {certainty}\n"
                    f"<b>Kiireellisyys:</b> {urgency}\n"
                    f"<b>Voimassa alkaen:</b> {effective}\n"
                    f"<b>Päättyy:</b> {expires}\n\n"
                )
        else:
            alerts_info += "\n🚨 Ei aktiivisia varoituksia U.S. NWS:n (weather.gov) mukaan.\n"

        combined_info += alerts_info

    # Combine all information
    combined_info += f"\n{detailed_weather_info}\n\n{final_forecast}"

    # Append additional data for Finland if available
    if additional_data:
        combined_info += f"\n\n[ Lisätiedot Suomeen (lähde: foreca.fi -- MAINITSE LÄHDE) ]\n{additional_data}"
    
    # Append the additional info at the end
    combined_info += f"\n\n{additional_info_to_add}"
    
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
    
