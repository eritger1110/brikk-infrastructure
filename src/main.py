# src/main.py
import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from src.database.db import db  # global SQLAlchemy() instance

# Make relative imports work when launched by gunicorn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ENABLE_SECURITY_ROUTES = os.getenv("ENABLE_SECURITY_ROUTES") == "1"
ENABLE_DEV_LOGIN = os.getenv("ENABLE_DEV_LOGIN", "0") == "1"
ENABLE_TALISMAN = os.getenv("ENABLE_TALISMAN", "1") == "1"  # set 0 to disable

# Flask-Limiter storage (agents blueprint calls limiter.init_app(app))
os.environ.setdefault("RATELIMIT_STORAGE_URI", os.getenv("RATELIMIT_STORAGE_URI", "memory://"))


def _normalize_db_url(url: str) -> str:
    """
    Normalize DATABASE_URL so SQLAlchemy loads the right DBAPI.
    We standardize on psycopg v3 driver ('+psycopg'), which supports Python 3.13.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg://" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


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
    else:
        db_url = _normalize_db_url(db_url)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    db.init_app(app)

    # --- JWT cookies ---
    app.config.update(
        JWT_TOKEN_LOCATION=["cookies"],
        JWT_COOKIE_SECURE=True,
        JWT_COOKIE_SAMESITE="None",
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

    # --- Security headers / CSP (quiet jsdelivr warnings & allow Stripe) ---
    if ENABLE_TALISMAN:
        try:
            from flask_talisman import Talisman
            csp = {
                "default-src": "'self'",
                "img-src": "'self' data:",
                "script-src": "'self'",
                "style-src": "'self' 'unsafe-inline'",
                "connect-src": (
                    "'self' https://api.getbrikk.com "
                    "https://js.stripe.com https://hooks.stripe.com "
                    "https://cdn.jsdelivr.net"
                ),
            }
            Talisman(app, force_https=True, content_security_policy=csp)
            app.logger.info("Talisman enabled")
        except Exception as e:
            app.logger.warning(f"Talisman not active ({e}). Set ENABLE_TALISMAN=0 or add flask-talisman.")

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
        # agents_bp already defines url_prefix="/api/v1/agents"
        from src.routes.agents import agents_bp, limiter as agents_limiter
        app.register_blueprint(agents_bp)
        try:
            agents_limiter.init_app(app)
        except Exception:
            pass
        app.logger.info("Registered agents_bp at /api/v1/agents")
    except Exception as e:
        app.logger.exception(f"agents_bp import/registration failed: {e}")

    try:
        from src.routes.billing import billing_bp
        app.register_blueprint(billing_bp, url_prefix="/api")
        app.logger.info("Registered billing_bp at /api")
    except Exception as e:
        app.logger.exception(f"billing_bp import/registration failed: {e}")

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

    # --- Preflight for ANY /api/* route ---
    @app.route("/api/<path:_sub>", methods=["OPTIONS"])
    def api_preflight(_sub):
        return ("", 204)

    # --- Debug route map ---
    @app.get("/api/_routes")
    def _routes():
        routes = []
        for r in app.url_map.iter_rules():
            methods = sorted([m for m in (r.methods or [])])
            routes.append({"rule": str(r.rule), "methods": methods})
        routes.sort(key=lambda x: x["rule"])
        return jsonify(routes)

    # --- DB init & gentle SQLite migration (add Agent.description/tags if missing) ---
    with app.app_context():
        db.create_all()

        from sqlalchemy import inspect, text
        try:
            insp = inspect(db.engine)
            if insp.has_table("agents"):
                cols = {c["name"] for c in insp.get_columns("agents")}
                with db.engine.begin() as conn:
                    if "description" not in cols:
                        conn.execute(text("ALTER TABLE agents ADD COLUMN description TEXT"))
                    if "tags" not in cols:
                        conn.execute(text("ALTER TABLE agents ADD COLUMN tags TEXT"))
        except Exception as mig_err:
            app.logger.warning(f"Skipped agents column migration: {mig_err}")

        app.logger.info(f"DB ready using URL: {app.config['SQLALCHEMY_DATABASE_URI']}")

    return app


# gunicorn entrypoint
app = create_app()
