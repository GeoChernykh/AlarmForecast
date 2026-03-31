import datetime as dt
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
import os
import json
from typing import Optional
import requests

from app.errors import InvalidUsage


load_dotenv()

ALARM_API_KEY = os.getenv("ALARM_API_KEY")

alarms_path = Path("data/alarms")


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

def region_hierarchy(path: Path = alarms_path / "regions_list.json") -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Region hierarchy file not found: {path}")
    with open(path, encoding="utf-8") as f:
        states = json.load(f)['states']

    correct_regions = dict()

    correct_regions['564'] = ('12', "Запорізька область") # hardcoded fix
    correct_regions['1293'] = ('22', "Харківська область") # hardcoded fix

    for state in states:
        region_id = state['regionId']
        region_name = state['regionName']

        # filter test region and crimea
        if region_id == '0' or region_id == '9999':
            continue
        
        child_ids = set()

        for district in state['regionChildIds']:
            child_ids.add(district['regionId'])

            for community in district['regionChildIds']:
                child_ids.add(community['regionId'])

        for id in child_ids:
            correct_regions[id] = (region_id, region_name)

    
    return correct_regions

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

def merge_alarms(raw_alarms, correct_regions):
    alarms = pd.DataFrame(columns=["region_id", "region_title", "region_city", "start", "end"])

    for alarm in raw_alarms:
        region_data = correct_regions.get(alarm['regionId'])
        if region_data is None:
            print(f"Missing parent region for id {alarm['regionId']}")
            continue

        region_id, region_name = region_data
        if region_name == 'Київ':
            region_title = 'Київська область'
            region_city = 'Київ'
        else:
            region_title = region_name
            region_city = region_name[:-4] + '.'

        start = _parse_dt(alarm['startDate'])
        end = _parse_dt(alarm['endDate'])

        row = [region_id, region_title, region_city, start, end]
        
        alarms.loc[len(alarms)] = row

    alarms['start'] = pd.to_datetime(alarms['start'])
    alarms['end'] = pd.to_datetime(alarms['end'])

    alarms.loc[alarms.end == pd.to_datetime('0001-01-01 00:00:00.000000'), "end"] = None

    # сортування
    alarms = alarms.sort_values(['region_city', 'start'])

    # попередній кінець в межах міста
    alarms['prev_end'] = alarms.groupby('region_city')['end'].shift()

    # новий інтервал, якщо немає перекриття
    alarms['new_group'] = (alarms['start'] > alarms['prev_end']).astype(int)

    # унікальний id інтервалу
    alarms['interval_id'] = alarms.groupby('region_city')['new_group'].cumsum()

    # агрегуємо
    alarms = (
        alarms.groupby(['region_city', 'interval_id'], as_index=False)
        .agg({
            'region_id': 'first',
            'region_title': 'first',
            'start': 'min',
            'end': 'max'
        })
        .drop(columns='interval_id')
    )

    alarms['start'] = alarms['start'].dt.tz_localize('UTC').dt.tz_convert('Europe/Kyiv')
    alarms['end'] = alarms['end'].dt.tz_localize('UTC').dt.tz_convert('Europe/Kyiv')

    return alarms

# if __name__ == "__main__":
#     d = region_hierarchy()
#     print(merge_alarms(get_alarms_history(dt.date.today()), d))