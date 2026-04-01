import sqlite3
from pathlib import Path
import pandas as pd
import datetime as dt
from app.core.features.alarms_features import explode_by_hour, fix_regions
from app.core.scraping.alarm import get_alarms_history_by_hour


class AlarmsDb:
    def __init__(self, db_path):
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.cur = self.con.cursor()
        self._init_db()

    def _init_db(self):
        self.con.execute(
            """
            CREATE TABLE IF NOT EXISTS alarms (
                region_id INTEGER NOT NULL,
                region TEXT NOT NULL,
                time TEXT NOT NULL,
                alarm INTEGER NOT NULL,
                has_started INTEGER NOT NULL,
                has_ended INTEGER NOT NULL,
                PRIMARY KEY (region_id, time)
            )
            """
        )

    def load_existing(self):
        path = Path("data/alarms/alarms_data_preprocessed_v2.csv")

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        alarms = pd.read_csv(path)
        alarms["start"] = pd.to_datetime(alarms["start"])
        alarms["end"] = pd.to_datetime(alarms["end"])

        alarms = fix_regions(alarms)
        alarms_exploded = explode_by_hour(alarms)

        rows = alarms_exploded.to_dict('records')
        print(rows[0])
        self.add(rows)

    def add(self, alarms) -> None:
        self.con.executemany(
            """
            INSERT OR REPLACE INTO alarms 
            VALUES (:region_id, :region, :time, :alarm, :has_started, :has_ended)
            """,
            alarms
        )
        self.con.commit()

    def get(self, start: str | None = None, end: str | None = None, ) -> list[sqlite3.Row]:
        query = """
            SELECT *
            FROM alarms
        """
        params = []

        if start and end:
            query += " WHERE time BETWEEN ? AND ?"
            params = [start, end]
        elif start:
            query += " WHERE time >= ?"
            params = [start]
        elif end:
            query += " WHERE time <= ?"
            params = [end]

        query += " ORDER BY region_id, time"

        return self.con.execute(query, params).fetchall()
    
    def get_latest_date(self) -> str | None:
        row = self.con.execute("SELECT MAX(time) FROM alarms").fetchone()
        return row[0]

    def update(self):
        # get last date and run script
        latest_date = self.get_latest_date()

        if not latest_date:
            try:
                self.load_existing()
                print("Data loaded succesfully.")
                latest_date = self.get_latest_date()
            except FileNotFoundError:
                print("No existing data. Scraping...")
                latest_date = dt.date(2022, 2, 24)

        date_range = pd.date_range(latest_date, dt.date.today() + dt.timedelta(days=1), freq='d')

        for date in date_range:
            try:
                date_hist = get_alarms_history_by_hour(date)
                rows = date_hist.to_dict('records')
                print(f"Inserting {len(rows)} rows for {date}, sample: {rows[0] if rows else 'empty'}")
                self.add(rows)
            except Exception as e:
                print(f"Failed for {date}: {e}")