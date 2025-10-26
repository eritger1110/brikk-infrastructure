# -*- coding: utf-8 -*-
"""
Multi-Provider Routes for Phase 9

Provides Mistral relay, Router with fallback, and provider status endpoints.
"""

from flask import Blueprint, request, jsonify
from src.services.openai_service import OpenAIService
from src.services.mistral_service import MistralService
from src.services.router_service import RouterService

bp = Blueprint("multi_provider", __name__)

# Initialize services
openai_service = OpenAIService()
mistral_service = MistralService()
router_service = RouterService()


@bp.route("/agents/mistral/chat", methods=["POST", "OPTIONS"])
def mistral_chat():
    """
    Mistral chat endpoint.
    
    POST /agents/mistral/chat
    Body: {
        "message": string,
        "system": string (optional),
        "language": string (optional),
        "meta": object (optional)
    }
    
    Returns: {
        "provider": "mistral",
        "model": string,
        "message": string,
        "usage": object,
        "request_id": string,
        "latency_ms": number
    }
    """
    if request.method == "OPTIONS":
        return "", 204
    
    data = request.get_json(force=True) or {}
    message = data.get("message", "")
    system = data.get("system")
    language = data.get("language")
    meta = data.get("meta")
    
    if not message:
        return jsonify({
            "error": "message field is required",
            "provider": "mistral"
        }), 400
    
    result = mistral_service.chat(message, system, language, meta)
    
    # Return 400 if not configured or error occurred
    if "error" in result:
        return jsonify(result), 400 if "not configured" in result.get("error", "") else 502
    
    return jsonify(result), 200


@bp.route("/agents/route/chat", methods=["POST", "OPTIONS"])
def route_chat():
    """
    Router endpoint with intelligent provider selection and fallback.
    
    POST /agents/route/chat
    Body: {
        "message": string,
        "system": string (optional),
        "language": "en"|"es"|"ja"|"ar" (optional, default: "en"),
        "hint": "cheap"|"quality"|"balanced" (optional, default: "balanced"),
        "policy": string (optional, custom policy override),
        "meta": object (optional)
    }
    
    Returns: {
        "provider": "openai"|"mistral",
        "fallback": boolean,
        "model": string,
        "message": string,
        "usage": object,
        "request_id": string,
        "latency_ms": number
    }
    """
    if request.method == "OPTIONS":
        return "", 204
    
    data = request.get_json(force=True) or {}
    message = data.get("message", "")
    system = data.get("system")
    language = data.get("language", "en")
    hint = data.get("hint", "balanced")
    policy = data.get("policy")
    meta = data.get("meta")
    
    if not message:
        return jsonify({
            "error": "message field is required"
        }), 400
    
    result = router_service.route_chat(
        message=message,
        system=system,
        language=language,
        hint=hint,
        policy=policy,
        meta=meta
    )
    
    # Return 502 if both providers failed
    if "error" in result and result.get("fallback") == False:
        return jsonify(result), 502
    
    return jsonify(result), 200


@bp.route("/health/providers", methods=["GET"])
@bp.route("/api/v1/providers/status", methods=["GET"])
def provider_status():
    """
    Get status of all configured providers.
    
    GET /health/providers or /api/v1/providers/status
    
    Returns: {
        "openai": {
            "configured": boolean,
            "model": string|null
        },
        "mistral": {
            "configured": boolean,
            "model": string|null
        }
    }
    """
    status = router_service.get_provider_status()
    return jsonify(status), 200

