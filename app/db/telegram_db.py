import sqlite3
import json
from pathlib import Path
import pandas as pd
from app.core.features.telegram_features import preprocess
from app.core.scraping.telegram_parser import fetch_messages
import datetime as dt


class TelegramDb:
    def __init__(self, db_path):
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.cur = self.con.cursor()
        self._init_db()

    def _init_db(self) -> None:
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS telegram (
                datetime                    TEXT PRIMARY KEY,
                messages_count              INTEGER,
                has_threat_sum              INTEGER,
                nlp_артобстрілу             INTEGER,
                nlp_бпла                    INTEGER,
                nlp_відбій                  INTEGER,
                nlp_відбій_тривоги          INTEGER,
                nlp_дніпропетровська        INTEGER,
                nlp_донецька                INTEGER,
                nlp_запорізька              INTEGER,
                nlp_нікополь                INTEGER,
                nlp_нікополь_нікопольська   INTEGER,
                nlp_нікопольська            INTEGER,
                nlp_повітряна               INTEGER,
                nlp_повітряна_тривога       INTEGER,
                nlp_тривога                 INTEGER,
                nlp_тривоги                 INTEGER,
                nlp_харківська              INTEGER,
                msg_count_last_3h           INTEGER,
                msg_count_last_24h          INTEGER,
                threat_diff_1h              INTEGER
            );
        """)
        self.con.commit()

    def load_existing(self, path: Path = Path('data/telegram/telegram_hourly_features_v3.csv')) -> None:
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        data = pd.read_csv(path)
        rows = data.to_dict('records')
        self.add(rows)

    def add(self, records: list[dict]) -> None:
        self.con.executemany("""
            INSERT OR REPLACE INTO telegram (
                datetime, messages_count, has_threat_sum,
                nlp_артобстрілу, nlp_бпла, nlp_відбій, nlp_відбій_тривоги,
                nlp_дніпропетровська, nlp_донецька, nlp_запорізька,
                nlp_нікополь, nlp_нікополь_нікопольська, nlp_нікопольська,
                nlp_повітряна, nlp_повітряна_тривога, nlp_тривога, nlp_тривоги,
                nlp_харківська, msg_count_last_3h, msg_count_last_24h, threat_diff_1h
            ) VALUES (
                :datetime, :messages_count, :has_threat_sum,
                :nlp_артобстрілу, :nlp_бпла, :nlp_відбій, :nlp_відбій_тривоги,
                :nlp_дніпропетровська, :nlp_донецька, :nlp_запорізька,
                :nlp_нікополь, :nlp_нікополь_нікопольська, :nlp_нікопольська,
                :nlp_повітряна, :nlp_повітряна_тривога, :nlp_тривога, :nlp_тривоги,
                :nlp_харківська, :msg_count_last_3h, :msg_count_last_24h, :threat_diff_1h
            )
        """, records)
        self.con.commit()

    def get(self, start_date: str | None = None, end_date: str | None = None) -> list[sqlite3.Row]:
        query = "SELECT * FROM telegram"
        params = []

        if start_date and end_date:
            query += " WHERE datetime BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date:
            query += " WHERE datetime >= ?"
            params = [start_date]
        elif end_date:
            query += " WHERE datetime <= ?"
            params = [end_date]

        query += " ORDER BY datetime"

        return self.con.execute(query, params).fetchall()

    def get_latest_datetime(self) -> dt.datetime | None:
        row = self.con.execute("SELECT MAX(datetime) FROM telegram").fetchone()
        if row[0] is None:
            return None
        return dt.datetime.fromisoformat(row[0])

    def update(self) -> None:
        latest = self.get_latest_datetime()

        if not latest:
            try:
                self.load_existing()
                print("Data loaded successfully.")
                latest = self.get_latest_datetime()
            except FileNotFoundError as e:
                print(e)
                print("Fetching from scratch...")
                latest = dt.datetime(2022, 2, 24)

        messages = fetch_messages(start_date=latest)
        preprocessed_msgs, _ = preprocess(messages) 
        preprocessed_msgs['datetime'] = preprocessed_msgs['datetime'].astype(str)
        rows = preprocessed_msgs.to_dict('records')
        if rows:
            self.add(rows)