import sqlite3
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


if __name__ == '__main__':
    db_path = Path("app/db/database.db")

    # with Database(db_path) as db:
    #     db.isw.update()
    #     db.alarms.update()
    #     db.weather.update()
    #     db.telegram.update()