import sqlite3
import pandas as pd
import datetime as dt
from pathlib import Path
from app.db.isw_db import IswDb
from app.db.alarms_db import AlarmsDb
from app.db.weather_db import WeatherDb
from app.db.telegram_db import TelegramDb
from app.core.features.merge_data import merge_all_data

class Database:
    def __init__(self, db_path):
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row

        self.isw = IswDb(db_path)
        self.alarms = AlarmsDb(db_path)
        self.weather = WeatherDb(db_path)
        self.telegram = TelegramDb(db_path)

    def close(self) -> None:
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print("Rolling back")
            self.con.rollback()
        else:
            print("Commiting")
            self.con.commit()
        self.close()

    def update(self) -> None:
        self.alarms.update()
        print("Alarms updated.")
        
        weather_last_date = self.weather.get_latest_date()
        if weather_last_date == dt.date.today():
            self.weather.update()
            print("Weather updated.")
        else:
            print("Weather already up to date.")
        
        self.isw.update()
        print("ISW updated.")

        self.telegram.update()
        print("Telegram updated.")      

    def get_merged(self, start_date=None) -> pd.DataFrame:
        isw_start_date = None
        if start_date:
            start_dt = pd.to_datetime(start_date)
            isw_start_dt = start_dt - pd.Timedelta(days=35)
            isw_start_date = isw_start_dt.strftime('%Y-%m-%d')

        alarms_rows = self.alarms.get(start_date=start_date) if start_date else self.alarms.get()
        weather_rows = self.weather.get(start_date=start_date) if start_date else self.weather.get()
        telegram_rows = self.telegram.get(start_date=start_date) if start_date else self.telegram.get()
        isw_rows = self.isw.get(start_date=isw_start_date) if start_date else self.isw.get()

        df_alarms = pd.DataFrame([dict(row) for row in alarms_rows])
        df_weather = pd.DataFrame([dict(row) for row in weather_rows])
        df_telegram = pd.DataFrame([dict(row) for row in telegram_rows])
        df_isw = pd.DataFrame([dict(row) for row in isw_rows])

        final_df = merge_all_data(df_alarms, df_weather, df_isw, df_telegram)

        # Фільтруємо "запасні" дні
        if start_date and not final_df.empty:
            target_start = pd.to_datetime(start_date, utc=True).tz_convert("Europe/Kyiv")
            final_df = final_df[final_df['time'] >= target_start]
            final_df = final_df.reset_index(drop=True)

        return final_df

if __name__ == '__main__':
    db_path = Path("app/db/database.db")

    with Database(db_path) as db:
        db.update()