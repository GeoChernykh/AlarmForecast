import json
from flask import Blueprint, jsonify
from app.errors import InvalidUsage
from pathlib import Path


forecast_path = Path("data/predictions/alarm_predictions.json")

alarm_forecast_bp = Blueprint('alarm_forecast', __name__)


@alarm_forecast_bp.route('/forecast', methods=['GET'])
def forecast():
    with open(forecast_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)