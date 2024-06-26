# api_get_weatherapi.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# >>> weather fetcher module version: v0.708
# >>> (Updated May 25 2024)
#
# This API functionality requires WeatherAPI key.
# You can get the API key from the corresponding service provider.
# Once you have the API key, add it to your environment variables:
# export WEATHERAPI_KEY="<your API key>"
# (or on i.e. Linux, add to your `~/.bashrc`: export WEATHERAPI_KEY="<your API key>" )
#
# (Updated May 25, 2024)

import httpx
import os
import logging

# Function to check for WeatherAPI key
def get_weatherapi_key():
    api_key = os.getenv('WEATHERAPI_KEY')
    if not api_key:
        logging.error("[WARNING] WeatherAPI key not set. You need to set the 'WEATHERAPI_KEY' environment variable to use WeatherAPI functionalities!")
        return None
    return api_key

# Dictionary to translate moon phases from English to Finnish
moon_phase_translation = {
    "New Moon": "uusikuu",
    "Waxing Crescent": "kasvava sirppi",
    "First Quarter": "ensimmäinen neljännes",
    "Waxing Gibbous": "kasvava puolikuu",
    "Full Moon": "täysikuu",
    "Waning Gibbous": "vähenevä puolikuu",
    "Last Quarter": "viimeinen neljännes",
    "Waning Crescent": "vähenevä sirppi"
}

# get moon phase data
async def get_moon_phase(lat, lon):
    api_key = get_weatherapi_key()
    if not api_key:
        return None

    logging.info(f"Fetching moon phase data for coordinates: Latitude: {lat}, Longitude: {lon}")
    base_url = 'http://api.weatherapi.com/v1/astronomy.json'
    url = f"{base_url}?key={api_key}&q={lat},{lon}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        logging.info(f"Moon phase response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logging.info(f"Moon phase data: {data}")
            moon_phase = data['astronomy']['astro']['moon_phase']
            translated_moon_phase = moon_phase_translation.get(moon_phase, moon_phase)
            return translated_moon_phase
        else:
            logging.error(f"Failed to fetch moon phase data: {response.text}")
            return None

# get timezone for the coordinates
async def get_timezone(lat, lon):
    api_key = get_weatherapi_key()
    if not api_key:
        return None

    logging.info(f"Fetching timezone data for coordinates: Latitude: {lat}, Longitude: {lon}")
    base_url = 'http://api.weatherapi.com/v1/timezone.json'
    url = f"{base_url}?key={api_key}&q={lat},{lon}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        logging.info(f"Timezone response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logging.info(f"Timezone data: {data}")
            timezone = data['location']['tz_id']
            return timezone
        else:
            logging.error(f"Failed to fetch timezone data: {response.text}")
            return None

# get daily forecast, safety alerts, and air quality index
async def get_daily_forecast(location):
    api_key = get_weatherapi_key()
    if not api_key:
        return None

    logging.info(f"Fetching daily forecast data for location: {location}")
    base_url = 'http://api.weatherapi.com/v1/forecast.json'
    url = f"{base_url}?key={api_key}&q={location}&days=1&alerts=yes&aqi=yes"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        logging.info(f"Daily forecast response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logging.info(f"Daily forecast data: {data}")
            forecast = data['forecast']['forecastday'][0]
            current = data['current']
            alerts = data.get('alerts', {})
            air_quality = current['air_quality']
            
            return {
                'date': forecast['date'],
                'temperature': forecast['day']['avgtemp_c'],
                'condition': forecast['day']['condition']['text'],
                'wind': forecast['day']['maxwind_kph'],
                'precipitation': forecast['day']['totalprecip_mm'],
                'uv_index': forecast['day']['uv'],
                'air_quality': air_quality,
                'alerts': alerts
            }
        else:
            logging.error(f"Failed to fetch daily forecast data: {response.text}")
            return None

# get current weather including UV index
async def get_current_weather_via_weatherapi(location):
    api_key = get_weatherapi_key()
    if not api_key:
        return None

    logging.info(f"Fetching current weather data for location: {location}")
    base_url = 'http://api.weatherapi.com/v1/current.json'
    url = f"{base_url}?key={api_key}&q={location}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        logging.info(f"Current weather response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logging.info(f"Current weather data: {data}")
            current = data['current']
            
            return {
                'temperature': current['temp_c'],
                'condition': current['condition']['text'],
                'wind': current['wind_kph'],
                'precipitation': current['precip_mm'],
                'uv_index': current['uv'],
                'visibility': current['vis_km'],  # Added visibility data
                'air_quality': current.get('air_quality', {})
            }
        else:
            logging.error(f"Failed to fetch current weather data: {response.text}")
            return None

# get astronomy data including moonrise, moonset, and moon illumination
async def get_astronomy_data(lat, lon):
    api_key = get_weatherapi_key()
    if not api_key:
        return None

    logging.info(f"Fetching astronomy data for coordinates: Latitude: {lat}, Longitude: {lon}")
    base_url = 'http://api.weatherapi.com/v1/astronomy.json'
    url = f"{base_url}?key={api_key}&q={lat},{lon}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        logging.info(f"Astronomy response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logging.info(f"Astronomy data: {data}")
            astro = data['astronomy']['astro']
            moonrise = astro['moonrise']
            moonset = astro['moonset']
            moon_illumination = astro['moon_illumination']
            return {
                'moonrise': moonrise,
                'moonset': moonset,
                'moon_illumination': moon_illumination
            }
        else:
            logging.error(f"Failed to fetch astronomy data: {response.text}")
            return None

# Additional WeatherAPI-related functions can be added here
