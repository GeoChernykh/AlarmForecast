import sqlite3
import pandas as pd
import datetime as dt
from pathlib import Path
from app.db.isw_db import IswDb
from app.db.alarms_db import AlarmsDb
from app.db.weather_db import WeatherDb
from app.db.telegram_db import TelegramDb


class Database:
    def __init__(self, db_path):
        self.con = sqlite3.connect(db_path)

        self.isw = IswDb(db_path)
        self.alarms = AlarmsDb(db_path)
        self.weather = WeatherDb(db_path)
        self.telegram = TelegramDb(db_path)

    def close(self) -> None:
        self.con.close()

    # --- context manager support ---
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
            print("Wether updated.")
        else:
            print("Weather already up to date.")
        
        self.isw.update()
        print("ISW updated.")

        self.telegram.update()
        print("Telegram updated.")      

    def get_merged(self, start_date) -> pd.DataFrame:
        pass


if __name__ == '__main__':
    db_path = Path("app/db/database.db")

    with Database(db_path) as db:
        db.update()