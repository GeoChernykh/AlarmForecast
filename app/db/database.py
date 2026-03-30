import sqlite3


class IswDb:
    def __init__(self, db_path) -> None:
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.c = self.conn.cursor()

    def _init_db(self) -> None:
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
            );
            
            CREATE TABLE IF NOT EXISTS article_bodies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
            )
        """)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    # --- context manager support ---
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.close()

    def add_article(self, date, title, url, text) -> None:
        pass


class AlarmsDb:
    def __int__(self):
        pass
        
    
class WeatherDb:
    def __init__(self):
        pass


class TelegramDb:
    def __init__(self):
        pass


class Database:
    def __init__(self, db_path):
        pass