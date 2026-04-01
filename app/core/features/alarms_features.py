import pandas as pd
import datetime as dt
from typing import Optional
from pathlib import Path
import json
import pickle


def explode_by_hour(df, date: Optional[dt.date] = None) -> pd.DataFrame:
    df = df.copy()  # avoid mutating the original
    df = df.drop(columns=["hours"], errors="ignore")


    df["hours"] = df.apply(
        lambda row: pd.date_range(
            row["start"].floor("h"),
            row["end"].floor("h") if pd.notna(row["end"]) else pd.Timestamp.now().floor("h"),
            freq="h"
        ), 
        axis=1,
        result_type='reduce'
    )

    alarm_expanded = df[["region_id", "region", "hours", "start", "end"]].explode("hours")
    alarm_expanded = alarm_expanded.rename(columns={"hours": "time"})
    alarm_expanded["alarm"] = 1

    alarm_expanded["has_started"] = (
        alarm_expanded["time"] == alarm_expanded["start"].dt.floor("h")
    ).astype(int)

    alarm_expanded["has_ended"] = (
        pd.notna(alarm_expanded["end"]) &
        (alarm_expanded["time"] == alarm_expanded["end"].dt.floor("h"))
    ).astype(int)

    alarm_expanded = alarm_expanded.drop(columns=["start", "end"])
    if date:
        if isinstance(date, pd.Timestamp):
            date = date.date()
        alarm_expanded = alarm_expanded.loc[alarm_expanded["time"].dt.date == date]

    alarm_expanded = (
    alarm_expanded.groupby(['region_id', 'time'], as_index=False)
        .agg({
            'region': 'first',
            'alarm':  'first',
            'has_started': 'sum',
            'has_ended':   'sum',
        })
        .reset_index(drop=True)
    )

    alarm_expanded["time"] = alarm_expanded["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    
    return alarm_expanded

def get_correct_regions(path: Path = Path("data/alarms/regions_list.json")) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Region hierarchy file not found: {path}")
    with open(path, encoding="utf-8") as f:
        states = json.load(f)['states']

    correct_regions = dict()

    for state in states:
        region_id = state['regionId']
        region_name = state['regionName']
        if region_name.startswith("м. "):
            region_name = region_name[3:]
        else:
            region_name = region_name[:-4] + '.'

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

    correct_regions['564'] = ('12', "Запорізька обл.") # hardcoded fix
    correct_regions['1293'] = ('22', "Харківська обл.") # hardcoded fix

    return correct_regions

def fix_regions(df, regions_path: Path = Path('data/alarms/regions_fixed.pkl')) -> pd.DataFrame:
    if not regions_path.exists():
        correct_regions = get_correct_regions()
        regions = {name: id for id, name in (correct_regions.values())}
        with open(regions_path, 'wb') as f:
            pickle.dump(regions, f)
    else:
        with open(regions_path, 'rb') as f:
            regions = pickle.load(f)

    if 'region_city' in df.columns:
        df['region'] = df['region_city']
        df = df.drop(columns=['region_city', 'region_title'], errors='ignore')

    df['region_id'] = df['region'].apply(lambda x: regions.get(x))
    return df

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

def create_features_alarms(df) -> pd.DataFrame:
    pass