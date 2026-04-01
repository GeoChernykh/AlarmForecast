import datetime as dt
import json
from dotenv import load_dotenv
import os

import requests

from app.errors import InvalidUsage

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


def get_forecast(location, start_date, end_date, unit_group="metric"):
    start_date = str(start_date)
    end_date = str(end_date)

    BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    
    elements = ['datetime', 'temp', 'feelslike', 'humidity', 'dew',
       'precip', 'precipprob', 'preciptype', 'windspeed',
       'winddir', 'pressure', 'visibility', 'cloudcover',
       'uvindex', 'conditions',]
    elements = ",".join(elements)

    request_url = f"{BASE_URL}/{location}/{start_date}/{end_date}?unitGroup={unit_group}&key={WEATHER_API_KEY}&include=hours&elements={elements}&lang=en"

    print(request_url)
    return
    response = requests.get(request_url)

    if response.status_code == requests.codes.ok:
        return json.loads(response.text)
    else:
        raise InvalidUsage(response.text, status_code=response.status_code)


def format_forecast(raw_forecast, location):
    city = location.split(',')[0]
    days = raw_forecast.get("days")

    result = []
    for day in days:
        hours_data = day.get("hours")
        date = day.get("datetime")
        for hour_data in hours_data:
            time = hour_data.pop("datetime")           
            hour_data['real_hour_datetime'] = f"{date} {time}"
            hour_data['city'] = city
            result.append(hour_data)

    return result

def get_formated_forecast(location, start_date, end_date):
    raw = get_forecast(location, start_date, end_date)
    formated = format_forecast(raw, location)
    return formated


if __name__ == "__main__":
    today = dt.date.today()
    tomorrow = today + dt.timedelta(days=1)
    # raw = get_forecast(location="Kyiv,Ukraine", start_date=today, end_date=tomorrow)
    # formatted = format_forecast(raw, start_date="2026-03-06", end_date="2026-03-07", location="Kyiv,Ukraine",)
    formated = get_formated_forecast(location="Kyiv,Ukraine",start_date="2026-03-06", end_date="2026-03-07")
    print(formated)