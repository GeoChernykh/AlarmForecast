import pandas as pd
from app.db.database import Database


def get_merged(dp_path, start_date) -> pd.DataFrame:
    with Database(dp_path) as db:
        isw = db.isw.get(start_date=start_date)
        # alarms
        # weather
        # telegram


