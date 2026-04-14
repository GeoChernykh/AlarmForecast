import json
from flask import Flask, jsonify
from app.errors import InvalidUsage
from pathlib import Path


forecast_path = Path("data/predictions/alarm_predictions.json")

app = Flask(__name__)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route('/forecast', methods=['GET'])
def forecast():
    with open(forecast_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)