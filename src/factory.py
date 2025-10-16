# -*- coding: utf-8 -*-
import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.database import db

# Observability imports
from src.services.metrics import init_metrics
from src.services.request_context import init_request_context
from src.services.structured_logging import init_logging
from src.services.size_limit_middleware import SizeLimitMiddleware

ENABLE_SECURITY_ROUTES = os.getenv("ENABLE_SECURITY_ROUTES") == "1"
ENABLE_DEV_ROUTES = os.getenv("BRIKK_ENABLE_DEV_ROUTES", "").lower() in ("1", "true", "yes")
ENABLE_TALISMAN = os.getenv("ENABLE_TALISMAN", "1") == "1"  # set 0 to disable


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg://" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _migrate_db(app):
    """Run Alembic migrations to head using the app's DB URL."""
    from pathlib import Path
    
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:
        app.logger.error("Failed to run migrations: Alembic not installed")
        return  # do not crash the process
    
    BASE_DIR = Path(__file__).resolve().parent.parent
    cfg = Config()  # in-memory config, avoid alembic.ini dependency
    cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", app.config["SQLALCHEMY_DATABASE_URI"])
    
    try:
        command.upgrade(cfg, "head")
        app.logger.info("Database migrations applied successfully")
    except Exception as e:
        app.logger.error(f"Migration failed: {e}")
        raise


def _seed_system_accounts():
    """Creates the default system ledger accounts if they don't exist."""
    from src.models.economy import LedgerAccount
    from flask import current_app
    import sqlalchemy as sa
    
    # Check if ledger_accounts table exists before attempting to seed
    eng = db.engine
    insp = sa.inspect(eng)
    
    if not insp.has_table("ledger_accounts"):
        current_app.logger.warning(
            "Skipping system account seeding: ledger_accounts table missing "
            "(migrate will create it)."
        )
        return

    system_accounts = [
        {"name": "platform_revenue", "type": "system"},
        {"name": "platform_fees", "type": "system"},
        {"name": "promotions", "type": "system"},
    ]

    for acc_data in system_accounts:
        acc = LedgerAccount.query.filter_by(name=acc_data["name"]).first()
        if not acc:
            new_acc = LedgerAccount(
                name=acc_data["name"],
                type=acc_data["type"])
            db.session.add(new_acc)
    db.session.commit()
    current_app.logger.info(f"Seeded {len(system_accounts)} system accounts")


