# src/main.py
import os, sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# make relative imports work when launched by gunicorn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db import db  # SQLAlchemy() instance


def _opt_import(path, name):
    """Optional import that won’t crash if a module is missing."""
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None


# Blueprints
auth_bp     = _opt_import("src.routes.auth", "auth_bp")
security_bp = _opt_import("src.routes.security", "security_bp")  # legacy (disabled by default)

# Gate the legacy routes behind an env var
ENABLE_SECURITY_ROUTES = os.getenv("ENABLE_SECURITY_ROUTES") == "1"


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )
    app.url_map.strict_slashes = False

    # --- Core config ---
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # --- DB config ---
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_path = os.path.join(os.path.dirname(__file__), "database", "app.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db_url = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # --- JWT cookies ---
    app.config.update(
        JWT_TOKEN_LOCATION=["cookies"],
        JWT_COOKIE_SECURE=True,        # HTTPS only
        JWT_COOKIE_SAMESITE="None",    # allow cross-site redirect from Netlify
        JWT_COOKIE_DOMAIN=os.getenv("JWT_COOKIE_DOMAIN", ".getbrikk.com"),
        JWT_COOKIE_CSRF_PROTECT=False,
    )
    JWTManager(app)

    # --- CORS (apply to ALL routes) ---
    allowed = ["https://www.getbrikk.com", "https://getbrikk.com"]
    CORS(
        app,
        supports_credentials=True,
        resources={r"/*": {
            "origins": allowed,
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "expose_headers": [],
            "max_age": 600,
        }},
    )

    # --- Health & root ---
    @app.route("/health", methods=["GET", "HEAD"])
    def health():
        return jsonify({"ok": True}), 200

    @app.route("/", methods=["GET", "HEAD"])
    def root():
        return jsonify({"ok": True, "service": "brikk-api"}), 200

    # --- Mount blueprints under /api ---
    if auth_bp:
        app.register_blueprint(auth_bp, url_prefix="/api")
        print("Registered auth_bp at /api")
    else:
        print("auth_bp missing — nothing mounted at /api/auth")

    # Legacy security routes are OFF unless explicitly enabled
    if security_bp and ENABLE_SECURITY_ROUTES:
        app.register_blueprint(security_bp, url_prefix="/api")
        print("Registered security_bp at /api (ENABLE_SECURITY_ROUTES=1)")
    else:
        print("Skipped security_bp registration")

    # --- Preflight for ANY /api/* route ---
    @app.route("/api/<path:_sub>", methods=["OPTIONS"])
    def api_preflight(_sub):
        # Flask-CORS will attach the Access-Control-* headers
        return ("", 204)

    # Ensure tables exist (sqlite dev)
    with app.app_context():
        db.create_all()

    return app


app = create_app()
