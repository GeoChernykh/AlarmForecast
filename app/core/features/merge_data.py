import pandas as pd
import numpy as np
from sklearn.preprocessing import OrdinalEncoder
from app.core.features.weather_features import add_region_ids
from app.core.features.isw_features import create_features_isw

def merge_all_data(alarms, weather, isw_raw, telegram) -> pd.DataFrame:
    alarms['time'] = pd.to_datetime(alarms['time'], utc=True).dt.tz_convert("Europe/Kyiv")
    
    timeline = pd.date_range(alarms['time'].min(), alarms['time'].max(), freq="h")
    region_ids = alarms['region_id'].unique()
    spine = pd.MultiIndex.from_product([region_ids, timeline], names=["region_id", "time"]) \
                .to_frame(index=False) \
                .sort_values(["region_id", "time"]) \
                .reset_index(drop=True)
                
    merged_df = spine.merge(alarms, on=["region_id", "time"], how="left")
    merged_df["alarm"] = merged_df["alarm"].fillna(0).astype(int)

    weather_df = weather.copy()
    if 'preciptype' in weather_df.columns:
        weather_df["preciptype"] = weather_df["preciptype"].fillna("None")
        
    weather_df = add_region_ids(weather_df)
    
    if "real_hour_datetime" in weather_df.columns:
        weather_df["time"] = pd.to_datetime(weather_df.pop("real_hour_datetime"))
    else:
        weather_df["time"] = pd.to_datetime(weather_df["time"])
        
    if weather_df['time'].dt.tz is None:
        weather_df['time'] = weather_df['time'].dt.tz_localize("Europe/Kyiv", ambiguous="infer")
    else:
        weather_df['time'] = weather_df['time'].dt.tz_convert("Europe/Kyiv")

    merged_df = merged_df.merge(weather_df, on=["region_id", "time"], how="left")

    tg_df = telegram.copy()
    if 'datetime' in tg_df.columns:
        tg_df.rename({"datetime": "time"}, axis=1, inplace=True)
        
    tg_df['time'] = pd.to_datetime(tg_df['time'], utc=True) \
                    .dt.tz_convert("Europe/Kyiv") \
                    .dt.floor("h", ambiguous="infer")
    tg_df = tg_df.drop_duplicates(subset="time")
    
    merged_df = merged_df.merge(tg_df, on=["time"], how="left")

    isw = create_features_isw(isw_raw)
    isw['date'] = pd.to_datetime(isw['date'])
    
    merged_df["date"] = merged_df["time"].dt.date
    merged_df["date"] = pd.to_datetime(merged_df["date"])
    
    merged_df = merged_df.merge(isw, on="date", how="left")
    merged_df = merged_df.drop(columns=["date"])

    df = merged_df.copy()
    df = df.loc[~df.time.isna()]
    df = df.drop(["city", "region"], axis=1, errors="ignore")
    
    temp_col = 'hour_temp' if 'hour_temp' in df.columns else 'temp'
    if temp_col in df.columns:
        df = df.loc[~df[temp_col].isna()]
        
    if "text_length" in df.columns:
        df["text_length"] = df["text_length"].fillna(-1)
        
    if "preciptype" in df.columns:
        df["preciptype"] = df["preciptype"].fillna("None")
        
    df = df.fillna({"has_started": 0, "has_ended": 0})
    
    isw_cluster_cols = [col for col in df.columns if col.startswith("isw_cluster")]
    if isw_cluster_cols:
        df[isw_cluster_cols] = df[isw_cluster_cols].fillna(0)
        
    vis_col = "hour_visibility" if "hour_visibility" in df.columns else "visibility"
    if vis_col in df.columns:
        df[vis_col] = df[vis_col].ffill()
        
    uv_col = "hour_uvindex" if "hour_uvindex" in df.columns else "uvindex"
    if uv_col in df.columns:
        df[uv_col] = df[uv_col].ffill()
        
    if "messages_count" in df.columns:
        df = df.loc[~df["messages_count"].isna()]

    df["year"] = df["time"].dt.year
    df["month"] = df["time"].dt.month
    df["day"] = df["time"].dt.day
    
    df = df.dropna(axis=0)
    df = df.reset_index(drop=True)

    encoder = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
    cat_cols = list(df.select_dtypes(include=["object", "category"]).columns)
    if cat_cols:
        df[cat_cols] = encoder.fit_transform(df[cat_cols])

    all_alarms = df.groupby("time")["alarm"].sum().rename("num_alarms").reset_index()
    df = pd.merge(df, all_alarms, on="time", how="left")
    
    for i in range(12):
        df[f"alarms_count_{i+1}h_ago"] = df.groupby("region_id")["num_alarms"].shift(i+1)
        
    df = df.drop(columns=["num_alarms"])

    for i in range(24):
        df[f"alarm_status_{i+1}h_ago"] = df.groupby("region_id")["alarm"].shift(i+1)

    df = df.dropna(axis=0).reset_index(drop=True)

    return df