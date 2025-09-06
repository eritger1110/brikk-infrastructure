# src/routes/welcome.py
import os
from flask import Blueprint, request, redirect, make_response
from flask_jwt_extended import create_access_token, set_access_cookies
import jwt as pyjwt  # PyJWT

welcome_bp = Blueprint("welcome_bp", __name__)

@welcome_bp.route("/welcome")
def welcome():
    token = request.args.get("token", "")
    if not token:
        return "Missing token", 400

    secret = os.environ.get("JWT_SECRET_KEY", "change-me")

    try:
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        # Token expired (most common when service cold-starts and token lifetime is short)
        return (
            "Link expired. Please return to the previous page and try again.", 401
        )
    except Exception:
        return "Unauthorized", 401

    email = payload.get("email")
    if not email:
        return "Unauthorized", 401

    # Mint your app session cookie
    app_claims = {"email": email, "role": "user"}
    access_token = create_access_token(identity=email, additional_claims=app_claims)

    # Where to send the user after we set the cookie
    # Example: https://www.getbrikk.com/app/  (or just https://www.getbrikk.com/)
    dashboard_url = os.environ.get("APP_WELCOME_URL", "https://www.getbrikk.com/")

    resp = make_response(redirect(dashboard_url))
    set_access_cookies(resp, access_token)
    return resp
