"""
Router service for intelligent provider selection and fallback.
Routes requests to appropriate AI providers based on language, hints, and availability.
"""

import uuid
import logging
from typing import Dict, Any, Optional
from src.services.openai_service import OpenAIService
from src.services.mistral_service import MistralService
from src.services.provider_metrics import record_request

logger = logging.getLogger(__name__)

class RouterService:
    """Service for routing requests to appropriate AI providers with fallback."""
    
    def __init__(self):
        self.openai = OpenAIService()
        self.mistral = MistralService()
        
        # Default routing policy
        self.default_policy = {
            "es": "mistral",  # Spanish -> prefer Mistral
            "en": "openai",   # English -> prefer OpenAI
            "ja": "openai",   # Japanese -> prefer OpenAI
            "ar": "openai"    # Arabic -> prefer OpenAI
        }
        
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all configured providers."""
        return {
            "openai": {
                "configured": self.openai.is_configured(),
                "model": self.openai.model if self.openai.is_configured() else None
            },
            "mistral": {
                "configured": self.mistral.is_configured(),
                "model": self.mistral.model if self.mistral.is_configured() else None
            }
        }
    
    def _select_provider(
        self,
        language: Optional[str] = None,
        hint: Optional[str] = None,
        policy: Optional[str] = None
    ) -> str:
        """
        Select the appropriate provider based on language, hint, and policy.
        
        Args:
            language: Language code (en, es, ja, ar)
            hint: Performance hint (cheap, quality, balanced)
            policy: Custom policy override
            
        Returns:
            Provider name ('openai' or 'mistral')
        """
        # If custom policy provided, use it
        if policy:
            if policy in ["openai", "mistral"]:
                return policy
        
        # Use language-based routing
        if language and language in self.default_policy:
            return self.default_policy[language]
        
        # Use hint-based routing
        if hint == "cheap":
            return "mistral"  # Mistral is typically cheaper
        elif hint == "quality":
            return "openai"   # OpenAI is typically higher quality
        
        # Default to OpenAI (most reliable)
        return "openai"
    
    def route_chat(
        self,
        message: str,
        system: Optional[str] = None,
        language: Optional[str] = "en",
        hint: Optional[str] = "balanced",
        policy: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Route a chat request to the appropriate provider with fallback.
        
        Args:
            message: User message
            system: Optional system message
            language: Language code (en, es, ja, ar)
            hint: Performance hint (cheap, quality, balanced)
            policy: Custom policy override
            meta: Optional metadata
            request_id: Optional request ID
            
        Returns:
            Dict with provider, fallback flag, model, message, usage, request_id
        """
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Select primary provider
        primary_provider = self._select_provider(language, hint, policy)
        fallback_used = False
        
        logger.info(
            f"[{request_id}] Router: "
            f"language={language}, hint={hint}, "
            f"primary={primary_provider}"
        )
        
        # Try primary provider
        if primary_provider == "mistral":
            result = self.mistral.chat(message, system, language, meta, request_id)
            
            # If Mistral failed, fallback to OpenAI
            if "error" in result:
                logger.warning(
                    f"[{request_id}] Mistral failed, falling back to OpenAI: "
                    f"{result.get('error')}"
                )
                fallback_used = True
                result = self.openai.chat(message, system, language, meta, request_id)
        else:
            result = self.openai.chat(message, system, language, meta, request_id)
            
            # If OpenAI failed, fallback to Mistral (if configured)
            if "error" in result and self.mistral.is_configured():
                logger.warning(
                    f"[{request_id}] OpenAI failed, falling back to Mistral: "
                    f"{result.get('error')}"
                )
                fallback_used = True
                result = self.mistral.chat(message, system, language, meta, request_id)
        
        # Add fallback flag to result
        result["fallback"] = fallback_used
        
        if fallback_used:
            logger.info(
                f"[{request_id}] Router fallback: "
                f"primary={primary_provider}, "
                f"actual={result.get('provider')}"
            )
            # Record fallback metric
            if "error" not in result:
                record_request(
                    result.get('provider', 'unknown'),
                    "success",
                    True,
                    result.get('latency_ms', 0)
                )
        
        return result

