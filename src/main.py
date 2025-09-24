# src/main.py
import os, sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# make relative imports work when launched by gunicorn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db import db  # SQLAlchemy() instance

# NEW: security headers (CSP/HSTS) + request-id
try:
    from flask_talisman import Talisman
except Exception:
    Talisman = None  # optional; app still runs without it
from src.services.security import attach_request_id

# NEW: agents API blueprint
from src.routes.agents import agents_bp

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
        JWT_COOKIE_SAMESITE="None",    # allow cross-site from Netlify
        JWT_COOKIE_DOMAIN=os.getenv("JWT_COOKIE_DOMAIN", ".getbrikk.com"),
        JWT_COOKIE_CSRF_PROTECT=False,
    )
    JWTManager(app)

    # --- CORS (apply to ALL routes) ---
    allowed = ["https://www.getbrikk.com", "https://getbrikk.com"]
    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/*": {
                "origins": allowed,
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                "expose_headers": [],
                "max_age": 600,
            }
        },
    )

    # --- Security headers (optional but recommended) ---
    if Talisman:
        csp = {
            "default-src": "'self'",
            "img-src": "'self' data:",
            "script-src": "'self'",
            "style-src": "'self' 'unsafe-inline'",
            "connect-src": "'self'",
        }
        # In Render/HTTPS you can set force_https=True. Keeping False to avoid local dev issues.
        Talisman(app, force_https=False, content_security_policy=csp)

    # --- Request ID for every request (helps logs/tracing) ---
    attach_request_id(app)

    # --- Health & root ---
    @app.route("/health", methods=["GET", "HEAD"])
    def health():
        return jsonify({"ok": True}), 200

    @app.route("/", methods=["GET", "HEAD"])
    def root():
        return jsonify({"ok": True, "service": "brikk-api"}), 200

    # --- Mount blueprints under /api ---
    try:
        from src.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix="/api")
        print("Registered auth_bp at /api"); app.logger.info("Registered auth_bp at /api")
    except Exception as e:
        print(f"auth_bp import/registration failed: {e}")
        app.logger.exception(f"auth_bp import/registration failed: {e}")
        print("auth_bp missing — nothing mounted at /api/auth")

    try:
        from src.routes.app import app_bp
        app.register_blueprint(app_bp, url_prefix="/api")
        print("Registered app_bp at /api"); app.logger.info("Registered app_bp at /api")
    except Exception as e:
        print(f"app_bp import/registration failed: {e}")
        app.logger.exception(f"app_bp import/registration failed: {e}")

    # NEW: Agents registry (mounted at /api/v1/agents by the blueprint itself)
    try:
        # NOTE: agents_bp already has url_prefix="/api/v1/agents"; register without extra prefix.
        app.register_blueprint(agents_bp)
        print("Registered agents_bp at /api/v1/agents"); app.logger.info("Registered agents_bp at /api/v1/agents")
    except Exception as e:
        print(f"agents_bp import/registration failed: {e}")
        app.logger.exception(f"agents_bp import/registration failed: {e}")

    # NEW: Billing routes (Stripe customer portal)
    try:
        from src.routes.billing import billing_bp
        app.register_blueprint(billing_bp, url_prefix="/api")
        print("Registered billing_bp at /api"); app.logger.info("Registered billing_bp at /api")
    except Exception as e:
        print(f"billing_bp import/registration failed: {e}")
        app.logger.exception(f"billing_bp import/registration failed: {e}")

    # Legacy security routes are OFF unless explicitly enabled
    if ENABLE_SECURITY_ROUTES:
        try:
            from src.routes.security import security_bp
            app.register_blueprint(security_bp, url_prefix="/api")
            print("Registered security_bp at /api (ENABLE_SECURITY_ROUTES=1)")
        except Exception as e:
            print(f"security_bp import/registration failed: {e}")
            app.logger.exception(f"security_bp import/registration failed: {e}")
    else:
        print("Skipped security_bp registration")

    # --- Preflight for ANY /api/* route (CORS) ---
    @app.route("/api/<path:_sub>", methods=["OPTIONS"])
    def api_preflight(_sub):
        return ("", 204)  # Flask-CORS adds headers

    # Ensure tables exist (including the new audit_logs)
    with app.app_context():
        # Import here so create_all can see the models
        from src.models.audit_log import AuditLog  # noqa: F401
        db.create_all()

    return app


app = create_app()
