# -*- coding: utf-8 -*-
# src/models/customer_profile.py
from src.database import db


class CustomerProfile(db.Model):
    __tablename__ = 'customer_profiles'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    address_json = db.Column(db.Text)
    stripe_customer_id = db.Column(db.String(64), unique=True)
    subscription_id = db.Column(db.String(64), unique=True)
    plan = db.Column(db.String(128))
