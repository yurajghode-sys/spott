"""
app/routes/events.py
GET  /api/events              — List events (paginated, filtered)
GET  /api/events/trending     — Trending events
GET  /api/events/<id>         — Single event detail
POST /api/events              — Create event (admin)
PUT  /api/events/<id>         — Update event (admin)
DELETE /api/events/<id>       — Delete event (admin)
GET  /api/events/categories   — All categories
POST /api/events/<id>/review  — Submit review/feedback
GET  /api/events/<id>/bookings — Event bookings (admin)
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from app import mongo, limiter
from app.models import make_event
from app.utils.responses import success_response, error_response, paginated_response
from app.utils.helpers import get_pagination, mongo_id, sanitise_str, utcnow
from app.middleware.auth import admin_required, get_current_user
from bson import ObjectId
import re

events_bp = Blueprint("events", __name__)

CATEGORIES = ["Music", "Tech", "Startup", "Art", "Food", "Sports", "Comedy", "Wellness", "Education"]


# ─── List events ─────────────────────────────────────────────
@events_bp.route("", methods=["GET"])
def list_events():
    page, per_page = get_pagination()
    query = {"status": "published"}

    # ── Filters ───────────────────────────────────────────────
    category = request.args.get("category", "").strip()
    if category and category.lower() != "all":
        query["category"] = {"$regex": re.escape(category), "$options": "i"}

    event_type = request.args.get("type", "").strip()  # free | paid
    if event_type in ("free", "paid"):
        query["type"] = event_type

    location = request.args.get("location", "").strip()
    if location:
        query["location"] = {"$regex": re.escape(location), "$options": "i"}

    date_filter = request.args.get("date", "").strip()
    if date_filter:
        query["datetime_iso"] = {"$gte": date_filter}

    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    if min_price is not None or max_price is not None:
        price_q = {}
        if min_price is not None: price_q["$gte"] = min_price
        if max_price is not None: price_q["$lte"] = max_price
        query["price_value"] = price_q

    # ── Sort ──────────────────────────────────────────────────
    sort_by = request.args.get("sort", "newest")
    sort_map = {
        "newest":   [("created_at", -1)],
        "oldest":   [("created_at",  1)],
        "price_asc":  [("price_value",  1)],
        "price_desc": [("price_value", -1)],
        "date":     [("datetime_iso",  1)],
    }
    sort = sort_map.get(sort_by, [("created_at", -1)])

    total  = mongo.db.events.count_documents(query)
    events = list(mongo.db.events.find(query).sort(sort)
                                             .skip((page - 1) * per_page)
                                             .limit(per_page))

    # Enrich with booking availability
    for ev in events:
        ev["id"] = str(ev["_id"])
        ev.pop("_id", None)
        booked = ev.get("booked_count", 0)
        cap    = ev.get("capacity", 0)
        ev["is_full"]    = cap > 0 and booked >= cap
        ev["seats_left"] = max(0, cap - booked) if cap > 0 else None

    return paginated_response(events, total, page, per_page)


# ─── Trending events ──────────────────────────────────────────
@events_bp.route("/trending", methods=["GET"])
def trending_events():
    events = list(mongo.db.events.find({"status": "published"})
                                 .sort("booked_count", -1)
                                 .limit(6))
    for ev in events:
        ev["id"] = str(ev["_id"]); ev.pop("_id", None)
    return success_response(events)


# ─── Categories ───────────────────────────────────────────────
@events_bp.route("/categories", methods=["GET"])
def categories():
    # Return categories with counts
    pipeline = [
        {"$match": {"status": "published"}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    result = list(mongo.db.events.aggregate(pipeline))
    cats = [{"name": r["_id"], "count": r["count"]} for r in result if r["_id"]]
    return success_response(cats)


# ─── Single event ─────────────────────────────────────────────
@events_bp.route("/<event_id>", methods=["GET"])
def get_event(event_id):
    oid = mongo_id(event_id)
    event = mongo.db.events.find_one({"_id": oid}) if oid else None

    # Also try slug
    if not event:
        event = mongo.db.events.find_one({"slug": event_id})

    if not event:
        return error_response("Event not found.", 404)

    event["id"] = str(event["_id"])
    event.pop("_id", None)

    # Check if current user has bookings for this event
    event["user_booked"] = False
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            bk = mongo.db.bookings.find_one({
                "user_id": uid, "event_id": event["id"], "status": "confirmed"
            })
            event["user_booked"] = bool(bk)
    except Exception:
        pass

    # Reviews / feedback
    reviews = list(mongo.db.reviews.find({"event_id": event["id"]}).sort("created_at", -1).limit(10))
    for r in reviews:
        r["id"] = str(r["_id"]); r.pop("_id", None)
    event["reviews"] = reviews
    event["avg_rating"] = _avg_rating(event["id"])

    booked = event.get("booked_count", 0)
    cap    = event.get("capacity", 0)
    event["is_full"]    = cap > 0 and booked >= cap
    event["seats_left"] = max(0, cap - booked) if cap > 0 else None

    return success_response(event)


# ─── Create event (admin) ─────────────────────────────────────
@events_bp.route("", methods=["POST"])
@jwt_required()
def create_event():
    uid  = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    if not sanitise_str(data.get("title", ""), 200):
        return error_response("Event title is required.", 422)

    doc = make_event(data, organiser_id=uid)
    result = mongo.db.events.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)

    return success_response(doc, "Event created successfully!", 201)


# ─── Update event (admin) ─────────────────────────────────────
@events_bp.route("/<event_id>", methods=["PUT"])
@admin_required
def update_event(event_id):
    oid = mongo_id(event_id)
    if not oid or not mongo.db.events.find_one({"_id": oid}):
        return error_response("Event not found.", 404)

    data = request.get_json(silent=True) or {}
    allowed = ["title", "description", "category", "date", "time", "datetime_iso",
               "location", "price", "emoji", "image_url", "capacity", "status",
               "badge", "tags"]
    updates = {k: data[k] for k in allowed if k in data}

    if "price" in updates:
        from app.utils.helpers import price_to_float
        updates["price_value"] = price_to_float(updates["price"])
        updates["type"] = "free" if updates["price_value"] == 0 else "paid"
    if "title" in updates:
        from app.models import _slugify
        updates["slug"] = _slugify(updates["title"])

    updates["updated_at"] = utcnow()
    mongo.db.events.update_one({"_id": oid}, {"$set": updates})

    updated = mongo.db.events.find_one({"_id": oid})
    updated["id"] = str(updated["_id"]); updated.pop("_id", None)
    return success_response(updated, "Event updated.")


# ─── Delete event (admin) ─────────────────────────────────────
@events_bp.route("/<event_id>", methods=["DELETE"])
@admin_required
def delete_event(event_id):
    oid = mongo_id(event_id)
    if not oid:
        return error_response("Invalid event ID.", 400)
    result = mongo.db.events.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return error_response("Event not found.", 404)
    # Cancel related bookings
    mongo.db.bookings.update_many(
        {"event_id": event_id},
        {"$set": {"status": "cancelled", "updated_at": utcnow()}}
    )
    return success_response(message="Event deleted.")


# ─── Submit review ────────────────────────────────────────────
@events_bp.route("/<event_id>/review", methods=["POST"])
@jwt_required()
def submit_review(event_id):
    uid  = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    rating  = data.get("rating", 0)
    comment = sanitise_str(data.get("comment", ""), 1000)

    if not (1 <= int(rating) <= 5):
        return error_response("Rating must be between 1 and 5.", 422)

    # Ensure user attended the event
    bk = mongo.db.bookings.find_one({"user_id": uid, "event_id": event_id, "status": "confirmed"})
    if not bk:
        return error_response("You must have a confirmed booking to leave a review.", 403)

    # Prevent duplicate
    existing = mongo.db.reviews.find_one({"user_id": uid, "event_id": event_id})
    if existing:
        return error_response("You already submitted a review for this event.", 409)

    user = get_current_user()
    doc = {
        "user_id":    uid,
        "event_id":   event_id,
        "rating":     int(rating),
        "comment":    comment,
        "user_name":  user.get("name", "Anonymous") if user else "Anonymous",
        "user_avatar": user.get("avatar_url", "") if user else "",
        "created_at": utcnow(),
    }
    mongo.db.reviews.insert_one(doc)
    return success_response(message=f"Thanks for your {rating}★ review! 🎉", status_code=201)


# ─── Event bookings (admin) ───────────────────────────────────
@events_bp.route("/<event_id>/bookings", methods=["GET"])
@admin_required
def event_bookings(event_id):
    page, per_page = get_pagination()
    query  = {"event_id": event_id}
    total  = mongo.db.bookings.count_documents(query)
    bks    = list(mongo.db.bookings.find(query).sort("booking_date", -1)
                                               .skip((page - 1) * per_page)
                                               .limit(per_page))
    for b in bks:
        b["id"] = str(b["_id"]); b.pop("_id", None)
    return paginated_response(bks, total, page, per_page)


# ─── Helper ───────────────────────────────────────────────────
def _avg_rating(event_id: str) -> float:
    pipeline = [
        {"$match": {"event_id": event_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}}},
    ]
    result = list(mongo.db.reviews.aggregate(pipeline))
    return round(result[0]["avg"], 1) if result else 0.0
