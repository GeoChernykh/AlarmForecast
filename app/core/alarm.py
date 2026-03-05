import datetime as dt
from dotenv import load_dotenv
import os

import requests

from ..errors import InvalidUsage

load_dotenv()

ALARM_API_KEY = os.getenv("ALARM_API_KEY")


def get_alarm_status():
    """Fetch raw alarm data from the external API.

    An :class:`InvalidUsage` is raised if the external service returns a
    non-200 status code so that the Flask error handler can turn it into
    a proper JSON response.
    """
    BASE_URL = "https://api.ukrainealarm.com/api/v3/alerts"

    headers = {}
    
    if ALARM_API_KEY:
        headers["Authorization"] = f"Bearer {ALARM_API_KEY}"

    response = requests.get(BASE_URL, headers=headers)
    if response.status_code == requests.codes.ok:
        return response.json()
    else:
        raise InvalidUsage(
            f"Alarm API error: {response.text}", status_code=response.status_code
        )


def format_alarm(region: str) -> dict:
    """Build the response payload for a single region request.

    The returned dictionary matches the schema previously produced by the
    original standalone ``alarm_api`` implementation, including a UTC
    timestamp and a nested ``alarms`` object.
    """
    alarm_data = get_alarm_status()

    region_alarm = None
    for alert in alarm_data:
        if region.lower() in alert.get("regionName", "").lower():
            region_alarm = alert
            break

    response_datetime = dt.datetime.now(dt.timezone.utc)
    return {
        "timestamp": response_datetime.isoformat(),
        "region": region,
        "alarms": {
            "active": bool(region_alarm),
            "type": region_alarm.get("type") if region_alarm else None,
        },
    }
