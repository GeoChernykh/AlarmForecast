import sqlite3


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
                url TEXT NOT NULL,
                text TEXT NOT NULL
            )
        """)
        self.con.commit()

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

    def add_article(self, date, title, url, text) -> None:
        self.con.execute(
            "INSERT INTO articles (date, title, url, text) VALUES (?, ?, ?)", (date, title, url, text)
        )

    def get_articles(
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