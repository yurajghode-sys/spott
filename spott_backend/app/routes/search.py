"""app/routes/search.py — Full-text event search"""
from flask import Blueprint, request
from app import mongo
from app.utils.responses import success_response
from app.utils.helpers import sanitise_str

search_bp = Blueprint("search", __name__)


@search_bp.route("", methods=["GET"])
def search():
    q = sanitise_str(request.args.get("q", ""), 200)
    if not q or len(q) < 2:
        return success_response([], "Search query too short.")

    # Text index search
    try:
        results = list(mongo.db.events.find(
            {"$text": {"$search": q}, "status": "published"},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(20))
    except Exception:
        # Fallback: regex search
        import re
        pattern = re.escape(q)
        results = list(mongo.db.events.find({
            "status": "published",
            "$or": [
                {"title":    {"$regex": pattern, "$options": "i"}},
                {"location": {"$regex": pattern, "$options": "i"}},
                {"category": {"$regex": pattern, "$options": "i"}},
                {"description": {"$regex": pattern, "$options": "i"}},
            ]
        }).limit(20))

    for r in results:
        r["id"] = str(r["_id"])
        r.pop("_id", None)
        r.pop("score", None)

    # Suggestions (event titles matching prefix)
    suggestions = [r["title"] for r in results[:6]]

    return success_response({
        "results":     results,
        "suggestions": suggestions,
        "total":       len(results),
        "query":       q,
    })
