from flask import Flask, jsonify
from flask_cors import CORS
from app.api.alarm_forecast import alarm_forecast_bp
from app.errors import InvalidUsage


app = Flask(__name__)
CORS(app)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


app.register_blueprint(alarm_forecast_bp)


if __name__ == "__main__":
    app.run(debug=True)