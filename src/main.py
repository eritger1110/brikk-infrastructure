# src/main.py
import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Make relative imports work when launched by gunicorn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db import db  # SQLAlchemy() instance


def _opt_import(path, name):
    """Optional blueprint import that won’t crash if a module is missing."""
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None


# Optional blueprints
auth_bp = _opt_import("src.routes.auth", "auth_bp")
security_bp = _opt_import("src.routes.security", "security_bp")
# user_bp      = _opt_import("src.routes.user", "user_bp")
# provision_bp = _opt_import("src.routes.provision", "provision_bp")


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )

    # Avoid 308 redirects on preflight
    app.url_map.strict_slashes = False

    # ---------------- Core config ----------------
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # DB config
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_path = os.path.join(os.path.dirname(__file__), "database", "app.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db_url = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Bind SQLAlchemy to the app
    db.init_app(app)

    # ---------------- JWT cookies ----------------
    app.config.update(
        JWT_TOKEN_LOCATION=["cookies"],
        JWT_COOKIE_SECURE=True,        # HTTPS only
        JWT_COOKIE_SAMESITE="None",    # allow cross-site redirect from Netlify
        JWT_COOKIE_DOMAIN=os.getenv("JWT_COOKIE_DOMAIN", ".getbrikk.com"),
        JWT_COOKIE_CSRF_PROTECT=False,
    )
    jwt = JWTManager(app)

    # ---------------- CORS ----------------
    ALLOWED_ORIGINS = [
        "https://www.getbrikk.com",
        "https://getbrikk.com",
    ]
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": ALLOWED_ORIGINS,
                "supports_credentials": True,
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            }
        },
    )

    # ---------------- Health/root ----------------
    @app.route("/health", methods=["GET", "HEAD"])
    def health():
        return jsonify({"ok": True}), 200

    @app.route("/", methods=["GET", "HEAD"])
    def root():
        return jsonify({"ok": True, "service": "brikk-api"}), 200

    # Simple API ping for quick checks
    @app.route("/api/ping", methods=["GET"])
    def api_ping():
        return jsonify({"ok": True}), 200

    # Generic preflight (Flask-CORS will add headers)
    @app.route("/api/<path:_sub>", methods=["OPTIONS"])
    def api_cors_preflight(_sub):
        return ("", 204)

    # ---------------- Blueprints ----------------
    # Auth blueprint lives under /api/auth/*
    if auth_bp:
        app.register_blueprint(auth_bp, url_prefix="/api")

    # Any other blueprints (expecting their own prefixes)
    if security_bp:
        app.register_blueprint(security_bp, url_prefix="/api")
    # if user_bp:
    #     app.register_blueprint(user_bp, url_prefix="/api")
    # if provision_bp:
    #     app.register_blueprint(provision_bp, url_prefix="/api")

    # Ensure tables exist (sqlite dev/local)
    with app.app_context():
        db.create_all()

    return app


app = create_app()
