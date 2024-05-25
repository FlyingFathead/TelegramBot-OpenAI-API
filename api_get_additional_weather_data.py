# api_get_additional_weather_data.py

import logging
import asyncio
import re

## NOTE: this is ONLY for example purposes!
async def get_additional_data_dump():
    try:
        # Execute the lynx command and capture the output
        command = 'lynx --dump -nolist https://www.foreca.fi/'
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if stderr:
            logging.error(f"Error in get_additional_data_dump: {stderr.decode()}")
            return "Error fetching data."

        output = stdout.decode()

        # Regular expressions to trim the output
        start_marker = r'Suomen sää juuri nyt'
        end_marker = r'Foreca YouTubessa'
        trimmed_output = re.search(rf'{start_marker}(.*?){end_marker}', output, re.DOTALL)

        # Return the trimmed output if markers are found
        if trimmed_output:
            debug_output = trimmed_output.group(1)

            # Parsing the specific weather forecast section
            parsed_forecast = parse_foreca_data(debug_output)

            # Format the parsed data for output
            formatted_forecast = f"{parsed_forecast}"

            # Print the output for debugging
            logging.info(formatted_forecast)

            return formatted_forecast
        else:
            return "Start or stop marker not found in the output."

    except Exception as e:
        # Handle errors (e.g., lynx not installed, network issues)
        logging.error(f"Exception in get_additional_data_dump: {e}")
        return str(e)
    
def parse_foreca_data(data):
    # Regular expressions to identify the start and end of the desired section
    start_marker = r'Sääennuste koko maahan'
    end_marker = r'Lähipäivien sää'

    # Extract the section
    forecast_section = re.search(rf'{start_marker}(.*?){end_marker}', data, re.DOTALL)
    if forecast_section:
        forecast_data = forecast_section.group(1).strip()
        # Further parsing can be done here to extract regional forecasts
        # Format the data for output
        return forecast_data
    else:
        return "Relevant weather forecast section not found."

# Example usage
# Assuming 'output' contains the lynx dump

# Example usage
if __name__ == "__main__":
    # Create an asyncio event loop
    loop = asyncio.get_event_loop()

    # Run the async function inside asyncio.run()
    result = loop.run_until_complete(get_additional_data_dump())
    
    # Print the result
    print(result)
