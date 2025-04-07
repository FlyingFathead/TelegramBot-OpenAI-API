# timedate_handler.py
import datetime
import pytz

# Maps English day names from strftime() -> Finnish
fi_days = {
    "Monday": "maanantai",
    "Tuesday": "tiistai",
    "Wednesday": "keskiviikko",
    "Thursday": "torstai",
    "Friday": "perjantai",
    "Saturday": "lauantai",
    "Sunday": "sunnuntai"
}

# Maps English month names -> Finnish “month in the partitive case” for typical date usage
fi_months = {
    "January": "tammikuuta",
    "February": "helmikuuta",
    "March": "maaliskuuta",
    "April": "huhtikuuta",
    "May": "toukokuuta",
    "June": "kesäkuuta",
    "July": "heinäkuuta",
    "August": "elokuuta",
    "September": "syyskuuta",
    "October": "lokakuuta",
    "November": "marraskuuta",
    "December": "joulukuuta"
}

def get_ordinal_suffix(day_num: int) -> str:
    """
    Returns the English ordinal suffix for a given day of the month, e.g. 
    1->"1st", 2->"2nd", 3->"3rd", 4->"4th", etc.
    """
    if 11 <= (day_num % 100) <= 13:
        return "th"
    elif day_num % 10 == 1:
        return "st"
    elif day_num % 10 == 2:
        return "nd"
    elif day_num % 10 == 3:
        return "rd"
    else:
        return "th"

def get_english_timestamp_str(now_utc: datetime.datetime) -> str:
    """
    Returns an English-formatted date/time string, e.g.:
    'Monday, April 9th, 2025 | Time (UTC): 12:34:56'
    """
    day_of_week_eng = now_utc.strftime("%A")    # e.g. "Monday"
    month_name_eng  = now_utc.strftime("%B")    # e.g. "April"
    day_num         = int(now_utc.strftime("%d"))
    year_str        = now_utc.strftime("%Y")
    suffix          = get_ordinal_suffix(day_num)
    date_str        = f"{month_name_eng} {day_num}{suffix}, {year_str}"
    time_str        = now_utc.strftime("%H:%M:%S")  # "12:34:56"
    
    return f"{day_of_week_eng}, {date_str} | Time (UTC): {time_str}"

def get_finnish_timestamp_str(now_utc: datetime.datetime) -> str:
    """
    Returns a Finnish-formatted date/time string. For example:
    'maanantai, 9. huhtikuuta 2025, klo 15:34:56 Suomen aikaa'
    
    (Adjust as you like for Finnish grammar.)
    """
    helsinki_tz = pytz.timezone("Europe/Helsinki")
    now_fin = now_utc.astimezone(helsinki_tz)

    weekday_eng = now_fin.strftime("%A")        # e.g. "Monday"
    day_of_week_fi = fi_days.get(weekday_eng, weekday_eng)

    month_eng  = now_fin.strftime("%B")         # e.g. "April"
    month_fi   = fi_months.get(month_eng, month_eng)

    day_num    = int(now_fin.strftime("%d"))    # e.g. 9
    year_str   = now_fin.strftime("%Y")         # e.g. "2025"

    # For Finnish style we might do e.g. "9. huhtikuuta 2025"
    date_str_fi = f"{day_num}. {month_fi} {year_str}"

    time_str_fi = now_fin.strftime("%H:%M:%S")  # "15:34:56"
    # For instance: "maanantai, 9. huhtikuuta 2025, klo 15:34:56 Suomen aikaa"
    return f"{day_of_week_fi}, {date_str_fi}, klo {time_str_fi} Suomen aikaa"
