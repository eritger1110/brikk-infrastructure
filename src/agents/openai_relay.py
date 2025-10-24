# -*- coding: utf-8 -*-
"""
OpenAI Relay Agent

This endpoint relays chat requests to OpenAI's API,
enabling Brikk to orchestrate OpenAI as part of agent chains.
"""
import os
import json
import requests
from flask import Blueprint, request, jsonify

bp = Blueprint("openai_relay", __name__, url_prefix="/agents/openai")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@bp.route("/chat", methods=["POST"])
def chat():
    """
    Relay a chat request to OpenAI's API.
    
    Expected payload:
    {
        "message": "User message to send to OpenAI",
        "system": "Optional system prompt (defaults to Brikk Test Agent)"
    }
    
    Returns:
    {
        "ok": true,
        "output": "OpenAI's response text"
    }
    """
    data = request.get_json(force=True) or {}
    message = data.get("message", "")
    system = data.get("system", "You are Brikk Test Agent. Be concise.")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    if not OPENAI_API_KEY:
        return jsonify({
            "ok": False,
            "error": "OPENAI_API_KEY not configured"
        }), 500
    
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": message}
                ]
            },
            timeout=30
        )
        resp.raise_for_status()
        out = resp.json()["choices"][0]["message"]["content"]
        return jsonify({"ok": True, "output": out})
    except requests.exceptions.RequestException as e:
        return jsonify({
            "ok": False,
            "error": f"OpenAI API error: {str(e)}"
        }), 500
    except (KeyError, IndexError) as e:
        return jsonify({
            "ok": False,
            "error": f"Unexpected OpenAI response format: {str(e)}"
        }), 500

