# src/main.py
import os, sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# make relative imports work when launched by gunicorn
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db import db  # SQLAlchemy() instance

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
    app.config
