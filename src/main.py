import os
import sys

# Make "from src.…" imports work when run by Render
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# DB and blueprints
from src.models.agent import db
from src.routes.auth import auth_bp                 # ← NEW (email verify + login)
from src.routes.user import user_bp
from src.routes.coordination import coordination_bp
from src.routes.security import security_bp
from src.routes.provision import provision_bp

# Optional "welcome" tester page
try:
    from src.routes.welcome import welcome_bp
except Exception:
    welcome_bp = None

# --------------------------------------------------------------------
# Create app with correct static/template folders
# --------------------------------------------------------------------
app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
    template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
)

# --------------------------------------------------------------------
# Core + DB config
# --------------------------------------------------------------------
app.config["SECRET_KEY"] = "brikk_enterprise_secret_key_2024_production"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --------------------------------------------------------------------
# JWT cookies (MUST be set before creating JWTManager(app))
# --------------------------------------------------------------------
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "change-me")
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = True            # HTTPS only
app.config["JWT_COOKIE_SAMESITE"] = "None"        # allow cross-site cookies (Netlify <-> Render)
app.config["JWT_COOKIE_CSRF_PROTECT"] = False     # enable later if you want double-submit CSRF

# Optional: allow cookies across subdomains (www/app/api)
cookie_domain = os.environ.get("COOKIE_DOMAIN")
if cookie_domain:
    app.config["JWT_COOKIE_DOMAIN"] = cookie_domain  # e.g., ".getbrikk.com"

# --------------------------------------------------------------------
# Extensions: CORS (with credentials) and JWT
# --------------------------------------------------------------------
CORS(
    app,
    resources={r"/api/*": {"origins": [
        "https://www.getbrikk.com",
        "https://getbrikk.com",
        "https://app.getbrikk.com",
        "https://brikk-infrastructure.onrender.com",  # useful for local/alt testing
    ]}},
    supports_credentials=True,  # allow browser to send cookies
)

jwt = JWTManager(app)
db.init_app(app)

# Create DB tables on first run
with app.app_context():
    db.create_all()

# --------------------------------------------------------------------
# Register blueprints (order doesn't matter)
# --------------------------------------------------------------------
app.register_blueprint(auth_bp)                                  # ← NEW
app.register_blueprint(user_bp, url_prefix="/api")
app.register_blueprint(coordination_bp, url_prefix="/api")
app.register_blueprint(security_bp, url_prefix="/api")
app.register_blueprint(provision_bp, url_prefix="/api")
if welcome_bp:
    app.register_blueprint(welcome_bp)

# --------------------------------------------------------------------
# Health check
# --------------------------------------------------------------------
@app.route("/health")
def health_check():
    return {
        "service": "Brikk Enterprise AI Agent Coordination Platform",
        "status": "healthy",
        "version": "2.0.0",
        "environment": "production",
        "features": [
            "Multi-language agent coordination",
            "Enterprise security & HIPAA compliance",
            "Real-time performance monitoring",
            "Comprehensive audit logging",
        ],
    }

# --------------------------------------------------------------------
# Static / app shell
# --------------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path: str):
    # Serve SPA shell for root and index.html
    if path == "" or path == "index.html":
        return render_template("index.html")

    # Serve static files if present
    static_folder_path = app.static_folder
    if not static_folder_path:
        return "Static folder not configured", 404

    full = os.path.join(static_folder_path, path)
    if path and os.path.exists(full):
        return send_from_directory(static_folder_path, path)

    # Default: SPA shell
    return render_template("index.html")


if __name__ == "__main__":
    # For local dev; Render sets its own web server/port
    app.run(host="0.0.0.0", port=5000, debug=True)
