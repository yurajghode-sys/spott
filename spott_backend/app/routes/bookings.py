"""
app/routes/bookings.py
POST /api/bookings              — Create booking
GET  /api/bookings              — User's bookings
GET  /api/bookings/<id>         — Single booking
DELETE /api/bookings/<id>       — Cancel booking
GET  /api/bookings/<id>/ticket  — Ticket (QR) data
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import mongo, limiter
from app.models import make_booking
from app.utils.responses import success_response, error_response, paginated_response
from app.utils.helpers import get_pagination, mongo_id, gen_ref, utcnow, price_to_float
from app.middleware.auth import get_current_user
from bson import ObjectId

bookings_bp = Blueprint("bookings", __name__)


# ─── Create booking ───────────────────────────────────────────
@bookings_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit("20 per hour")
def create_booking():
    uid  = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    event_id    = data.get("event_id", "").strip()
    ticket_type = data.get("ticket_type", "general")
    quantity    = max(1, min(10, int(data.get("quantity", 1) or 1)))
    notes       = str(data.get("notes", ""))[:500]

    if not event_id:
        return error_response("event_id is required.", 422)
    if ticket_type not in ("general", "vip", "student"):
        ticket_type = "general"

    # ── Fetch event ───────────────────────────────────────────
    oid = mongo_id(event_id)
    event = mongo.db.events.find_one({"_id": oid}) if oid else None
    if not event or event.get("status") != "published":
        return error_response("Event not found or not available.", 404)

    # ── Capacity check ────────────────────────────────────────
    capacity = event.get("capacity", 0)
    booked   = event.get("booked_count", 0)
    if capacity and booked + quantity > capacity:
        return error_response(
            f"Only {max(0, capacity - booked)} seats remaining.", 400, "CAPACITY_EXCEEDED"
        )

    # ── Duplicate booking check ───────────────────────────────
    existing = mongo.db.bookings.find_one({
        "user_id":  uid,
        "event_id": event_id,
        "status":   "confirmed",
    })
    if existing:
        return error_response("You already have a confirmed booking for this event.", 409, "DUPLICATE_BOOKING")

    # ── Get user info ─────────────────────────────────────────
    user = get_current_user()
    attendee_name  = user.get("name", "")  if user else ""
    attendee_email = user.get("email", "") if user else ""

    # ── Amount ────────────────────────────────────────────────
    price_str  = event.get("price", "Free")
    unit_price = price_to_float(price_str)
    amount     = unit_price * quantity

    # ── Create booking ────────────────────────────────────────
    booking_ref = gen_ref("SPOTT")
    doc = make_booking(
        user_id=uid, event_id=event_id,
        booking_ref=booking_ref, ticket_type=ticket_type,
        quantity=quantity, amount_paid=amount,
        attendee_name=attendee_name, attendee_email=attendee_email,
    )
    doc["notes"] = notes
    doc["event_title"]    = event.get("title", "")
    doc["event_date"]     = event.get("date", "")
    doc["event_time"]     = event.get("time", "")
    doc["event_location"] = event.get("location", "")
    doc["event_emoji"]    = event.get("emoji", "🎉")

    result = mongo.db.bookings.insert_one(doc)
    booking_id = str(result.inserted_id)

    # ── Update event booked count ──────────────────────────────
    mongo.db.events.update_one(
        {"_id": oid},
        {"$inc": {"booked_count": quantity}}
    )

    # ── Update user stats ──────────────────────────────────────
    mongo.db.users.update_one(
        {"_id": ObjectId(uid)},
        {"$inc": {"bookings_count": 1, "points": 100}}
    )

    doc["id"] = booking_id
    doc.pop("_id", None)

    return success_response({
        "booking": doc,
        "message": f"🎉 You're in! Booking confirmed.",
        "qr_data": doc.get("qr_data", ""),
    }, "Booking confirmed!", 201)


# ─── List user bookings ───────────────────────────────────────
@bookings_bp.route("", methods=["GET"])
@jwt_required()
def list_bookings():
    uid        = get_jwt_identity()
    page, per_page = get_pagination()

    status = request.args.get("status", "confirmed")
    query  = {"user_id": uid}
    if status and status != "all":
        query["status"] = status

    total = mongo.db.bookings.count_documents(query)
    bks   = list(mongo.db.bookings.find(query)
                                  .sort("booking_date", -1)
                                  .skip((page - 1) * per_page)
                                  .limit(per_page))
    for b in bks:
        b["id"] = str(b["_id"]); b.pop("_id", None)

    return paginated_response(bks, total, page, per_page)


# ─── Single booking ───────────────────────────────────────────
@bookings_bp.route("/<booking_id>", methods=["GET"])
@jwt_required()
def get_booking(booking_id):
    uid = get_jwt_identity()
    bk  = mongo.db.bookings.find_one(
        {"booking_ref": booking_id, "user_id": uid}
    )
    if not bk:
        oid = mongo_id(booking_id)
        bk  = mongo.db.bookings.find_one({"_id": oid, "user_id": uid}) if oid else None
    if not bk:
        return error_response("Booking not found.", 404)
    bk["id"] = str(bk["_id"]); bk.pop("_id", None)
    return success_response(bk)


# ─── Cancel booking ───────────────────────────────────────────
@bookings_bp.route("/<booking_id>", methods=["DELETE"])
@jwt_required()
def cancel_booking(booking_id):
    uid = get_jwt_identity()
    oid = mongo_id(booking_id)
    bk  = mongo.db.bookings.find_one({"_id": oid, "user_id": uid}) if oid else None
    if not bk:
        return error_response("Booking not found.", 404)
    if bk.get("status") == "cancelled":
        return error_response("Booking is already cancelled.", 400)

    mongo.db.bookings.update_one(
        {"_id": oid},
        {"$set": {"status": "cancelled", "updated_at": utcnow()}}
    )
    # Return seat to pool
    mongo.db.events.update_one(
        {"_id": mongo_id(bk["event_id"])},
        {"$inc": {"booked_count": -bk.get("quantity", 1)}}
    )
    return success_response(message="Booking cancelled.")


# ─── Get ticket / QR data ─────────────────────────────────────
@bookings_bp.route("/<booking_id>/ticket", methods=["GET"])
@jwt_required()
def get_ticket(booking_id):
    uid = get_jwt_identity()
    bk  = mongo.db.bookings.find_one({"booking_ref": booking_id, "user_id": uid})
    if not bk:
        oid = mongo_id(booking_id)
        bk  = mongo.db.bookings.find_one({"_id": oid, "user_id": uid}) if oid else None
    if not bk:
        return error_response("Ticket not found.", 404)

    user = get_current_user()
    ticket = {
        "booking_ref":    bk.get("booking_ref"),
        "event_title":    bk.get("event_title"),
        "event_date":     bk.get("event_date"),
        "event_time":     bk.get("event_time"),
        "event_location": bk.get("event_location"),
        "event_emoji":    bk.get("event_emoji", "🎉"),
        "ticket_type":    bk.get("ticket_type", "General"),
        "quantity":       bk.get("quantity", 1),
        "amount_paid":    bk.get("amount_paid", 0),
        "attendee_name":  bk.get("attendee_name"),
        "attendee_email": bk.get("attendee_email"),
        "status":         bk.get("status"),
        "qr_data":        bk.get("qr_data", ""),
        "booked_on":      bk.get("booking_date"),
    }
    return success_response(ticket)
