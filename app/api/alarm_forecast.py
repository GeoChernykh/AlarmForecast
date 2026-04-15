import json
from flask import Flask, jsonify, request
from app.errors import InvalidUsage
from flask_cors import CORS
from pathlib import Path
import os
from functools import wraps
from dotenv import load_dotenv

load_dotenv()


forecast_path = Path("data/predictions/alarm_predictions.json")

app = Flask(__name__)
CORS(app)


def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        expected_key = os.getenv('ALARM_FORECAST_API_KEY')
        if not expected_key:
            raise InvalidUsage('API key not configured', status_code=500)
        if api_key != expected_key:
            raise InvalidUsage('Invalid API key', status_code=401)
        return f(*args, **kwargs)
    return decorated_function


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route('/forecast', methods=['GET'])
@require_api_key
def forecast():
    with open(forecast_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)