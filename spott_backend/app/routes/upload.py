"""app/routes/upload.py — Image upload endpoint"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.middleware.auth import admin_required
from app.utils.responses import success_response, error_response
from app.utils.helpers import save_image

upload_bp = Blueprint("upload", __name__)


@upload_bp.route("/image", methods=["POST"])
@admin_required
def upload_image():
    if "file" not in request.files:
        return error_response("No file provided.", 422)
    file = request.files["file"]
    if file.filename == "":
        return error_response("No file selected.", 422)
    subfolder = request.form.get("folder", "events")
    try:
        url = save_image(file, subfolder)
        return success_response({"url": url}, "Image uploaded successfully.", 201)
    except ValueError as e:
        return error_response(str(e), 422)
    except Exception as e:
        return error_response("Upload failed.", 500)
