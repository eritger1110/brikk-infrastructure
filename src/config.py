import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "a_default_secret_key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///brikk.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "a_default_jwt_secret_key")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    CREDITS_PRICE_USD_CENTS = int(os.getenv("CREDITS_PRICE_USD_CENTS", 100))
    COORDINATION_COST_CREDITS = int(os.getenv("COORDINATION_COST_CREDITS", 1))
    ENABLE_ECONOMY = os.getenv("ENABLE_ECONOMY", "1") == "1"

