# api_get_time.py
# for fetching time according to coordinates; placeholder/WIP

from timezonefinder import TimezoneFinder
from datetime import datetime
import pytz
import httpx  # For making requests to a geocoding API

def get_coordinates_for_location(location_name: str) -> tuple:

    # etches the latitude and longitude for a given location name.
    # This function uses a geocoding API to convert location names to coordinates.
    # Replace 'Your_API_Key_Here' with your actual API key for the geocoding service.

    api_url = f"https://api.opencagedata.com/geocode/v1/json?q={location_name}&key=Your_API_Key_Here"
    try:
        response = httpx.get(api_url)
        data = response.json()
        # Extracting the first result as an example. You might want to refine this for accuracy.
        coordinates = data['results'][0]['geometry']
        return coordinates['lat'], coordinates['lng']
    except Exception as e:
        print(f"Error fetching coordinates for location '{location_name}': {e}")
        return None, None

# Determines the local time for a given location name.
def get_local_time_for_location(location_name: str) -> str:
    
    lat, lng = get_coordinates_for_location(location_name)
    if lat is None or lng is None:
        return "Could not determine the coordinates for the location."

    # Find the time zone for the given coordinates
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=lat, lng=lng)
    if timezone_str is None:
        return "Could not determine the time zone for the location."

    # Get the current time in the determined time zone
    timezone = pytz.timezone(timezone_str)
    local_time = datetime.now(timezone)
    return local_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')