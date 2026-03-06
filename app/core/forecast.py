import datetime as dt
import json
from dotenv import load_dotenv
import os

import requests

from ..errors import InvalidUsage

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


def get_forecast(location, start_date, end_date, unit_group="metric"):
    BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    elements = "datetime,humidity,offset,temp,windspeed,pressure,visibility,severerisk,offsetseconds,cloudcover"
    request_url = f"{BASE_URL}/{location}/{start_date}/{end_date}?unitGroup={unit_group}&key={WEATHER_API_KEY}&include=hours&elements={elements}&lang=en"

    response = requests.get(request_url)
    print(response.json())

    if response.status_code == requests.codes.ok:
        return format_forecast(json.loads(response.text), start_date, end_date)
    else:
        raise InvalidUsage(response.text, status_code=response.status_code)


def format_forecast(raw_forecast, start_date, end_date):
    """Transform raw forecast data into hourly forecast dict keyed by datetime."""
    curr_datetime = dt.datetime.now()

    days = raw_forecast.get("days")
    hours = []
    for day in days:
        hours.extend(day.get("hours"))

    hours = hours[curr_datetime.hour:(curr_datetime.hour + 24)]

    forecast = {}
    for hour in hours:
        datetime = hour.pop("datetime")
        h = int(datetime[:2])
        if h >= curr_datetime.hour:
            datetime = f"{str(start_date)} {datetime}"
        else:
            datetime = f"{str(end_date)} {datetime}"
        forecast[datetime] = hour

    return forecast


if __name__ == "__main__":
    print(get_forecast(location="Kyiv,Ukraine", start_date="2026-03-06", end_date="2026-03-07"))