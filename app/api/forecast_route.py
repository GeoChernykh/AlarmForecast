from flask import Blueprint, request, jsonify
import datetime as dt

from ..errors import InvalidUsage
from ..core.forecast import get_forecast, format_forecast


forecast_bp = Blueprint("forecast", __name__, url_prefix="/forecast")


@forecast_bp.route("", methods=["GET"])
def forecast_endpoint():
    location = request.args.get("location")

    if location is None:
        raise InvalidUsage("location is required", status_code=400)

    curr_datetime = dt.datetime.now()
    start_date = curr_datetime.date()
    end_date = start_date + dt.timedelta(days=1)

    raw_forecast = get_forecast(location=location, start_date=start_date, end_date=end_date)
    forecast = format_forecast(raw_forecast, start_date, end_date, curr_datetime)

    return jsonify(forecast)