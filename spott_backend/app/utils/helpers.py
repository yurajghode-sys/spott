"""app/utils/helpers.py — Common utilities"""
import re, os, uuid, secrets, string, hashlib
from datetime import datetime, timezone
from flask import request, current_app
from werkzeug.utils import secure_filename
from bson import ObjectId

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def gen_ref(prefix: str = "SPOTT", length: int = 8) -> str:
    """Generate a unique booking/confirmation reference like SPOTT-AB12XY98."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(length))
    return f"{prefix}-{suffix}"


def allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_image(file_obj, subfolder: str = "events") -> str:
    """Save an uploaded image and return its URL path."""
    if not file_obj or not allowed_image(file_obj.filename):
        raise ValueError("Invalid image file. Allowed: png, jpg, jpeg, gif, webp")
    ext = file_obj.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    file_obj.save(os.path.join(folder, filename))
    return f"/static/uploads/{subfolder}/{filename}"


def get_pagination():
    """Extract page / per_page from query string."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = min(100, max(1, int(request.args.get("per_page", 12))))
    except (ValueError, TypeError):
        per_page = 12
    return page, per_page


def sanitise_str(value, max_len: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_len]


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, str(email or "")))


def is_valid_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-\(\)\+]", "", str(phone or ""))
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def mongo_id(id_str: str):
    """Convert string to ObjectId safely."""
    try:
        return ObjectId(str(id_str))
    except Exception:
        return None


def price_to_float(price_str: str) -> float:
    """Convert '₹2,499' or 'Free' to float."""
    if not price_str or str(price_str).lower() in ("free", "0", ""):
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", str(price_str))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def generate_qr_data(booking_ref: str, event_title: str, user_email: str) -> str:
    """Generate QR code data string."""