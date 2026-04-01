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

def create_features_alarms(df) -> pd.DataFrame:
    pass