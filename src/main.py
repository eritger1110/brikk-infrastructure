# src/main.py
import os, sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# make relative imports work when launched by gunicorn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db import db

# optional blueprints (won't crash if a module is absent)
def _opt_import(path, name):
    try:
        mod = __import__(path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None

auth_bp     = _opt_import("src.routes.auth", "auth_bp")
security_bp = _opt_import("src.routes.security", "security_bp")
# add more optional BPs if you have them:
# user_bp     = _opt_import("src.routes.user", "user_bp")
# provision_bp = _opt_import("src.routes.provision", "provision_bp")
# coordination_bp = _opt_import("src.routes.coordination", "coordination_bp")

def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    )

    # --- Core config ---
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # DB: prefer DATABASE_URL, else sqlite file
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_path = os.path.join(os.path.dirname(__file__), "database", "app.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db_url = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- JWT cookies only ---
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", app.config["SECRET_KEY"])
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_COOKIE_SECURE"] = True           # required for SameSite=None
    app.config["JWT_COOKIE_SAMESITE"] = "None"

    # Only set JWT_COOKIE_DOMAIN when API itself is on *.getbrikk.com
    cookie_domain = os.environ.get("JWT_COOKIE_DOMAIN", "").strip()
    if cookie_domain and cookie_domain.endswith(".getbrikk.com"):
        # You can keep this env var defined, but it won’t break if left empty.
        app.config["JWT_COOKIE_DOMAIN"] = cookie_domain
    # otherwise: leave unset so cookies are scoped to the onrender.com host

    # --- CORS ---
    app_url = os.environ.get("APP_URL", "https://www.getbrikk.com").rstrip("/")
    allowed_origins = {
        "https://www.getbrikk.com",
        "https://getbrikk.com",
        app_url,  # in case you deploy the app somewhere else for staging
    }
    CORS(app, resources={r"/api/*": {"origins": list(allowed_origins)}}, supports_credentials=True)

    # --- Init extensions ---
    db.init_app(app)
    JWTManager(app)
    
    # --- health & root probes (Render) ---
    from flask import jsonify  # make sure this import is at the top of the file

    @app.route("/health", methods=["GET", "HEAD"])
    def health():
        # keep it super small and always 200 if the process is alive
        return jsonify({"ok": True}), 200

    @app.route("/", methods=["GET", "HEAD"])
    def root():
        return jsonify({"ok": True, "service": "brikk-api"}), 200

    # --- Blueprints ---
    if auth_bp:     app.register_blueprint(auth_bp)
    if security_bp: app.register_blueprint(security_bp)
    # if user_bp:     app.register_blueprint(user_bp)
    # if provision_bp: app.register_blueprint(provision_bp)
    # if coordination_bp: app.register_blueprint(coordination_bp)

    # --- Health ---
    @app.get("/healthz")
    def healthz():
        return jsonify({"ok": True})

    # create tables if using sqlite
    with app.app_context():
        db.create_all()

    return app

app = create_app()
