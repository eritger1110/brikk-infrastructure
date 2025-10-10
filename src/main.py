import os
import sys
import importlib
from typing import List

from flask import Flask, jsonify, request, current_app
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from src.database.db import db  # global SQLAlchemy() instance

# Make relative imports work when launched by gunicorn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Observability imports
from src.services.metrics import init_metrics
from src.services.request_context import init_request_context
from src.services.structured_logging import init_logging

ENABLE_SECURITY_ROUTES = os.getenv("ENABLE_SECURITY_ROUTES") == "1"
ENABLE_DEV_LOGIN = os.getenv("ENABLE_DEV_LOGIN", "0") == "1"
ENABLE_TALISMAN = os.getenv("ENABLE_TALISMAN", "1") == "1"  # set 0 to disable

# Flask-Limiter storage (agents blueprint calls limiter.init_app(app))
os.environ.setdefault(
    "RATELIMIT_STORAGE_URI",
    os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)


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

    # Inbound signature verification config (used by src.routes.inbound)
    app.config["INBOUND_SIGNING_SECRET"] = os.getenv("INBOUND_SIGNING_SECRET")
    app.config["REQUIRE_INBOUND_SIGNATURE"] = os.getenv("REQUIRE_INBOUND_SIGNATURE", "1") == "1"
    app.config["INBOUND_MAX_SKEW"] = int(os.getenv("INBOUND_MAX_SKEW", "300"))

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
    jwt_cookie_domain = os.getenv("JWT_COOKIE_DOMAIN", ".getbrikk.com")
    app.config.update(
        JWT_TOKEN_LOCATION=["cookies"],
        JWT_COOKIE_SECURE=True,          # HTTPS only
        JWT_COOKIE_SAMESITE="None",      # allow cross-site from www.getbrikk.com
        JWT_COOKIE_DOMAIN=jwt_cookie_domain if jwt_cookie_domain else None,
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
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "X-Brikk-Signature"],
                "expose_headers": [],
                "max_age": 600,
            }
        },
    )

    # --- Initialize observability ---
    # Initialize logging first (before other middleware)
    init_logging(app)
    
    # Initialize request context middleware
    init_request_context(app)
    
    # Initialize metrics and health endpoints
    init_metrics(app)

    # --- Security headers / CSP ---
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
            app.logger.warning(
                f"Talisman not active ({e}). Set ENABLE_TALISMAN=0 or add flask-talisman."
            )

    # --- Health & root ---
    @app.route("/health", methods=["GET", "HEAD"])
    def health():
        return jsonify({"ok": True}), 200

    @app.route("/", methods=["GET", "HEAD"])
    def root():
        return jsonify({"ok": True, "service": "brikk-api"}), 200

    # --- Mount blueprints (register routes) ---
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
            agents_limiter.init_app(app)  # uses RATELIMIT_STORAGE_URI
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

    try:
        from src.routes.coordination import coordination_bp
        app.register_blueprint(coordination_bp)
        app.logger.info("Registered coordination_bp (includes existing /api/coordination/* and new /api/v1/coordination)")
    except Exception as e:
        app.logger.exception(f"coordination_bp import/registration failed: {e}")

    try:
        from src.routes.auth_admin import auth_admin_bp
        app.register_blueprint(auth_admin_bp)
        app.logger.info("Registered auth_admin_bp at /internal (protected by BRIKK_ADMIN_TOKEN)")
    except Exception as e:
        app.logger.exception(f"auth_admin_bp import/registration failed: {e}")

    try:
        from src.routes.workflows import workflows_bp
        app.register_blueprint(workflows_bp)
        app.logger.info("Registered workflows_bp")
    except Exception as e:
        app.logger.exception(f"workflows_bp import/registration failed: {e}")

    try:
        from src.routes.monitoring import monitoring_bp
        app.register_blueprint(monitoring_bp)
        app.logger.info("Registered monitoring_bp")
    except Exception as e:
        app.logger.exception(f"monitoring_bp import/registration failed: {e}")

    try:
        from src.routes.alerting import alerting_bp
        app.register_blueprint(alerting_bp)
        app.logger.info("Registered alerting_bp")
    except Exception as e:
        app.logger.exception(f"alerting_bp import/registration failed: {e}")

    try:
        from src.routes.webhooks import webhooks_bp
        app.register_blueprint(webhooks_bp)
        app.logger.info("Registered webhooks_bp")
    except Exception as e:
        app.logger.exception(f"webhooks_bp import/registration failed: {e}")

    try:
        from src.routes.discovery import discovery_bp
        app.register_blueprint(discovery_bp)
        app.logger.info("Registered discovery_bp")
    except Exception as e:
        app.logger.exception(f"discovery_bp import/registration failed: {e}")

    # --- Inbound: inline sanity ping so we know the app is alive at this prefix ---
    @app.get("/api/inbound/_ping_inline")
    def _inbound_inline():
        return jsonify({"ok": True, "where": "inline"}), 200

    # --- Inbound blueprint ---
    print(">>> inbound: attempting import", flush=True)
    try:
        mod = importlib.import_module("src.routes.inbound")
        inbound_bp = getattr(mod, "inbound_bp")
        print(f">>> inbound: module file = {getattr(mod, '__file__', '<?>')}", flush=True)
        df = getattr(inbound_bp, "deferred_functions", None)
        print(
            f">>> inbound: deferred_functions count = {len(df) if df is not None else 'n/a'}",
            flush=True,
        )

        app.register_blueprint(inbound_bp, url_prefix="/api/inbound")

        def _mounted() -> List[str]:
            return sorted(
                [str(r.rule) for r in app.url_map.iter_rules() if str(r.rule).startswith("/api/inbound/")]
            )

        mounted = _mounted()
        print(f">>> inbound: routes after register = {mounted}", flush=True)
        print(">>> inbound: registered OK", flush=True)

    except Exception as e:
        app.logger.exception(f"inbound_bp import/registration failed: {e}")
        print(f">>> inbound: FAILED -> {e}", flush=True)

    # Optional: Zendesk connector
    try:
        from src.routes.connectors_zendesk import zendesk_bp
        app.register_blueprint(zendesk_bp, url_prefix="/api")
        app.logger.info("Registered zendesk_bp at /api")
    except Exception as e:
        app.logger.exception(f"zendesk_bp import/registration failed: {e}")

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

    # --- DB init & gentle SQLite migration ---
    with app.app_context():
        db.create_all()

        from sqlalchemy import inspect, text

        try:
            insp = inspect(db.engine)

            # agents: add description/tags if missing
            if insp.has_table("agents"):
                cols = {c["name"] for c in insp.get_columns("agents")}
                with db.engine.begin() as conn:
                    if "description" not in cols:
                        conn.execute(text("ALTER TABLE agents ADD COLUMN description TEXT"))
                    if "tags" not in cols:
                        conn.execute(text("ALTER TABLE agents ADD COLUMN tags TEXT"))

            # users: add role/org_id if missing (handy for SQLite dev)
            if insp.has_table("users"):
                ucols = {c["name"] for c in insp.get_columns("users")}
                with db.engine.begin() as conn:
                    if "role" not in ucols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20)"))
                    if "org_id" not in ucols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN org_id VARCHAR(64)"))
        except Exception as mig_err:
            app.logger.warning(f"Skipped column migration: {mig_err}")

        # Minimal/log-safe visibility of the configured driver
        driver = app.config["SQLALCHEMY_DATABASE_URI"].split("://", 1)[0]
        app.logger.info(f"DB ready (driver={driver})")

    return app


# gunicorn entrypoint
app = create_app()

