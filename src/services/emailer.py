# src/services/emailer.py
import os
import json
import requests

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "no-reply@getbrikk.com")
FROM_NAME = os.environ.get("FROM_NAME", "Brikk")

def send_email(to_email: str, subject: str, html: str) -> bool:
    if not SENDGRID_API_KEY:
        print("WARN: SENDGRID_API_KEY is not set; skipping email.")
        return False

    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    ok = 200 <= resp.status_code < 300
    if not ok:
        print("SendGrid error:", resp.status_code, resp.text)
    return ok
