# api_get_nws.py
#
# > get the weather using the NWS (National Weather Service, US) API
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import asyncio
import httpx
import logging
from config_paths import NWS_USER_AGENT, NWS_RETRIES, NWS_RETRY_DELAY, FETCH_NWS_FORECAST, FETCH_NWS_ALERTS

# Base URL for NWS API
NWS_BASE_URL = 'https://api.weather.gov'

async def get_nws_forecast(lat, lon, retries=NWS_RETRIES, delay=NWS_RETRY_DELAY):
    """
    Fetches the forecast from the NWS API for the given latitude and longitude.
    
    Args:
        lat (float): Latitude in decimal degrees.
        lon (float): Longitude in decimal degrees.
        retries (int): Number of retries for transient errors. Defaults to RETRIES.
        delay (int): Delay between retries in seconds.
    
    Returns:
        dict: Combined forecast data or None if fetching fails.
    """

    if not FETCH_NWS_FORECAST:
        logging.info("Fetching NWS forecast is disabled in the config.")
        return None

    # Round coordinates to 4 decimal places
    lat = round(lat, 4)
    lon = round(lon, 4)
    points_url = f"{NWS_BASE_URL}/points/{lat},{lon}"
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for attempt in range(retries + 1):  # Ensure at least one attempt is made
            try:
                # Step 1: Retrieve metadata for the location
                response = await client.get(points_url, headers={'User-Agent': NWS_USER_AGENT})
                response.raise_for_status()
                points_data = response.json()
                
                # Extract forecast URLs
                forecast_url = points_data['properties']['forecast']
                forecast_hourly_url = points_data['properties'].get('forecastHourly')
                
                # Step 2: Retrieve forecast data
                forecast_response = await client.get(forecast_url, headers={'User-Agent': NWS_USER_AGENT})
                forecast_response.raise_for_status()
                forecast_data = forecast_response.json()
                
                # Step 3: Retrieve hourly forecast data
                forecast_hourly_data = None
                if forecast_hourly_url:
                    try:
                        forecast_hourly_response = await client.get(forecast_hourly_url, headers={'User-Agent': NWS_USER_AGENT})
                        forecast_hourly_response.raise_for_status()
                        forecast_hourly_data = forecast_hourly_response.json()
                    except httpx.HTTPStatusError as e:
                        logging.error(f"NWS Hourly Forecast HTTP error: {e.response.status_code} - {e.response.text}")
                
                return {
                    'nws_forecast': forecast_data,
                    'nws_forecast_hourly': forecast_hourly_data
                }
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < retries:
                    logging.warning(f"NWS API HTTP error: {e.response.status_code} - {e.response.text}. Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logging.error(f"NWS API HTTP error: {e.response.status_code} - {e.response.text}")
                    break
            except Exception as e:
                logging.error(f"Error fetching NWS forecast: {e}")
                break
        
    return None

async def get_nws_alerts(lat, lon):
    """
    Fetches active alerts from the NWS API for the given latitude and longitude.
    
    Args:
        lat (float): Latitude in decimal degrees.
        lon (float): Longitude in decimal degrees.
    
    Returns:
        list: A list of active alerts or an empty list if none are found.
    """

    if not FETCH_NWS_ALERTS:
        logging.info("Fetching NWS alerts is disabled in the config.")
        return []

    alerts_url = f"{NWS_BASE_URL}/alerts/active?point={lat},{lon}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(alerts_url, headers={'User-Agent': NWS_USER_AGENT})
            response.raise_for_status()
            alerts_data = response.json()
            
            # Extract alerts from GeoJSON
            alerts = alerts_data.get('features', [])
            return alerts
        
        except httpx.HTTPStatusError as e:
            logging.error(f"NWS Alerts API HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logging.error(f"Error fetching NWS alerts: {e}")
    
    return []
