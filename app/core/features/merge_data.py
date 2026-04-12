import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import OrdinalEncoder
from app.core.features.weather_features import add_region_ids
from app.core.features.isw_features import create_features_isw
from app.core.features.alarms_features import add_neighbor_alarm_count


encoder = joblib.load("app/models/preprocessing/merged_df_encoder.joblib")
region_ids = pd.read_csv("data/alarms/regions.csv")["region_id"].tolist()

def merge_all_data(alarms, weather, isw, telegram, region_ids=region_ids, encoder=encoder) -> pd.DataFrame:
    assert not (alarms.empty or weather.empty or isw.empty or telegram.empty)

    alarms['time'] = pd.to_datetime(alarms['time']).dt.tz_localize("Europe/Kyiv", ambiguous="NaT", nonexistent="shift_forward")
    
    timeline = pd.date_range(alarms['time'].min(), pd.Timestamp.now(tz="Europe/Kyiv"), freq="h")
    
    spine = pd.MultiIndex.from_product([region_ids, timeline], names=["region_id", "time"]) \
                .to_frame(index=False) \
                .sort_values(["region_id", "time"]) \
                .reset_index(drop=True)
                
    df = spine.merge(alarms, on=["region_id", "time"], how="left")
    df["alarm"] = df["alarm"].fillna(0).astype(int)
    assert not df.empty, "alarms merged"

    weather["preciptype"] = weather["preciptype"].fillna("None")
        
    weather = add_region_ids(weather)
    
    weather["time"] = pd.to_datetime(weather.pop("real_hour_datetime")).dt.tz_localize("Europe/Kyiv", ambiguous="NaT", nonexistent="shift_forward")

    df = df.merge(weather, on=["region_id", "time"], how="left")

    tg_df = telegram.copy()
    if 'datetime' in tg_df.columns:
        tg_df.rename({"datetime": "time"}, axis=1, inplace=True)
        
    tg_df['time'] = pd.to_datetime(tg_df['time'], utc=True) \
                    .dt.tz_convert("Europe/Kyiv") \
                    .dt.floor("h", ambiguous="infer")
    tg_df = tg_df.drop_duplicates(subset="time")
    
    df = df.merge(tg_df, on=["time"], how="left")

    if 'text' in list(isw.columns):
        isw = create_features_isw(isw)
        
    isw['date'] = pd.to_datetime(isw['date'])
    
    df["date"] = df["time"].dt.date
    df["date"] = pd.to_datetime(df["date"])
    
    df = df.merge(isw, on="date", how="left")
    df = df.drop(columns=["date"])
    df = df.drop(["city", "region"], axis=1, errors="ignore")
            
    # preprocessing

    df = df.sort_values(['region_id', 'time'])

    all_alarms = df.groupby("time")["alarm"].sum().rename("num_alarms").reset_index()

    df = pd.merge(df, all_alarms, on="time", how="left")
    # df["other_alarms_count"] = df["num_alarms"] - df["alarm"]
    for i in range(24):
        df[f"alarms_count_{i+1}h_ago"] = df["num_alarms"].shift(i+1)

    for i in range(24):
        df[f"alarm_status_{i+1}h_ago"] = df.groupby("region_id")["alarm"].shift(i+1)

    df = df.drop(columns="num_alarms")
    
    df = add_neighbor_alarm_count(df)
    df['neighbor_alarm_count'] = df.groupby("region_id")['neighbor_alarm_count'].shift(1)

    df["text_length"] = df["text_length"].fillna(0)
    df["preciptype"] = df["preciptype"].fillna("None")
            
    isw_cluster_cols = [col for col in df.columns if col.startswith("isw_cluster")]
    df[isw_cluster_cols] = df[isw_cluster_cols].fillna(0)
        
    df["visibility"] = df.groupby('region_id')["visibility"].ffill()
    df["uvindex"] = df.groupby("region_id")["uvindex"].ffill()
    df['temp'] = df.groupby('region_id')['temp'].ffill(limit=12)
        
    df['messages_count'] = df['messages_count'].fillna(0)

    # df["year"] = df["time"].dt.year
    # df["month"] = df["time"].dt.month
    # df["day"] = df["time"].dt.day 
    df["hour"] = df["time"].dt.hour
    df['day_of_week'] = df['time'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

    cat_cols = ['preciptype', 'conditions']
    df[cat_cols] = encoder.transform(df[cat_cols])

    df = df.loc[~df.temp.isna()]
    df = df.loc[~df.time.isna()]
    df = df.dropna(axis=0).reset_index(drop=True)
    assert not df.empty

    return df