import pandas as pd
import numpy as np
import datetime as dt
import joblib
import json
from pathlib import Path
from app.db.database import Database
from app.core.features.weather_features import add_region_ids
from app.core.features.alarms_features import add_neighbor_alarm_count


models_dir = Path("app/models/")

model_path = models_dir / f"lgbm_pipeline.joblib"
if not model_path.exists():
    raise FileNotFoundError(f"Model not found on path: {model_path}")
pipeline = joblib.load(model_path)

db_path = Path("app/db/database.db")
if not db_path.exists():
    raise FileNotFoundError(f"Database not found on path: {db_path}")

curr_hour = pd.Timestamp.now(tz="Europe/Kyiv").floor('h')
curr_hour_str = curr_hour.strftime("%Y-%m-%d %H:%M:%S")

with Database(db_path) as db:
    db.update()
    curr_hour_data = db.get_merged(start_date=curr_hour_str)
    weather_forecast_rows = db.weather.get(start_date=curr_hour_str)
    
df_weather = pd.DataFrame([dict(row) for row in weather_forecast_rows])
df_weather = add_region_ids(df_weather)

df_weather = df_weather.drop(columns=['city'], errors='ignore')
df_weather = df_weather.rename(columns={'real_hour_datetime': 'time'})
df_weather['time'] = pd.to_datetime(df_weather['time']).dt.tz_localize("Europe/Kyiv", ambiguous="NaT", nonexistent="shift_forward")

encoder_path = models_dir / 'preprocessing/merged_df_encoder.joblib'
if not encoder_path.exists():
    raise FileNotFoundError(f"Encoder not found on path: {encoder_path}")
encoder = joblib.load(encoder_path)

cat_cols = ['preciptype', 'conditions']
df_weather[cat_cols] = encoder.transform(df_weather[cat_cols])

timeline = pd.date_range(curr_hour, curr_hour + dt.timedelta(hours=24), freq='h')
region_ids = df_weather.region_id.unique()

spine = pd.MultiIndex.from_product([region_ids, timeline], names=["region_id", "time"]) \
                .to_frame(index=False) \
                .sort_values(["region_id", "time"]) \
                .reset_index(drop=True)

not_weather_cols = list(set(curr_hour_data.columns) - set(df_weather.columns))

df = pd.merge(spine, df_weather, how='inner', on=['region_id', 'time'])
df = pd.merge(df, curr_hour_data[not_weather_cols + ['region_id', 'time']], how='left', on=['region_id', 'time'])

df["hour"] = df["time"].dt.hour
df['day_of_week'] = df['time'].dt.dayofweek
df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

df = df.drop(columns='alarm')
alarm_cols = [col for col in df.columns if col.startswith("alarm")] + ['neighbor_alarm_count']
cols_to_fill = [col for col in df.columns if col not in alarm_cols]
df[cols_to_fill] = df.groupby("region_id")[cols_to_fill].ffill()

forecast = pd.DataFrame(columns=['region_id', 'time', 'alarm'])
prev_hour_data = curr_hour_data.copy()
curr_hour_data = curr_hour_data.drop(columns='alarm', errors='ignore')

for hour in timeline:
    curr_hour_data = df.loc[df.time == hour].copy().reset_index(drop=True)

    if curr_hour_data[alarm_cols].isna().any().any():
        # fill alarms_count and alarm_status
        curr_hour_data['alarms_count_1h_ago'] = prev_hour_data['alarm'].sum()
        curr_hour_data['alarm_status_1h_ago'] = prev_hour_data['alarm'].values
        for i in range(1, 24):
            curr_hour_data[f"alarms_count_{i+1}h_ago"] = prev_hour_data[f"alarms_count_{i}h_ago"].values
            curr_hour_data[f"alarm_status_{i+1}h_ago"] = prev_hour_data[f"alarm_status_{i}h_ago"].values

        temp = add_neighbor_alarm_count(prev_hour_data)
        curr_hour_data['neighbor_alarm_count'] = temp['neighbor_alarm_count']
        assert ~curr_hour_data[alarm_cols].isna().any().any()
    
    pred = pipeline.predict(curr_hour_data)
    pred_probs = pipeline.predict_proba(curr_hour_data)
    res = pd.DataFrame({"region_id": curr_hour_data["region_id"], "time": curr_hour_data["time"], "alarm": pred, "alarm_prob": pred_probs[:, 1]})
    forecast = pd.concat([forecast, res], axis=0, ignore_index=True)
    
    prev_hour_data = curr_hour_data.copy()
    prev_hour_data['alarm'] = pred
    assert ~prev_hour_data[alarm_cols].isna().any().any()

def temperature_scale(probs, temperature=2.0):
    probs = np.clip(probs, 1e-7, 1 - 1e-7)
    logits = np.log(probs / (1 - probs))
    scaled_logits = logits / temperature
    return 1 / (1 + np.exp(-scaled_logits))

TEMPERATURE = 2.0
forecast['alarm_prob'] = temperature_scale(forecast['alarm_prob'].values, temperature=TEMPERATURE)

forecast['time_str'] = pd.to_datetime(forecast['time']).dt.strftime('%H:%M')

regions = pd.read_csv("data/alarms/regions.csv")
forecast = pd.merge(forecast, regions[['region_id', 'region']], how='left', on='region_id')

result = forecast.groupby('region_id').apply(
    lambda g: dict(zip(g['time_str'], g['alarm_prob']))
).to_dict()

output = {"last_prediction_time": str(dt.datetime.now()), "regions_forecast": {str(k): v for k, v in result.items()}}

forecast_save_dir = Path("data/predictions/alarm_predictions.json")
if not forecast_save_dir.parent.exists():
    forecast_save_dir.parent.mkdir(parents=True, exist_ok=True)

with open(forecast_save_dir, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)
print(f"Forecast saved to {forecast_save_dir}")