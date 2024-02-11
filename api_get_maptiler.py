# api_get_maptiler.py

import logging
import httpx
import os

# the function below can be implemented to use for POI lookups
async def get_location_from_coordinates(latitude, longitude):
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

# this function can look up coordinates from a given address
async def get_coordinates_from_address(address):
    logging.info(f"Fetching coordinates for address: {address}")    
    # Retrieve MapTiler API key from environment variables
    api_key = os.getenv('MAPTILER_API_KEY')
    if not api_key:
        logging.error("[ERROR] MapTiler API key not set. You need to set the 'MAPTILER_API_KEY' environment variable for this function to work!")        
        return "MapTiler API key not set."

    # Construct the API request URL for geocoding
    geocode_url = f"https://api.maptiler.com/geocoding/{address}.json?key={api_key}"
    logging.info(f"Making API request to URL: {geocode_url}")    

    async with httpx.AsyncClient() as client:
        response = await client.get(geocode_url)
        logging.info(f"Received response with status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            logging.info(f"Response data: {data}")            
            # Assuming the first feature is the most relevant match
            if data['features']:
                first_feature = data['features'][0]
                coordinates = first_feature['geometry']['coordinates']
                # Coordinates are returned as [longitude, latitude]
                return {'longitude': coordinates[0], 'latitude': coordinates[1]}
            else:
                logging.info("No features found for the provided address.")
                return "No location found for the provided address."
        else:
            logging.error(f"Failed to fetch coordinates: {response.text}")            
            return "Failed to fetch coordinates."

# get a map image (for maptiler's paid plan only)
async def get_static_map_image(latitude, longitude, zoom, width, height, mapId='streets'):
    api_key = os.getenv('MAPTILER_API_KEY')
    if not api_key:
        logging.error("[ERROR] MapTiler API key not set.")
        return "MapTiler API key not set."

    scale = '@2x'  # For HiDPI/Retina maps
    format = 'png'  # Output format
    url = f"https://api.maptiler.com/maps/{mapId}/static/{longitude},{latitude},{zoom}/{width}x{height}{scale}.{format}?key={api_key}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            # Save the image to a file for debugging
            with open('map_image.png', 'wb') as f:
                f.write(response.content)
            logging.info("Static map image saved successfully.")
            return response.content  # Returns the image data
        else:
            logging.error(f"Failed to generate static map: Status code {response.status_code}")
            return None
