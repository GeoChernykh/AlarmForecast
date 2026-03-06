import datetime as dt
from dotenv import load_dotenv
import os

import requests

from app.errors import InvalidUsage

load_dotenv()

ALARM_API_KEY = os.getenv("ALARM_API_KEY")

ALL_REGIONS = [
    "Kyiv",
    "Kyiv Oblast",
    "Lviv Oblast",
    "Kharkiv Oblast",
    "Odesa Oblast",
    "Dnipro Oblast",
    "Zaporizhzhia Oblast",
    "Chernihiv Oblast",
    "Sumy Oblast",
    "Poltava Oblast",
    "Vinnytsia Oblast",
    "Zhytomyr Oblast",
    "Rivne Oblast",
    "Volyn Oblast",
    "Ternopil Oblast",
    "Ivano-Frankivsk Oblast",
    "Chernivtsi Oblast",
    "Khmelnytskyi Oblast",
    "Cherkasy Oblast",
    "Kirovohrad Oblast",
    "Mykolaiv Oblast",
    "Kherson Oblast",
    "Donetsk Oblast",
    "Luhansk Oblast",
    "Zakarpattia Oblast"
]


def get_alarm_status():
    """Fetch raw alarm data from Ukraine Alarm API.

    Returns a list of alerts if successful, or an empty list if request fails
    or response is not valid JSON.
    """
    BASE_URL = "https://api.ukrainealarm.com/api/v3/alerts"

    headers = {
        "Authorization": f"{ALARM_API_KEY}",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    try:
        response = requests.get(BASE_URL, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return []


def format_alarm(alarm_data) -> dict:
    regions = [
        {
            "region": region,
            "active": any(region == alert.get("regionName") for alert in alarm_data),
            "type": next(
                (alert.get("type") for alert in alarm_data if region == alert.get("regionName")),
                None
            ),
        }
        for region in ALL_REGIONS
    ]

    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()

    return {
        "success": True,
        "timestamp": timestamp,
        "data": regions
    }


if __name__ == "__main__":
    print(format_alarm(get_alarm_status()))
