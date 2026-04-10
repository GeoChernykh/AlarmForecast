import pandas as pd
import datetime as dt
import joblib
from pathlib import Path
from app.db.database import Database
from app.core.features.weather_features import add_region_ids



model_path = Path("app/models/lgbm_pipeline.joblib")
db_path = Path("app/db/database.db")
last_hour = pd.Timestamp.now(tz="Europe/Kyiv").floor('h')

if not model_path.exists():
    raise FileNotFoundError("Model not found on path: ", model_path)

if not db_path.exists():
    raise FileNotFoundError("Database not found on path: ", db_path)

pipeline = joblib.load(model_path)

with Database(db_path) as db:
    last_hour_data = db.get_merged(start_date=last_hour.strftime("%Y-%m-%d %H:%M:%S"))
    weather_forecast = db.weather.get(start_date=last_hour)
    
weather_forecast = add_region_ids(weather_forecast)