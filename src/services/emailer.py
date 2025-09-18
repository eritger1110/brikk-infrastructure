# src/services/emailer.py
from __future__ import annotations

import os
import json
import requests
from typing import Optional, Dict, Any

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL       = os.environ.get("FROM_EMAIL", "connect@getbrikk.com")
FROM_NAME        = os.environ.get("FROM_NAME",  "Brikk")
# Optional: set to "true" to avoid actually sending during tests
SENDGRID_SANDBOX = os.environ.get("SENDGRID_SANDBOX", "").lower() in {"1", "true", "yes", "on"}

def send_email(
    to_email: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
) -> bool:
    """
    Minimal SendGrid v3 send. Returns True on 2xx.
    If SENDGRID_API_KEY is missing, returns False (and logs to stdout).
    """
    if not SENDGRID_API_KEY:
        print("WARN: SENDGRID_API_KEY not set; skipping email.")
        return False

    if not text:
        # simple text fallback from html
        text = (html or "").replace("<br>", "\n").replace("<br/>", "\n")
        text = text.replace("<br />", "\n").replace("</p>", "\n")
        # a very basic strip of tags
        text = "".join(ch for ch in text if ch not in "<>")

    payload: Dict[str, Any] = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text},
            {"type": "text/html",  "value": html},
        ],
    }

    if SENDGRID_SANDBOX:
        payload["mail_settings"] = {"sandbox_mode": {"enable": True}}

    req_headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }
    if headers:
        req_headers.update(headers)

    try:
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers=req_headers,
            data=json.dumps(payload),
            timeout=timeout,
        )
        ok = 200 <= resp.status_code < 300
        if not ok:
            print("SendGrid error:", resp.status_code, resp.text)
        return ok
    except Exception as e:
        print("SendGrid exception:", e)
        return False
