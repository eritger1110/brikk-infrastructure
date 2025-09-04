from flask import Blueprint, request, jsonify
from src.models.customer_profile import db, CustomerProfile
import os, json

provision_bp = Blueprint('provision', __name__)
PROVISION_SECRET = os.environ.get("PROVISION_SECRET")

@provision_bp.post('/provision/stripe')
def provision_from_stripe():
    if request.headers.get("Authorization") != f"Bearer {PROVISION_SECRET}":
        return jsonify({"error":"unauthorized"}), 401

    data = request.get_json() or {}
    email = data.get("email")
    if not email:
        return jsonify({"error":"email required"}), 400

    profile = CustomerProfile.query.filter_by(email=email).first() or CustomerProfile(email=email)
    profile.name = data.get("name")
    profile.phone = data.get("phone")
    profile.address_json = json.dumps(data.get("address") or {})
    profile.stripe_customer_id = data.get("stripeCustomerId")
    profile.subscription_id = data.get("subscriptionId")
    profile.plan = data.get("plan")
    db.session.add(profile); db.session.commit()

    # TODO: create org/user/limits and produce a deep link:
    app_url = os.environ.get("APP_WELCOME_URL", "https://www.getbrikk.com/")
    return jsonify({"ok": True, "app_url": app_url})
