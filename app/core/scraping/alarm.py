import datetime as dt
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
import os
import json
from typing import Optional
import requests
import time

from app.errors import InvalidUsage
from app.core.features.alarms_features import explode_by_hour, get_correct_regions, merge_alarms


load_dotenv()

ALARM_API_KEY = os.getenv("ALARM_API_KEY")

alarms_path = Path("data/alarms")

correct_regions = get_correct_regions()

def get_alarm_status():
    """Fetch raw alarm data from Ukraine Alarm API.

    Returns a list of alerts if successful, or an empty list if request fails
    or response is not valid JSON.
    """
    BASE_URL = "https://api.ukrainealarm.com/api/v3/alerts"

    headers = {
        "Authorization": f"{ALARM_API_KEY}",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    try:
        response = requests.get(BASE_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return []
    

def get_alarms_history(date: dt.date):
    BASE_URL = f"https://api.ukrainealarm.com/api/v3/alerts/dateHistory?date={date.strftime('%Y%m%d')}"

    if not ALARM_API_KEY:
        raise InvalidUsage("ALARM_API_KEY environment variable is not set")

    headers = {
        "Authorization": f"{ALARM_API_KEY}",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    i = 0
    while True:
        i += 1
        try:
            response = requests.get(BASE_URL, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            break
        except (requests.RequestException, ValueError) as e:
            print(f"Error fetching alarm status: {e}")
        time.sleep(2*i)
    print(f'Fetching alarm status: Successful after {i} retries.')
    return result

def get_alarms_history_by_hour(date) -> pd.DataFrame:
    history = get_alarms_history(date)
    
    if not history:
        return pd.DataFrame()

    merged_alarms = merge_alarms(history, correct_regions)
    exploded_alarms = explode_by_hour(merged_alarms, date=date)
    return exploded_alarms


if __name__ == "__main__":
    date = dt.date.today() - dt.timedelta(days=1)
    print(get_alarms_history_by_hour(date))