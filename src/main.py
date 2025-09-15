# src/main.py
import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Make relative imports work when launched by gunicorn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db import db


def _opt_import(path, name):
    """Import a blueprint if it exists; return None if not."""
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None


# Optional blueprints (won't crash if a module is absent)
auth_bp = _opt_import("src.routes.auth", "auth_bp")          # already has url_prefix="/api/auth"
security_bp = _opt_import("src.routes.security", "security_bp")  # no prefix in the file


def create_app() -> Flask:
    app = Flask(__name__)

    # --- Core config ---
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Database URL (Render typically sets DATABASE_URL). Fallback to sqlite file.
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_path = os.path.join(os.path.dirname(__file__), "database", "app.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db_url = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- JWT Cookies ---
    # We issue JWTs via cookies only (so the success page can set a session cross-site).
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_COOKIE_SECURE"] = True          # HTTPS only
    app.config["JWT_COOKIE_SAMESITE"] = "None"      # allow Netlify → API cross-site
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False   # keep simple for now

    # Only set cookie domain if provided (e.g. ".getbrikk.com"). If empty, the cookie is host-only.
    cookie_domain = (os.getenv("JWT_COOKIE_DOMAIN") or "").strip()
    if cookie_domain:
        app.config["JWT_COOKIE_DOMAIN"] = cookie_domain

    # --- CORS ---
    # Allowed origins (add more via CORS_ORIGINS env, comma-separated)
    allowed_origins = [
        "https://app.getbrikk.com",
        "https://www.getbrikk.com",
        "https://getbrikk.com",
    ]
    extra = (os.getenv("CORS_ORIGINS") or "").strip()
    if extra:
        for origin in extra.split(","):
            origin = origin.strip()
            if origin and origin not in allowed_origins:
                allowed_origins.append(origin)

    CORS(app, supports_credentials=True, origins=allowed_origins)

    # Init extensions
    JWTManager(app)
    db.init_app(app)

    # Create tables if we're on sqlite (safe no-op for Postgres)
    with app.app_context():
        if db_url.startswith("sqlite:///"):
            db.create_all()

    # --- Health & root probes ---
    @app.route("/health", methods=["GET", "HEAD"])
    def health():
        return jsonify({"ok": True}), 200

    @app.route("/", methods=["GET", "HEAD"])
    def root():
        return jsonify({"ok": True, "service": "brikk-api"}), 200

    # --- Blueprints ---
    # auth_bp already defines url_prefix="/api/auth" in src/routes/auth.py → register with NO extra prefix
    if auth_bp:
        app.register_blueprint(auth_bp)

    # security_bp defines routes like "/auth/complete-signup" → mount it under "/api"
    if security_bp:
        app.register_blueprint(security_bp, url_prefix="/api")

    # Optional extra health under /api for convenience
    @app.route("/api/health", methods=["GET", "HEAD"])
    def api_health():
        return jsonify({"ok": True}), 200

    return app


app = create_app()
