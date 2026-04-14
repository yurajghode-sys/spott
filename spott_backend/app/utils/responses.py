"""app/utils/responses.py — Standardised JSON response helpers"""
from flask import jsonify
from bson import ObjectId
import json, datetime


class MongoJSONEncoder(json.JSONEncoder):
    """Handle ObjectId and datetime serialisation."""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)


def _clean(data):
    """Recursively convert ObjectId → str in dicts/lists."""
    if isinstance(data, dict):
        return {k: _clean(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_clean(i) for i in data]
    if isinstance(data, ObjectId):
        return str(data)
    if isinstance(data, (datetime.datetime, datetime.date)):
        return data.isoformat()
    return data


def success_response(data=None, message="Success", status_code=200, **kwargs):
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = _clean(data)
    body.update(kwargs)
    return jsonify(body), status_code


def error_response(message="An error occurred", status_code=400, code=None, errors=None):
    body = {"success": False, "error": message}
    if code:
        body["code"] = code
    if errors:
        body["errors"] = errors
    return jsonify(body), status_code


def paginated_response(items, total, page, per_page, message="Success"):
    return jsonify({
        "success": True,
        "message": message,
        "data": _clean(items),
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, (total + per_page - 1) // per_page),
            "has_next": page * per_page < total,
            "has_prev": page > 1,
        },
    }), 200
