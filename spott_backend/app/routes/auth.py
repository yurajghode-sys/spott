"""
app/routes/auth.py
POST /api/auth/register    — Create account
POST /api/auth/login       — Get JWT token
POST /api/auth/logout      — Client-side token discard
GET  /api/auth/me          — Current user profile
PUT  /api/auth/me          — Update profile
POST /api/auth/newsletter  — Subscribe to newsletter
"""

import bcrypt
from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from app import mongo, limiter
from app.models import make_user
from app.utils.responses import success_response, error_response
from app.utils.helpers import is_valid_email, is_valid_phone, sanitise_str, utcnow
from app.middleware.auth import get_current_user
from bson import ObjectId

auth_bp = Blueprint("auth", __name__)


# ─── Register ────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per minute")
def register():
    data = request.get_json(silent=True) or {}

    name  = sanitise_str(data.get("name",  ""), 120)
    email = sanitise_str(data.get("email", ""), 255).lower()
    phone = sanitise_str(data.get("phone", ""), 20)
    pwd   = data.get("password", "")

    # ── Validation ────────────────────────────────────────────
    if not name:
        return error_response("Name is required.", 422, errors={"name": "required"})
    if not is_valid_email(email):
        return error_response("Valid email is required.", 422, errors={"email": "invalid"})
    if len(pwd) < 6:
        return error_response("Password must be at least 6 characters.", 422, errors={"password": "too_short"})
    if phone and not is_valid_phone(phone):
        return error_response("Invalid phone number.", 422, errors={"phone": "invalid"})

    # ── Check duplicate ───────────────────────────────────────
    if mongo.db.users.find_one({"email": email}):
        return error_response("Email is already registered.", 409, "EMAIL_EXISTS")

    # ── Hash password & save ──────────────────────────────────
    pw_hash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt(rounds=12)).decode()
    user_doc = make_user(name, email, pw_hash, phone=phone)
    result = mongo.db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # ── Issue token ───────────────────────────────────────────
    token = create_access_token(identity=user_id, additional_claims={"role": "user"})

    return success_response({
        "token": token,
        "user": {
            "id":    user_id,
            "name":  name,
            "email": email,
            "role":  "user",
        }
    }, "Account created! Welcome to Spott 🎉", 201)


# ─── Login ───────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("15 per minute")
def login():
    data  = request.get_json(silent=True) or {}
    email = sanitise_str(data.get("email", ""), 255).lower()
    pwd   = data.get("password", "")

    if not email or not pwd:
        return error_response("Email and password are required.", 422)

    user = mongo.db.users.find_one({"email": email})
    if not user:
        return error_response("Invalid email or password.", 401, "INVALID_CREDENTIALS")
    if not user.get("is_active", True):
        return error_response("Account is deactivated.", 403, "ACCOUNT_INACTIVE")
    if not bcrypt.checkpw(pwd.encode(), user["password"].encode()):
        return error_response("Invalid email or password.", 401, "INVALID_CREDENTIALS")

    # Update last login
    mongo.db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": utcnow()}})

    user_id = str(user["_id"])
    role    = user.get("role", "user")
    token   = create_access_token(identity=user_id, additional_claims={"role": role})

    return success_response({
        "token": token,
        "user": {
            "id":     user_id,
            "name":   user["name"],
            "email":  user["email"],
            "role":   role,
            "avatar": user.get("avatar_url", ""),
        }
    }, f"Welcome back, {user['name'].split()[0]}! 👋")


# ─── Logout ──────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
def logout():
    # JWT is stateless — client discards the token
    return success_response(message="Logged out successfully.")


# ─── Get current user ─────────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    user = get_current_user()
    if not user:
        return error_response("User not found.", 404)

    uid = str(user["_id"])
    # Booking stats
    booking_count  = mongo.db.bookings.count_documents({"user_id": uid, "status": "confirmed"})
    upcoming_count = 0  # can be enriched

    return success_response({
        "id":             uid,
        "name":           user.get("name", ""),
        "email":          user.get("email", ""),
        "phone":          user.get("phone", ""),
        "role":           user.get("role", "user"),
        "avatar_url":     user.get("avatar_url", ""),
        "bio":            user.get("bio", ""),
        "interests":      user.get("interests", []),
        "points":         user.get("points", 0),
        "saved_events":   user.get("saved_events", []),
        "bookings_count": booking_count,
        "created_at":     user.get("created_at"),
        "last_login":     user.get("last_login"),
    })


# ─── Update profile ───────────────────────────────────────────
@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_me():
    user = get_current_user()
    if not user:
        return error_response("User not found.", 404)

    data = request.get_json(silent=True) or {}
    allowed = ["name", "phone", "bio", "avatar_url", "interests"]
    updates = {}
    for field in allowed:
        if field in data:
            updates[field] = sanitise_str(str(data[field]), 500) if field not in ("interests",) else data[field]

    if "phone" in updates and updates["phone"] and not is_valid_phone(updates["phone"]):
        return error_response("Invalid phone number.", 422)

    updates["updated_at"] = utcnow()
    mongo.db.users.update_one({"_id": user["_id"]}, {"$set": updates})
    return success_response(message="Profile updated successfully.")


# ─── Toggle saved event ────────────────────────────────────────
@auth_bp.route("/me/save-event/<event_id>", methods=["POST"])
@jwt_required()
def toggle_save_event(event_id):
    user = get_current_user()
    if not user:
        return error_response("User not found.", 404)

    saved = user.get("saved_events", [])
    if event_id in saved:
        mongo.db.users.update_one({"_id": user["_id"]}, {"$pull": {"saved_events": event_id}})
        return success_response({"saved": False}, "Event removed from saved.")
    else:
        mongo.db.users.update_one({"_id": user["_id"]}, {"$addToSet": {"saved_events": event_id}})
        return success_response({"saved": True}, "Event saved!")


# ─── Newsletter subscribe ─────────────────────────────────────
@auth_bp.route("/newsletter", methods=["POST"])
@limiter.limit("5 per minute")
def newsletter():
    data  = request.get_json(silent=True) or {}
    email = sanitise_str(data.get("email", ""), 255).lower()

    if not is_valid_email(email):
        return error_response("Valid email is required.", 422)

    try:
        mongo.db.newsletter.insert_one({"email": email, "created_at": utcnow()})
    except Exception:
        pass  # duplicate — already subscribed

    return success_response(message="You're subscribed! 🎉 Weekly picks incoming.")
