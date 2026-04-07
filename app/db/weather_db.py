import sqlite3
from pathlib import Path
import pandas as pd
import datetime as dt
from app.core.scraping.weather_forecast import get_formated_forecast


class WeatherDb:
    def __init__(self, db_path):
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.cur = self.con.cursor()
        self._init_db()

    def _init_db(self) -> None:
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                temp                REAL,
                feelslike           REAL,
                humidity            REAL,
                dew                 REAL,
                precip              REAL,
                precipprob          REAL,
                preciptype          TEXT,
                windspeed           REAL,
                winddir             REAL,
                pressure            REAL,
                visibility          REAL,
                cloudcover          REAL,
                uvindex             REAL,
                conditions          TEXT,
                real_hour_datetime  TEXT NOT NULL,
                city                TEXT NOT NULL,
                PRIMARY KEY (city, real_hour_datetime)
            )
        """)
        self.con.commit()

    def load_existing(self) -> None:
        path = Path('data/weather/weather_data_preprocessed_v3.csv')

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        weather = pd.read_csv(path)
        rows = weather.to_dict('records')

        self.add(rows)
        self.con.commit()

    def add(self, rows: list[dict]) -> None:
        self.con.executemany("""
            INSERT OR REPLACE INTO weather (
                temp, feelslike, humidity, dew, precip, precipprob, preciptype,
                windspeed, winddir, pressure, visibility, cloudcover, uvindex,
                conditions, real_hour_datetime, city
            ) VALUES (
                :temp, :feelslike, :humidity, :dew, :precip, :precipprob, :preciptype,
                :windspeed, :winddir, :pressure, :visibility, :cloudcover, :uvindex,
                :conditions, :real_hour_datetime, :city
            )
        """, rows)
        self.con.commit()

    def get(self, start_date: str | None = None, end_date: str | None = None) -> list[sqlite3.Row]:
        query = """
            SELECT *
            FROM weather
        """
        params = []

        if start_date and end_date:
            query += " WHERE real_hour_datetime BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date:
            query += " WHERE real_hour_datetime >= ?"
            params = [start_date]
        elif end_date:
            query += " WHERE real_hour_datetime <= ?"
            params = [end_date]

        query += " ORDER BY real_hour_datetime"

        return self.con.execute(query, params).fetchall()

    def get_latest_date(self) -> str | None:
        row = self.con.execute("SELECT MAX(real_hour_datetime) FROM weather").fetchone()
        datetime = row[0]  # returns None if table is empty
        if datetime is None:
            return datetime
        
        date = pd.to_datetime(datetime).date()
        return date

    def update(self) -> None:
        today = dt.date.today()
        latest_date = self.get_latest_date()

        if not latest_date:
            try:
                self.load_existing()
                print("Data loaded successfully.")
                latest_date = self.get_latest_date()
            except FileNotFoundError:
                print("No existing data found.")
                latest_date = today

        cities = pd.read_csv('data/alarms/regions.csv')['city'].tolist()
        cities = set(cities)
        rows = []

        for c in cities:
            location = f"{c},Ukraine"
            weather = get_formated_forecast(location=location,
                                            start_date=today, # must be setted to latest date but due to high querry cost setted to today
                                            end_date=today + dt.timedelta(days=1))
            rows.extend(weather)

        self.add(rows)


        

