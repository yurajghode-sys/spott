"""app/routes/users.py — User-specific endpoints"""
from flask import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import mongo
from app.utils.responses import success_response, error_response, paginated_response
from app.utils.helpers import get_pagination
from app.middleware.auth import get_current_user

users_bp = Blueprint("users", __name__)


@users_bp.route("/saved-events", methods=["GET"])
@jwt_required()
def saved_events():
    user = get_current_user()
    if not user:
        return error_response("User not found.", 404)
    saved_ids = user.get("saved_events", [])
    from app.utils.helpers import mongo_id
    from bson import ObjectId
    oids = [ObjectId(i) for i in saved_ids if len(i) == 24]
    events = list(mongo.db.events.find({"_id": {"$in": oids}}))
    for ev in events:
        ev["id"] = str(ev["_id"]); ev.pop("_id", None)
    return success_response(events)


@users_bp.route("/stats", methods=["GET"])
@jwt_required()
def user_stats():
    uid = get_jwt_identity()
    user = get_current_user()
    if not user:
        return error_response("User not found.", 404)
    confirmed = mongo.db.bookings.count_documents({"user_id": uid, "status": "confirmed"})
    cancelled = mongo.db.bookings.count_documents({"user_id": uid, "status": "cancelled"})
    reviews   = mongo.db.reviews.count_documents({"user_id": uid})
    return success_response({
        "confirmed_bookings": confirmed,
        "cancelled_bookings": cancelled,
        "reviews_written":    reviews,
        "saved_events":       len(user.get("saved_events", [])),
        "points":             user.get("points", 0),
    })
