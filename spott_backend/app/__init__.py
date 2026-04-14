import os
from flask import Flask, jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

# Extensions
mongo = PyMongo()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_name: str = None) -> Flask:
    print("🔥 create_app() is running")

    app = Flask(__name__, instance_relative_config=True)

    # ================= CONFIG =================
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/spott_db")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

    # ================= INIT =================
    mongo.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    CORS(app)

    # ================= BASIC ROUTES =================
    @app.route("/")
    def home():
        return "HOME WORKING"

    @app.route("/test")
    def test():
        return "WORKING"

    @app.route("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "service": "spott-api"
        })

    # ================= SAFE BLUEPRINT LOADING =================
    # 🔥 This prevents app crash if any file has error

    try:
        from app.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        print("✅ auth_bp loaded")
    except Exception as e:
        print("❌ auth_bp error:", e)

    try:
        from app.routes.events import events_bp
        app.register_blueprint(events_bp, url_prefix="/api/events")
        print("✅ events_bp loaded")
    except Exception as e:
        print("❌ events_bp error:", e)

    try:
        from app.routes.bookings import bookings_bp
        app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
        print("✅ bookings_bp loaded")
    except Exception as e:
        print("❌ bookings_bp error:", e)

    try:
        from app.routes.users import users_bp
        app.register_blueprint(users_bp, url_prefix="/api/users")
        print("✅ users_bp loaded")
    except Exception as e:
        print("❌ users_bp error:", e)

    try:
        from app.routes.admin import admin_bp
        app.register_blueprint(admin_bp, url_prefix="/api/admin")
        print("✅ admin_bp loaded")
    except Exception as e:
        print("❌ admin_bp error:", e)

    try:
        from app.routes.upload import upload_bp
        app.register_blueprint(upload_bp, url_prefix="/api/upload")
        print("✅ upload_bp loaded")
    except Exception as e:
        print("❌ upload_bp error:", e)

    try:
        from app.routes.search import search_bp
        app.register_blueprint(search_bp, url_prefix="/api/search")
        print("✅ search_bp loaded")
    except Exception as e:
        print("❌ search_bp error:", e)

    return app