import pandas as pd
import datetime as dt
from typing import Optional


def explode_by_hour(df, date: Optional[dt.date] = None) -> pd.DataFrame:
    df = df.copy()  # avoid mutating the original
    # df = df.drop(columns=["hours"], errors="ignore")

    df["hours"] = df.apply(
        lambda row: list(pd.date_range(
            row["start"].floor("h"),
            row["end"].floor("h") if pd.notna(row["end"]) else pd.Timestamp.now().floor("h"),
            freq="h"
        )), 
        axis=1
    )

    alarm_expanded = df[["region_id", "hours", "start", "end"]].explode("hours")
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
        alarm_expanded = alarm_expanded.loc[alarm_expanded["time"].dt.date == date]
    
    return alarm_expanded

def create_features_alarms(df) -> pd.DataFrame:
    pass