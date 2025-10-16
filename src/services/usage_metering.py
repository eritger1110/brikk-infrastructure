# -*- coding: utf-8 -*-
"""
Usage Metering Middleware (Phase 6 PR-2).

Records API usage in the ledger for metered billing.
Integrates with existing request context and auth middleware.
"""
from flask import Flask, g, request, Response
from src.models.usage_ledger import UsageLedger
from src.services.pricing import get_unit_cost
from src.database import db
from decimal import Decimal
from typing import Optional


class UsageMeteringMiddleware:
    """
    Middleware to record API usage for billing.
    
    Hooks into after_request to log usage entries.
    """
    
    # Routes to exclude from metering
    EXCLUDED_ROUTES = {
        '/health',
        '/telemetry/health',
        '/telemetry/metrics',
        '/docs',
        '/static/openapi.json',
    }
    
    def __init__(self, app: Optional[Flask] = None):
        """Initialize usage metering middleware."""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Register middleware with Flask app."""
        app.after_request(self._record_usage)
    
    def _should_meter(self, response: Response) -> bool:
        """
        Determine if request should be metered.
        
        Args:
            response: Flask response object
            
        Returns:
            True if request should be metered
        """
        # Only meter successful responses (2xx, 3xx)
        if response.status_code >= 400:
            return False
        
        # Skip excluded routes
        path = request.path
        for excluded in self.EXCLUDED_ROUTES:
            if path.startswith(excluded):
                return False
        
        # Must have org_id to meter
        if not hasattr(g, 'org_id') or not g.org_id:
            return False
        
        return True
    
    def _get_tier(self) -> str:
        """
        Get tier for current request from auth context.
        
        Returns:
            Tier name (FREE, HACKER, STARTER, PRO, ENT, INTERNAL, DEFAULT)
        """
        # Check for tier in auth context
        if hasattr(g, 'tier') and g.tier:
            return g.tier
        
        # Check for tier in auth_context dict
        if hasattr(g, 'auth_context') and isinstance(g.auth_context, dict):
            if 'tier' in g.auth_context:
                return g.auth_context['tier']
        
        # Default tier
        return 'DEFAULT'
    
    def _get_actor_id(self) -> str:
        """
        Get actor ID (API key or OAuth client ID).
        
        Returns:
            Actor identifier string
        """
        # Check for actor_id in context
        if hasattr(g, 'actor_id') and g.actor_id:
            return g.actor_id
        
        # Check for API key ID
        if hasattr(g, 'api_key_id') and g.api_key_id:
            return f"api_key:{g.api_key_id}"
        
        # Check for OAuth client ID
        if hasattr(g, 'client_id') and g.client_id:
            return f"oauth:{g.client_id}"
        
        # Fallback to org_id
        return f"org:{g.org_id}"
    
    def _get_agent_id(self) -> Optional[str]:
        """
        Get agent ID if request is agent-related.
        
        Returns:
            Agent ID or None
        """
        # Check if request path includes agent ID
        if '/agents/' in request.path:
            parts = request.path.split('/agents/')
            if len(parts) > 1:
                agent_id = parts[1].split('/')[0]
                return agent_id
        
        # Check for agent_id in context
        if hasattr(g, 'agent_id') and g.agent_id:
            return g.agent_id
        
        return None
    
    def _record_usage(self, response: Response) -> Response:
        """
        Record usage after request completion.
        
        Args:
            response: Flask response object
            
        Returns:
            Unmodified response
        """
        # Check if metering is enabled for this request
        if not self._should_meter(response):
            return response
        
        try:
            # Get metering parameters
            org_id = g.org_id
            actor_id = self._get_actor_id()
            tier = self._get_tier()
            route = request.path
            agent_id = self._get_agent_id()
            
            # Get unit cost from tier
            unit_cost = get_unit_cost(tier)
            
            # Record usage (default: 1 unit per request)
            # Future: extend to support CPU/latency-based units
            UsageLedger.record_usage(
                org_id=org_id,
                actor_id=actor_id,
                route=route,
                unit_cost=unit_cost,
                usage_units=1,
                agent_id=agent_id
            )
            
        except Exception as e:
            # Log error but don't fail the request
            if hasattr(self.app, 'logger'):
                self.app.logger.error(f"Usage metering failed: {e}")
        
        return response


def init_usage_metering(app: Flask):
    """
    Initialize usage metering for the application.
    
    Args:
        app: Flask application instance
    """
    UsageMeteringMiddleware(app)

