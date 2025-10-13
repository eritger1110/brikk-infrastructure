# -*- coding: utf-8 -*-
# src/routes/provision.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies
from datetime import timedelta
import os
import bcrypt
import stripe
from src.models.user import User, db  # adjust import if your model is elsewhere

provision_bp = Blueprint('provision', __name__)
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

APP_DASHBOARD_PATH = os.getenv('APP_DASHBOARD_PATH', '/app/')
COOKIE_DOMAIN = os.getenv('COOKIE_DOMAIN', '.getbrikk.com')  # optional


@provision_bp.route('/api/signup-from-stripe', methods=['POST'])
def signup_from_stripe():
    """
    Body: { session_id, first_name, last_name, password }
    Verifies checkout session with Stripe, uses its email, creates user, sets cookie auth, returns next path.
    """
    data = request.get_json(silent=True) or {}
    sid = data.get('session_id', '').strip()
    first = data.get('first_name', '').strip()
    last = data.get('last_name', '').strip()
    password = data.get('password', '')

    if not sid or not password or len(password) < 8:
        return jsonify(success=False, error='Invalid payload'), 400

    try:
        # Verify the checkout session with Stripe
        session = stripe.checkout.Session.retrieve(sid, expand=['customer'])
        if session.mode != 'subscription' or session.status != 'complete':
            return jsonify(success=False, error='Checkout not completed'), 400

        email = (
            session.customer_details.email if session.customer_details and session.customer_details.email else (
                getattr(
                    session.customer,
                    'email',
                    None) if isinstance(
                    session.customer,
                    object) else None))
        if not email:
            return jsonify(
                success=False, error='No email on Stripe session'), 400

        # Create or update user
        user = User.query.filter_by(email=email).first()
        if not user:
            # adapt fields to your model (username, name, etc.)
            user = User(username=email.split('@')[0], email=email)
            db.session.add(user)

        if first:
            # if your model has first_name/last_name fields, set them:
            if hasattr(user, 'first_name'):
                user.first_name = first
            if hasattr(user, 'last_name'):
                user.last_name = last

        # set password hash (bcrypt)
        user.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()).decode('utf-8')
        db.session.commit()

        # OPTIONAL: send welcome / verification email via SendGrid (uses env SENDGRID_API_KEY, FROM_EMAIL)
        # Skipped here to keep the example tight; you can reuse the email code
        # we added earlier.

        # Issue a login cookie so they land signed in
        access_token = create_access_token(
            identity=str(
                user.id), expires_delta=timedelta(
                days=7))
        resp = jsonify(success=True, next=APP_DASHBOARD_PATH)
        set_access_cookies(
            resp,
            access_token,
            domain=COOKIE_DOMAIN if COOKIE_DOMAIN else None,
            samesite='None',
            secure=True)
        return resp

    except stripe.error.StripeError as e:
        return jsonify(success=False, error=f'Stripe error: {str(e)}'), 400
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e)), 500