def create_app() -> Flask:
    app = Flask(__name__)
    app.url_map.strict_slashes = False

    # --- Core config ---
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # --- DB config ---
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "instance",
            "app.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db_url = f"sqlite:///{db_path}"
    else:
        db_url = _normalize_db_url(db_url)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # --- JWT cookies ---
    JWTManager(app)

    # --- CORS ---
    CORS(app, supports_credentials=True)

    # --- Initialize observability ---
    init_logging(app)
    init_request_context(app)
    init_metrics(app)
    
    # --- Initialize size limit middleware (PR-L) ---
    size_limit = SizeLimitMiddleware()
    size_limit.init_app(app)
    
    # --- Initialize API Gateway services ---
    from src.services.gateway_metrics import init_gateway_metrics
    from src.services.audit_logger import init_audit_logging
    from src.services.rate_limiter import init_rate_limiter
    from src.services.usage_metering import init_usage_metering
    
    init_gateway_metrics(app)
    init_audit_logging(app)
    init_usage_metering(app)  # Phase 6: Usage metering for billing
    # Note: Rate limiter requires Redis, will gracefully degrade if unavailable
    try:
        limiter = init_rate_limiter(app)
        app.extensions['limiter'] = limiter
    except Exception as e:
        app.logger.warning(f"Rate limiter initialization failed: {e}. Rate limiting disabled.")

    # --- Mount blueprints ---
    with app.app_context():
        from src.routes import (
            auth, agents, billing, coordination, auth_admin, workflows,
            monitoring, alerting, webhooks, discovery, reputation, connectors_zendesk,
            health, inbound, api_keys, auth_test, oauth,
            telemetry, docs, agent_registry, deprecations, trust,
            marketplace, analytics, agent_discovery, reviews
        )
        from src.routes import app as app_routes
        app.register_blueprint(auth.auth_bp, url_prefix="/api")
        app.register_blueprint(app_routes.app_bp, url_prefix="/api")
        app.register_blueprint(agents.agents_bp)
        app.register_blueprint(billing.billing_bp, url_prefix="/api")
        app.register_blueprint(coordination.coordination_bp)
        app.register_blueprint(auth_admin.auth_admin_bp)
        app.register_blueprint(workflows.workflows_bp)
        app.register_blueprint(monitoring.monitoring_bp)
        app.register_blueprint(alerting.alerting_bp)
        app.register_blueprint(webhooks.webhooks_bp)
        app.register_blueprint(discovery.discovery_bp)
        app.register_blueprint(reputation.reputation_bp)
        app.register_blueprint(
            connectors_zendesk.zendesk_bp,
            url_prefix="/api")
        app.register_blueprint(health.health_bp, url_prefix="/")
        app.register_blueprint(inbound.inbound_bp, url_prefix="/api")
        app.register_blueprint(api_keys.api_keys_bp, url_prefix="/api")
        app.register_blueprint(auth_test.auth_test_bp, url_prefix="/api/v1/auth-test")
        app.register_blueprint(oauth.oauth_bp, url_prefix="/oauth")
        app.register_blueprint(telemetry.telemetry_bp, url_prefix="/telemetry")
        app.register_blueprint(docs.docs_bp)
        app.register_blueprint(docs.swaggerui_blueprint, url_prefix=docs.SWAGGER_URL)
        app.register_blueprint(agent_registry.agent_registry_bp, url_prefix="/api/v1")
        app.register_blueprint(deprecations.deprecations_bp, url_prefix="/api")
        app.register_blueprint(trust.trust_bp, url_prefix="/api/v1/trust")
        
        # Phase 7: Marketplace & Analytics
        app.register_blueprint(marketplace.marketplace_bp, url_prefix="/api/v1/marketplace")
        app.register_blueprint(analytics.analytics_bp, url_prefix="/api/v1/analytics")
        app.register_blueprint(agent_discovery.agent_discovery_bp, url_prefix="/api/v1/agent-discovery")
        app.register_blueprint(reviews.reviews_bp, url_prefix="/api/v1/reviews")

        # Dev routes (not in prod)
        if ENABLE_DEV_ROUTES:
            try:
                from src.routes.dev_login import dev_bp
                app.register_blueprint(dev_bp, url_prefix="/api")
                app.logger.info("Registered dev_bp at /api")
            except Exception as e:
                app.logger.warning(f"Dev routes disabled (import failed): {e}")
        else:
            app.logger.info("Skipped dev_bp registration")

        if ENABLE_SECURITY_ROUTES:
            from src.routes import security
            app.register_blueprint(security.security_bp, url_prefix="/api")

    # --- DB init ---
    with app.app_context():
        # Only auto-create tables in testing or if explicitly enabled
        is_testing = app.config.get("TESTING") or os.getenv("TESTING", "false").lower() == "true"
        if is_testing or os.getenv("BRIKK_DB_AUTOCREATE", "false").lower() == "true":
            db.create_all()
        
        # Run migrations BEFORE seeding (default on in prod; can disable with env)
        # Skip migrations in test mode since db.create_all() already creates correct schema
        if not is_testing and os.getenv("BRIKK_DB_MIGRATE_ON_START", "true").lower() == "true":
            try:
                _migrate_db(app)
            except Exception as e:
                app.logger.error(f"Failed to run migrations: {e}")
                raise
        
        # Seed system accounts (safe if tables don't exist)
        _seed_system_accounts()

    return app

