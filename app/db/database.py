import sqlite3
from pathlib import Path
from app.db.isw_db import IswDb


class Database:
    def __init__(self, db_path):
        self.con = sqlite3.connect(db_path)

        self.isw = IswDb(db_path)

    def close(self) -> None:
        self.con.close()

    # --- context manager support ---
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.con.rollback()
        else:
            self.con.commit()
        self.close()


if __name__ == '__main__':
    db_path = Path("app/db/database.db")

    with Database(db_path) as db:
        db.isw.update()