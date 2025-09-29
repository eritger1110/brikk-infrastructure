# src/routes/connectors_zendesk.py
import os, requests
from flask import Blueprint, request, jsonify
from src.services.security import require_auth

zendesk_bp = Blueprint("zendesk", __name__, url_prefix="/api/connectors/zendesk")

def _cfg():
    return {
        "subdomain": os.getenv("ZENDESK_SUBDOMAIN"),
        "email": os.getenv("ZENDESK_EMAIL"),
        "token": os.getenv("ZENDESK_API_TOKEN"),
    }

def _auth():
    c = _cfg()
    return (f"{c['email']}/token", c["token"])

@zendesk_bp.get("/tickets")
@require_auth
def list_tickets():
    c = _cfg()
    url = f"https://{c['subdomain']}.zendesk.com/api/v2/tickets.json?page[size]=25"
    r = requests.get(url, auth=_auth(), timeout=20)
    return jsonify(r.json()), r.status_code

@zendesk_bp.post("/tickets/reply")
@require_auth
def reply_ticket():
    c = _cfg()
    data = request.get_json(silent=True) or {}
    tid = data.get("ticket_id")
    body = data.get("body") or "Thanks, we're on it."
    if not tid:
        return jsonify({"error": "ticket_id required"}), 400
    url = f"https://{c['subdomain']}.zendesk.com/api/v2/tickets/{tid}.json"
    payload = {"ticket": {"comment": {"body": body, "public": True}}}
    r = requests.put(url, json=payload, auth=_auth(), timeout=20)
    return jsonify(r.json()), r.status_code
