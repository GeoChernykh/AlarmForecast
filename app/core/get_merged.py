import pandas as pd
from app.db.database import Database


def get_merged(dp_path, start_date) -> pd.DataFrame:
    with Database(dp_path) as db:
        # returns rows from database. You need to wrap them into pandas DataFrame
        isw_rows = db.isw.get(start_date=start_date)
        # alarms
        # weather
        # telegram


