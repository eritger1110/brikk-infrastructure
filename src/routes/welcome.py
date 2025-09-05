# src/routes/welcome.py
import os
import jwt
from flask import Blueprint, request, redirect, make_response, current_app, abort

welcome_bp = Blueprint("welcome", __name__)

# Where to send users after the cookie is set
APP_FRONTEND_URL   = os.getenv("APP_FRONTEND_URL", "https://app.getbrikk.com")
APP_DASHBOARD_PATH = os.getenv("APP_DASHBOARD_PATH", "/")   # e.g. "/app" or "/" – change if needed

# Cookie settings
COOKIE_NAME   = os.getenv("SESSION_COOKIE_NAME", "access_token_cookie")  # default flask-jwt-extended cookie name
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", ".getbrikk.com")              # works for app/api subdomains

# Token verification
JWT_SECRET    = os.environ["JWT_SECRET_KEY"]   # must match the key used by Netlify to sign the token
JWT_AUDIENCE  = os.getenv("JWT_AUD", "brikk")  # keep in sync with the token payload

@welcome_bp.route("/welcome")
def welcome():
    token = request.args.get("token", "")
    if not token:
        # no token -> just send to the app home
        return redirect(APP_FRONTEND_URL + APP_DASHBOARD_PATH)

    try:
        # Verify the short-lived token we created in Netlify
        jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            audience=JWT_AUDIENCE,
            options={"require": ["exp", "iat"]}
        )
    except Exception as e:
        current_app.logger.warning(f"/welcome invalid token: {e}")
        abort(401)

    # Set the session cookie for the app domain and redirect
    resp = make_response(redirect(APP_FRONTEND_URL + APP_DASHBOARD_PATH))
    resp.set_cookie(
        COOKIE_NAME,
        token,
        max_age=7 * 24 * 3600,        # 7 days
        domain=COOKIE_DOMAIN,
        secure=True,
        httponly=True,
        samesite="None",
    )
    return resp
