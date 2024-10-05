# api_get_global_time.py

import subprocess

TIMEZONES = [
    "UTC", "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Helsinki", "Asia/Tokyo",
    "Asia/Shanghai", "Australia/Sydney", "Asia/Kolkata", "America/Sao_Paulo"
]

def get_time_for_timezone(timezone):
    try:
        command = f"TZ={timezone} date +'%Y-%m-%d %H:%M:%S %Z'"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            return f"Failed to fetch time for timezone {timezone}: {result.stderr.strip()}"
        
        return result.stdout.strip()
    except Exception as e:
        return f"Error executing date command for timezone {timezone}: {str(e)}"

async def get_global_time():
    times = {}
    for timezone in TIMEZONES:
        times[timezone] = get_time_for_timezone(timezone)
    return times