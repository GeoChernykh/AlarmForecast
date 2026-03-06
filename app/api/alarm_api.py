import os

from flask import Blueprint, request, jsonify

from ..errors import InvalidUsage
from ..core.alarm import format_alarm, get_alarm_status


alarm_bp = Blueprint("alarms", __name__, url_prefix="/alarms")


@alarm_bp.route("", methods=["GET"])
def alarm_endpoint():
    
    # region = request.args.get("region")

    # result = format_alarm(region=region)
    result = get_alarm_status()
    return jsonify(result)
