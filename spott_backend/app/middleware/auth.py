"""app/middleware/auth.py — Authentication decorators"""
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.utils.responses import error_response
from app import mongo
from bson import ObjectId


def get_current_user():
    """Return the current user document from MongoDB."""
    try:
        uid = get_jwt_identity()
        return mongo.db.users.find_one({"_id": ObjectId(uid)})
    except Exception:
        return None


def jwt_required_safe(fn):
    """JWT required — returns clean JSON error on failure."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            return error_response(str(e), 401, "UNAUTHORIZED")
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    """Decorator: requires valid JWT + admin role."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return error_response("Authentication required.", 401, "UNAUTHORIZED")
        user = get_current_user()
        if not user or user.get("role") != "admin":
            return error_response("Admin privileges required.", 403, "FORBIDDEN")
        return fn(*args, **kwargs)
    return wrapper


def login_required(fn):
    """Decorator: requires valid JWT (any role)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return error_response("Please log in to continue.", 401, "UNAUTHORIZED")
        user = get_current_user()
        if not user or not user.get("is_active", True):
            return error_response("Account not found or deactivated.", 401, "ACCOUNT_INACTIVE")
        return fn(*args, **kwargs)
    return wrapper
