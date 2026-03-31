import datetime as dt
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
import os
import json
from typing import Optional
import requests

from app.errors import InvalidUsage
from app.core.features.alarms_features import explode_by_hour


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

def get_correct_regions(path: Path = alarms_path / "regions_list.json") -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Region hierarchy file not found: {path}")
    with open(path, encoding="utf-8") as f:
        states = json.load(f)['states']

    correct_regions = dict()

    

    for state in states:
        region_id = state['regionId']
        region_name = state['regionName']

        # filter test region and crimea
        if region_id == '0' or region_id == '9999':
            continue
        
        child_ids = {region_id}

        for district in state['regionChildIds']:
            child_ids.add(district['regionId'])

            for community in district['regionChildIds']:
                child_ids.add(community['regionId'])

        for id in child_ids:
            correct_regions[id] = (region_id, region_name)

    correct_regions['564'] = ('12', "Запорізька область") # hardcoded fix
    correct_regions['1293'] = ('22', "Харківська область") # hardcoded fix

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

def _merge_intervals(group, group_name):
    group = group.sort_values('start')
    
    region_city = group_name
    region_id = group['region_id'].iloc[0]
    region_title = group['region_title'].iloc[0]

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
    result['region_city'] = region_city
    result['region_id'] = region_id
    result['region_title'] = region_title

    return result

def merge_alarms(raw_alarms, correct_regions):
    rows = []

    for alarm in raw_alarms:
        region_data = correct_regions.get(alarm['regionId'])
        if region_data is None:
            print(f"Missing parent region for id {alarm['regionId']}")
            continue

        region_id, region_name = region_data

        if region_name == 'м. Київ':
            region_title = 'Київська область'
            region_city = 'Київ'
        else:
            region_title = region_name
            region_city = region_name[:-4] + '.'

        start = _parse_dt(alarm['startDate'])
        end = _parse_dt(alarm['endDate'])

        # замінюємо "порожню" дату
        if end == pd.Timestamp('0001-01-01'):
            end = pd.NaT

        rows.append([region_id, region_title, region_city, start, end])

    alarms = pd.DataFrame(rows, columns=[
        "region_id", "region_title", "region_city", "start", "end"
    ])

    alarms['start'] = pd.to_datetime(alarms['start']).dt.floor('min')
    alarms['end'] = pd.to_datetime(alarms['end']).dt.floor('min')

    # застосування по region_city
    result = (
        alarms.groupby('region_city')
        .apply(lambda g: _merge_intervals(g, g.name))
        .reset_index(drop=True)
    )

    return result

def get_alarms_history_by_hour(date) -> pd.DataFrame:
    correct_regions = get_correct_regions()
    history = get_alarms_history(date)
    merged_alarms = merge_alarms(history, correct_regions)
    exploded_alarms = explode_by_hour(merged_alarms, date=date)
    return exploded_alarms


if __name__ == "__main__":
    date = dt.date.today() - dt.timedelta(days=1)
    print(get_alarms_history_by_hour(date))