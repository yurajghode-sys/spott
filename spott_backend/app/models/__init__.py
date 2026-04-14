"""
app/models/__init__.py — MongoDB collection schemas & validators
These are NOT ORM models — they provide schema validation helpers
and factory functions for consistent document structure.
"""

from datetime import datetime, timezone
import re


def utcnow():
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────────────────────
USER_SCHEMA = {
    "name":       str,
    "email":      str,
    "phone":      str,
    "password":   str,      # bcrypt hash
    "role":       str,      # "user" | "admin"
    "avatar_url": str,
    "bio":        str,
    "interests":  list,
    "is_active":  bool,
    "created_at": datetime,
    "updated_at": datetime,
    "last_login": datetime,
    "bookings_count": int,
    "saved_events": list,   # list of event _id strings
    "points": int,
}


def make_user(name, email, password_hash, role="user", phone=""):
    return {
        "name":          name.strip(),
        "email":         email.lower().strip(),
        "phone":         phone.strip(),
        "password":      password_hash,
        "role":          role,
        "avatar_url":    "",
        "bio":           "",
        "interests":     [],
        "is_active":     True,
        "created_at":    utcnow(),
        "updated_at":    utcnow(),
        "last_login":    None,
        "bookings_count": 0,
        "saved_events":  [],
        "points":        50,    # welcome points
    }


# ─────────────────────────────────────────────────────────────
# EVENT
# ─────────────────────────────────────────────────────────────
EVENT_SCHEMA = {
    "title":        str,
    "slug":         str,
    "description":  str,
    "category":     str,
    "date":         str,      # "Jan 5, 2026"
    "time":         str,      # "9:00 AM"
    "datetime_iso": str,      # ISO 8601 for sorting
    "location":     str,
    "price":        str,      # "₹2,499" or "Free"
    "price_value":  float,    # numeric for filtering
    "type":         str,      # "free" | "paid"
    "emoji":        str,
    "image_url":    str,
    "capacity":     int,
    "booked_count": int,
    "status":       str,      # "published" | "draft" | "cancelled"
    "badge":        str,      # "free" | "paid" | "live"
    "tags":         list,
    "organiser_id": str,
    "created_at":   datetime,
    "updated_at":   datetime,
}


def make_event(data: dict, organiser_id: str = "") -> dict:
    from app.utils.helpers import price_to_float, sanitise_str
    price_str = sanitise_str(data.get("price", "Free"), 50)
    return {
        "title":        sanitise_str(data.get("title", ""), 200),
        "slug":         _slugify(data.get("title", "")),
        "description":  sanitise_str(data.get("description", ""), 3000),
        "category":     sanitise_str(data.get("category", ""), 80),
        "date":         sanitise_str(data.get("date", ""), 50),
        "time":         sanitise_str(data.get("time", ""), 30),
        "datetime_iso": sanitise_str(data.get("datetime_iso", ""), 50),
        "location":     sanitise_str(data.get("location", ""), 300),
        "price":        price_str,
        "price_value":  price_to_float(price_str),
        "type":         "free" if price_to_float(price_str) == 0 else "paid",
        "emoji":        sanitise_str(data.get("emoji", "🎉"), 10),
        "image_url":    sanitise_str(data.get("image_url", ""), 500),
        "capacity":     int(data.get("capacity", 0) or 0),
        "booked_count": 0,
        "status":       data.get("status", "published"),
        "badge":        data.get("badge", ""),
        "tags":         data.get("tags", []),
        "organiser_id": str(organiser_id),
        "created_at":   utcnow(),
        "updated_at":   utcnow(),
    }


# ─────────────────────────────────────────────────────────────
# BOOKING
# ─────────────────────────────────────────────────────────────
BOOKING_SCHEMA = {
    "user_id":      str,
    "event_id":     str,
    "booking_ref":  str,
    "ticket_type":  str,    # "general" | "vip" | "student"
    "quantity":     int,
    "amount_paid":  float,
    "status":       str,    # "confirmed" | "cancelled" | "pending"
    "booking_date": datetime,
    "qr_data":      str,
    "attendee_name": str,
    "attendee_email": str,
    "notes":        str,
}


def make_booking(user_id, event_id, booking_ref, ticket_type="general",
                 quantity=1, amount_paid=0.0, attendee_name="", attendee_email=""):
    from app.utils.helpers import generate_qr_data
    return {
        "user_id":       str(user_id),
        "event_id":      str(event_id),
        "booking_ref":   booking_ref,
        "ticket_type":   ticket_type,
        "quantity":      quantity,
        "amount_paid":   amount_paid,
        "status":        "confirmed",
        "booking_date":  utcnow(),
        "qr_data":       generate_qr_data(booking_ref, "", attendee_email),
        "attendee_name": attendee_name,
        "attendee_email": attendee_email,
        "notes":         "",
        "updated_at":    utcnow(),
    }


# ─────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────
def _slugify(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80]
