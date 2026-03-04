import datetime as dt
import json
import os

import requests
from flask import Flask, jsonify, request


API_TOKEN = os.environ.get("API_TOKEN")
ALARM_API_KEY = os.environ.get("ALARM_API_KEY")  # поки може бути None

app = Flask(__name__)


class InvalidUsage(Exception):
    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        else:
            self.status_code = 400
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route("/")
def home_page():
    return "<p><h2>KMA L2: Python SaaS – Alarm API.</h2></p>"


def get_alarm_status():

    BASE_URL = "https://api.ukrainealarm.com/api/v3/alerts"

    headers = {}

    if ALARM_API_KEY:
        headers["Authorization"] = f"Bearer {ALARM_API_KEY}"

    response = requests.get(BASE_URL, headers=headers)

    if response.status_code == requests.codes.ok:
        return response.json()
    else:
        raise InvalidUsage(
            f"Alarm API error: {response.text}",
            status_code=response.status_code,
        )

@app.route("/api/alarms", methods=["POST"])
def alarm_endpoint():

    if not request.is_json:
        raise InvalidUsage("JSON body required", status_code=400)

    json_data = request.get_json() or {}

    if json_data.get("token") is None:
        raise InvalidUsage("token is required", status_code=400)

    if json_data.get("token") != API_TOKEN:
        raise InvalidUsage("wrong API token", status_code=403)

    if json_data.get("requester_name") is None:
        raise InvalidUsage("requester_name required", status_code=400)

    if json_data.get("region") is None:
        raise InvalidUsage("region required", status_code=400)

    requester_name = json_data.get("requester_name")
    region = json_data.get("region")

    alarm_data = get_alarm_status()

    region_alarm = None

    for alert in alarm_data:
        if region.lower() in alert.get("regionName", "").lower():
            region_alarm = alert
            break

    response_datetime = dt.datetime.now(dt.timezone.utc)

    result = {
        "requester_name": requester_name,
        "timestamp": response_datetime.isoformat(),
        "region": region,
        "alarms": {
            "active": bool(region_alarm),
            "type": region_alarm.get("type") if region_alarm else None
        },
    }

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)