import sqlite3
import json
from pathlib import Path
from app.core.scraping.scraper_isw_v2 import scrape_isw


class IswDb:
    def __init__(self, db_path) -> None:
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys = ON")
        self.cur = self.con.cursor()
        self._init_db()

    def _init_db(self) -> None:
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                text TEXT NOT NULL
            )
        """)
        self.con.commit()

    def load_existing(self) -> None:
        path = Path('data/isw/isw_data_v2.json')

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        with open(path, encoding="utf-8") as f:
            articles = json.load(f)

        self.con.executemany(
            "INSERT OR IGNORE INTO articles (date, title, url, text) VALUES (:date, :title, :url, :text)", articles
        )
        self.con.commit()

    def add(self, articles) -> None:
        self.con.executemany(
            "INSERT OR IGNORE INTO articles (date, title, url, text) VALUES (:date, :title, :url, :text)", articles
        )
        self.con.commit()

    def get(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[sqlite3.Row]:
        query = """
            SELECT id, date, title, url, text
            FROM articles
        """
        params = []

        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date:
            query += " WHERE date >= ?"
            params = [start_date]
        elif end_date:
            query += " WHERE date <= ?"
            params = [end_date]

        query += " ORDER BY date"

        return self.con.execute(query, params).fetchall()
    
    def get_latest_date(self) -> str | None:
        row = self.con.execute("SELECT MAX(date) FROM articles").fetchone()
        return row[0]  # returns None if table is empty
    
    def update(self) -> None:
        latest_date = self.get_latest_date()

        if not latest_date:
            try:
                self.load_existing()
                print("Data loaded succesfully.")
                latest_date = self.get_latest_date()
            except FileNotFoundError:
                print("No existing data. Scraping...")

        articles = scrape_isw(start_date=latest_date, max_pages=100)
        if articles:
            self.add(articles)

        
