# src/services/emailer.py
import os
import json
import requests

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "").strip()
FROM_EMAIL = os.environ.get("FROM_EMAIL", "connect@getbrikk.com").strip()
FROM_NAME = os.environ.get("FROM_NAME", "Brikk").strip()

def send_email(*, to_email: str, subject: str, html: str, text: str = "") -> bool:
    """
    Send an email with SendGrid v3. Returns True on 2xx. Logs response body on failure.
    """
    if not SENDGRID_API_KEY:
        print("WARN: SENDGRID_API_KEY is not set; skipping email send.")
        return False

    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [
            {"to": [{"email": to_email}], "subject": subject}
        ],
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "reply_to": {"email": FROM_EMAIL, "name": FROM_NAME},
        "content": [
            {"type": "text/plain", "value": text or " "},
            {"type": "text/html", "value": html or "<div></div>"},
        ],
        "tracking_settings": {
            "click_tracking": {"enable": False, "enable_text": False},
            "open_tracking": {"enable": True},
        },
        "categories": ["brikk", "verification"],
    }

    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            url, headers=headers, data=json.dumps(payload), timeout=15
        )
    except Exception as e:
        print("SendGrid request error:", repr(e))
        return False

    ok = 200 <= resp.status_code < 300  # SendGrid usually returns 202
    if not ok:
        print("SendGrid error:", resp.status_code, resp.text)
    return ok
