'''
App factory for Brikk infrastructure.
'''
from flask import Flask
from .database import db

def create_app(config_overrides=None):
    app = Flask(__name__)

    # Load default config
    app.config.from_object("src.config.Config")

    if config_overrides:
        app.config.from_mapping(config_overrides)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from .routes import coordination, health, internal, inbound
    app.register_blueprint(coordination.bp)
    app.register_blueprint(health.bp)
    app.register_blueprint(internal.bp)
    app.register_blueprint(inbound.inbound_bp, url_prefix="/api")

    return app

