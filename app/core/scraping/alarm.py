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
from app.core.features.alarms_features import explode_by_hour, get_correct_regions


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

    result = None
    i = 0
    while not result:
        i += 1
        try:
            response = requests.get(BASE_URL, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError) as e:
            print(f"Error fetching alarm status: {e}")
        time.sleep(2*i)
    print(f'Fetching alarm status: Successful after {i} retries.')
    return result

def _parse_dt(s: Optional[str]) -> Optional[dt.datetime]:
    if not s:
        return None
    s = s.rstrip("Z")
    if "." in s:
        base, frac = s.split(".", 1)
        frac = frac[:6]
        s = f"{base}.{frac}"
    datetime = dt.datetime.fromisoformat(s)
    return datetime

def _merge_intervals(group, group_name):
    group = group.sort_values('start')
    
    region = group_name
    region_id = group['region_id'].iloc[0]

    merged = []
    current_start = None
    current_end = None

    for _, row in group.iterrows():
        start, end = row['start'], row['end']
        
        if current_start is None:
            current_start, current_end = start, end
        else:
            # якщо поточний або новий інтервал ще не закінчився — об'єднуємо
            if pd.isna(current_end) or pd.isna(end):
                if start <= (current_end if pd.notna(current_end) else start):
                    current_end = pd.NaT  # незакритий інтервал поглинає все
                else:
                    merged.append((current_start, current_end))
                    current_start, current_end = start, end
            elif start <= current_end:
                current_end = max(current_end, end)
            else:
                merged.append((current_start, current_end))
                current_start, current_end = start, end
    
    if current_start is not None:
        merged.append((current_start, current_end))
    
    result = pd.DataFrame(merged, columns=['start', 'end'])
    result['region'] = region
    result['region_id'] = region_id

    return result

def merge_alarms(raw_alarms, correct_regions):
    rows = []

    for alarm in raw_alarms:
        region_data = correct_regions.get(alarm['regionId'])
        if region_data is None:
            print(f"Missing parent region for id {alarm['regionId']}")
            continue

        region_id, region = region_data

        start = _parse_dt(alarm['startDate'])
        end = _parse_dt(alarm['endDate'])

        # замінюємо "порожню" дату
        if end == pd.Timestamp('0001-01-01'):
            end = pd.NaT

        rows.append([region_id, region, start, end])

    alarms = pd.DataFrame(rows, columns=["region_id", "region", "start", "end"])

    alarms['start'] = pd.to_datetime(alarms['start']).dt.floor('min')
    alarms['end'] = pd.to_datetime(alarms['end']).dt.floor('min')

    result = (
        alarms.groupby('region')
        .apply(lambda g: _merge_intervals(g, g.name))
        .reset_index(drop=True)
    )

    return result

def get_alarms_history_by_hour(date) -> pd.DataFrame:
    history = get_alarms_history(date)
    merged_alarms = merge_alarms(history, correct_regions)
    exploded_alarms = explode_by_hour(merged_alarms, date=date)
    return exploded_alarms


if __name__ == "__main__":
    date = dt.date.today() - dt.timedelta(days=1)
    print(get_alarms_history_by_hour(date))