# src/main.py
import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from src.database.db import db  # SQLAlchemy() instance

# make relative imports work when launched by gunicorn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ENABLE_SECURITY_ROUTES = os.getenv("ENABLE_SECURITY_ROUTES") == "1"
ENABLE_DEV_LOGIN = os.getenv("ENABLE_DEV_LOGIN", "0") == "1"
ENABLE_TALISMAN = os.getenv("ENABLE_TALISMAN", "1") == "1"   # turn off with 0 if needed

# Recommended for prod: set to your Redis, e.g. redis://:pwd@host:6379/0
# Flask-Limiter will read this in the routes module when limiter.init_app(app) is called.
os.environ.setdefault("RATELIMIT_STORAGE_URI", os.getenv("RATELIMIT_STORAGE_URI", "memory://"))

def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )
    # Avoid 301/405 on paths that differ only by trailing slash
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
        JWT_COOKIE_SAMESITE="None",    # allow cross-site from www.getbrikk.com
        JWT_COOKIE_DOMAIN=os.getenv("JWT_COOKIE_DOMAIN", ".getbrikk.com"),
        JWT_COOKIE_CSRF_PROTECT=False,
    )
    JWTManager(app)

    # --- CORS ---
    allowed_origins = ["https://www.getbrikk.com", "https://getbrikk.com"]
    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                "expose_headers": [],
                "max_age": 600,
            }
        },
    )

    # --- Optional: Security headers / CSP (quiet jsdelivr warning & allow Stripe) ---
    if ENABLE_TALISMAN:
        try:
            from flask_talisman import Talisman
            csp = {
                "default-src": "'self'",
                "img-src": "'self' data:",
                "script-src": "'self'",
                "style-src": "'self' 'unsafe-inline'",
                # Allow API, Stripe, and (optional) jsdelivr for sourcemaps/future fetches
                "connect-src": "'self' https://api.getbrikk.com https://js.stripe.com https://hooks.stripe.com https://cdn.jsdelivr.net",
            }
            # Render terminates TLS at the edge; force_https keeps security posture consistent
            Talisman(app, force_https=True, content_security_policy=csp)
            app.logger.info("Talisman enabled")
        except Exception as e:
            app.logger.warning(f"Talisman not active ({e}). Set ENABLE_TALISMAN=0 or install flask-talisman.")

    # --- Health & root ---
    @app.route("/health", methods=["GET", "HEAD"])
    def health():
        return jsonify({"ok": True}), 200

    @app.route("/", methods=["GET", "HEAD"])
    def root():
        return jsonify({"ok": True, "service": "brikk-api"}), 200

    # --- Mount blueprints ---
    try:
        from src.routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix="/api")
        app.logger.info("Registered auth_bp at /api")
    except Exception as e:
        app.logger.exception(f"auth_bp import/registration failed: {e}")

    try:
        from src.routes.app import app_bp
        app.register_blueprint(app_bp, url_prefix="/api")
        app.logger.info("Registered app_bp at /api")
    except Exception as e:
        app.logger.exception(f"app_bp import/registration failed: {e}")

    try:
        # NOTE: agents_bp already has url_prefix="/api/v1/agents" INSIDE the blueprint.
        # Do NOT add another prefix here or you'll get /api/v1/api/v1/agents.
        from src.routes.agents import agents_bp, limiter as agents_limiter
        app.register_blueprint(agents_bp)
        try:
            agents_limiter.init_app(app)  # will use RATELIMIT_STORAGE_URI
        except Exception:
            pass  # already bound
        app.logger.info("Registered agents_bp at /api/v1/agents")
    except Exception as e:
        app.logger.exception(f"agents_bp import/registration failed: {e}")

    try:
        from src.routes.billing import billing_bp
        app.register_blueprint(billing_bp, url_prefix="/api")
        app.logger.info("Registered billing_bp at /api")
    except Exception as e:
        app.logger.exception(f"billing_bp import/registration failed: {e}")

    # Optional dev login (gated by ENABLE_DEV_LOGIN=1)
    if ENABLE_DEV_LOGIN:
        try:
            from src.routes.dev_login import dev_bp
            app.register_blueprint(dev_bp, url_prefix="/api")
            app.logger.info("Registered dev_login at /api")
        except Exception as e:
            app.logger.exception(f"dev_login import/registration failed: {e}")

    if ENABLE_SECURITY_ROUTES:
        try:
            from src.routes.security import security_bp
            app.register_blueprint(security_bp, url_prefix="/api")
            app.logger.info("Registered security_bp at /api (ENABLE_SECURITY_ROUTES=1)")
        except Exception as e:
            app.logger.exception(f"security_bp import/registration failed: {e}")
    else:
        app.logger.info("Skipped security_bp registration")

        # --- Debug endpoint: list all registered routes & methods ---
    @app.get("/api/_routes")
    def _routes():
        routes = []
        for r in app.url_map.iter_rules():
            methods = sorted([m for m in (r.methods or [])])
            routes.append({"rule": str(r.rule), "methods": methods})
        routes.sort(key=lambda x: x["rule"])
        return jsonify(routes)

    # --- Create tables ---
    with app.app_context():
        db.create_all()

    return app


# gunicorn entrypoint
app = create_app()
