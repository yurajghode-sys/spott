"""
app/routes/admin.py — Admin-only APIs
GET  /api/admin/dashboard        — Stats overview
GET  /api/admin/users            — All users (paginated)
GET  /api/admin/users/<id>       — Single user
PUT  /api/admin/users/<id>       — Update user (role / status)
DELETE /api/admin/users/<id>     — Delete user
GET  /api/admin/bookings         — All bookings
PUT  /api/admin/bookings/<id>    — Update booking status
GET  /api/admin/events           — All events (incl. drafts)
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from app import mongo
from app.utils.responses import success_response, error_response, paginated_response
from app.utils.helpers import get_pagination, mongo_id, sanitise_str, utcnow
from app.middleware.auth import admin_required
from bson import ObjectId

admin_bp = Blueprint("admin", __name__)


# ─── Dashboard stats ──────────────────────────────────────────
@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def dashboard():
    total_users    = mongo.db.users.count_documents({})
    total_events   = mongo.db.events.count_documents({})
    total_bookings = mongo.db.bookings.count_documents({"status": "confirmed"})

    # Revenue (sum of amount_paid)
    pipeline = [
        {"$match": {"status": "confirmed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_paid"}}},
    ]
    rev_result = list(mongo.db.bookings.aggregate(pipeline))
    total_revenue = rev_result[0]["total"] if rev_result else 0.0

    # Recent bookings
    recent_bookings = list(mongo.db.bookings.find({})
                                            .sort("booking_date", -1)
                                            .limit(5))
    for b in recent_bookings:
        b["id"] = str(b["_id"]); b.pop("_id", None)

    # Popular events
    popular = list(mongo.db.events.find({"status": "published"})
                                  .sort("booked_count", -1)
                                  .limit(5))
    for ev in popular:
        ev["id"] = str(ev["_id"]); ev.pop("_id", None)

    # Category breakdown
    cat_pipeline = [
        {"$match": {"status": "published"}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    categories = [{"name": r["_id"], "count": r["count"]}
                  for r in mongo.db.events.aggregate(cat_pipeline) if r["_id"]]

    # Monthly bookings (last 6 months)
    monthly_pipeline = [
        {"$match": {"status": "confirmed"}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$booking_date"}},
            "count": {"$sum": 1},
            "revenue": {"$sum": "$amount_paid"},
        }},
        {"$sort": {"_id": 1}},
        {"$limit": 6},
    ]
    monthly = list(mongo.db.bookings.aggregate(monthly_pipeline))

    return success_response({
        "stats": {
            "total_users":    total_users,
            "total_events":   total_events,
            "total_bookings": total_bookings,
            "total_revenue":  round(total_revenue, 2),
        },
        "recent_bookings": recent_bookings,
        "popular_events":  popular,
        "category_breakdown": categories,
        "monthly_data":    monthly,
    })


# ─── List all users ───────────────────────────────────────────
@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    page, per_page = get_pagination()
    query = {}

    role = request.args.get("role", "").strip()
    if role in ("admin", "user"):
        query["role"] = role

    search = request.args.get("q", "").strip()
    if search:
        query["$or"] = [
            {"name":  {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    total = mongo.db.users.count_documents(query)
    users = list(mongo.db.users.find(query, {"password": 0})
                               .sort("created_at", -1)
                               .skip((page - 1) * per_page)
                               .limit(per_page))
    for u in users:
        u["id"] = str(u["_id"]); u.pop("_id", None)
        u["bookings_count"] = mongo.db.bookings.count_documents({"user_id": u["id"]})

    return paginated_response(users, total, page, per_page)


# ─── Single user ──────────────────────────────────────────────
@admin_bp.route("/users/<user_id>", methods=["GET"])
@admin_required
def get_user(user_id):
    oid = mongo_id(user_id)
    user = mongo.db.users.find_one({"_id": oid}, {"password": 0}) if oid else None
    if not user:
        return error_response("User not found.", 404)
    user["id"] = str(user["_id"]); user.pop("_id", None)
    user["bookings"] = list(mongo.db.bookings.find({"user_id": user_id})
                                             .sort("booking_date", -1)
                                             .limit(20))
    for b in user["bookings"]:
        b["id"] = str(b["_id"]); b.pop("_id", None)
    return success_response(user)


# ─── Update user ──────────────────────────────────────────────
@admin_bp.route("/users/<user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    oid = mongo_id(user_id)
    if not oid or not mongo.db.users.find_one({"_id": oid}):
        return error_response("User not found.", 404)

    data = request.get_json(silent=True) or {}
    allowed = ["role", "is_active", "name", "phone"]
    updates = {}
    if "role" in data and data["role"] in ("admin", "user"):
        updates["role"] = data["role"]
    if "is_active" in data:
        updates["is_active"] = bool(data["is_active"])
    for field in ["name", "phone"]:
        if field in data:
            updates[field] = sanitise_str(str(data[field]), 200)

    updates["updated_at"] = utcnow()
    mongo.db.users.update_one({"_id": oid}, {"$set": updates})
    return success_response(message="User updated.")


# ─── Delete user ──────────────────────────────────────────────
@admin_bp.route("/users/<user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    oid = mongo_id(user_id)
    if not oid:
        return error_response("Invalid user ID.", 400)
    # Prevent self-deletion
    self_id = get_jwt_identity()
    if user_id == self_id:
        return error_response("Cannot delete your own account.", 400)
    result = mongo.db.users.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return error_response("User not found.", 404)
    return success_response(message="User deleted.")


# ─── All bookings ─────────────────────────────────────────────
@admin_bp.route("/bookings", methods=["GET"])
@admin_required
def list_all_bookings():
    page, per_page = get_pagination()
    query = {}

    status = request.args.get("status", "").strip()
    if status:
        query["status"] = status

    event_id = request.args.get("event_id", "").strip()
    if event_id:
        query["event_id"] = event_id

    total = mongo.db.bookings.count_documents(query)
    bks   = list(mongo.db.bookings.find(query)
                                  .sort("booking_date", -1)
                                  .skip((page - 1) * per_page)
                                  .limit(per_page))
    for b in bks:
        b["id"] = str(b["_id"]); b.pop("_id", None)

    return paginated_response(bks, total, page, per_page)


# ─── Update booking status ────────────────────────────────────
@admin_bp.route("/bookings/<booking_id>", methods=["PUT"])
@admin_required
def update_booking(booking_id):
    oid = mongo_id(booking_id)
    if not oid:
        return error_response("Invalid booking ID.", 400)
    data   = request.get_json(silent=True) or {}
    status = data.get("status", "")
    if status not in ("confirmed", "cancelled", "pending"):
        return error_response("Invalid status. Use: confirmed | cancelled | pending.", 422)
    mongo.db.bookings.update_one(
        {"_id": oid},
        {"$set": {"status": status, "updated_at": utcnow()}}
    )
    return success_response(message=f"Booking status updated to '{status}'.")


# ─── Admin event list (incl. drafts) ──────────────────────────
@admin_bp.route("/events", methods=["GET"])
@admin_required
def admin_events():
    page, per_page = get_pagination()
    query = {}

    status = request.args.get("status", "").strip()
    if status:
        query["status"] = status

    total  = mongo.db.events.count_documents(query)
    events = list(mongo.db.events.find(query)
                                 .sort("created_at", -1)
                                 .skip((page - 1) * per_page)
                                 .limit(per_page))
    for ev in events:
        ev["id"] = str(ev["_id"]); ev.pop("_id", None)

    return paginated_response(events, total, page, per_page)
