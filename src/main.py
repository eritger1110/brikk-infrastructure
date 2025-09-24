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
        print("Registered auth_bp at /api")
        app.logger.info("Registered auth_bp at /api")
    except Exception as e:
        print(f"auth_bp import/registration failed: {e}")
        app.logger.exception(f"auth_bp import/registration failed: {e}")
        print("auth_bp missing — nothing mounted at /api/auth")

    try:
        from src.routes.app import app_bp
        app.register_blueprint(app_bp, url_prefix="/api")
        print("Registered app_bp at /api")
        app.logger.info("Registered app_bp at /api")
    except Exception as e:
        print(f"app_bp import/registration failed: {e}")
        app.logger.exception(f"app_bp import/registration failed: {e}")

    try:
        # NOTE: agents_bp already has url_prefix="/api/v1/agents" INSIDE the blueprint.
        # Do NOT add another prefix here or you'll get /api/v1/api/v1/agents.
        from src.routes.agents import agents_bp, limiter as agents_limiter
        app.register_blueprint(agents_bp)
        # initialize the limiter instance defined in routes/agents.py
        try:
            agents_limiter.init_app(app)
        except Exception:
            # if limiter already bound, ignore
            pass
        print("Registered agents_bp at /api/v1/agents")
        app.logger.info("Registered agents_bp at /api/v1/agents")
    except Exception as e:
        print(f"agents_bp import/registration failed: {e}")
        app.logger.exception(f"agents_bp import/registration failed: {e}")

    try:
        from src.routes.billing import billing_bp
        app.register_blueprint(billing_bp, url_prefix="/api")
        print("Registered billing_bp at /api")
        app.logger.info("Registered billing_bp at /api")
    except Exception as e:
        print(f"billing_bp import/registration failed: {e}")
        app.logger.exception(f"billing_bp import/registration failed: {e}")

    # Optional dev login (gated by ENABLE_DEV_LOGIN=1)
    if ENABLE_DEV_LOGIN:
        try:
            from src.routes.dev_login import dev_bp
            app.register_blueprint(dev_bp, url_prefix="/api")
            print("Registered dev_login at /api/auth/dev-login")
            app.logger.info("Registered dev_login")
        except Exception as e:
            print(f"dev_login import/registration failed: {e}")
            app.logger.exception(f"dev_login import/registration failed: {e}")

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
