"""
OpenAI service for Brikk platform.
Provides chat completions via OpenAI API with graceful error handling.
"""

import os
import uuid
import time
import logging
import requests
from typing import Dict, Any, Optional
from src.services.provider_metrics import record_request, update_provider_availability

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for interacting with OpenAI API."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.api_base = "https://api.openai.com/v1"
        self.timeout = 30
        
    def is_configured(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.api_key)
    
    def chat(
        self,
        message: str,
        system: Optional[str] = None,
        language: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to OpenAI API.
        
        Args:
            message: User message
            system: Optional system message
            language: Optional language hint (en, es, ja, ar)
            meta: Optional metadata
            request_id: Optional request ID for tracking
            
        Returns:
            Dict with provider, model, message, usage, request_id, and optional error
        """
        if not request_id:
            request_id = str(uuid.uuid4())
            
        start_time = time.time()
        
        # Check if configured
        if not self.is_configured():
            logger.warning(f"[{request_id}] OpenAI API key not configured")
            return {
                "error": "OPENAI_API_KEY not configured",
                "provider": "openai",
                "model": self.model,
                "request_id": request_id,
                "latency_ms": int((time.time() - start_time) * 1000)
            }
        
        # Build messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        else:
            messages.append({"role": "system", "content": "You are a helpful AI assistant."})
        messages.append({"role": "user", "content": message})
        
        # Prepare request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        try:
            logger.info(f"[{request_id}] OpenAI request: model={self.model}, language={language}")
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                
                logger.info(
                    f"[{request_id}] OpenAI success: "
                    f"latency={latency_ms}ms, "
                    f"tokens={usage.get('total_tokens', 0)}"
                )
                
                # Record metrics
                record_request("openai", "success", False, latency_ms)
                update_provider_availability("openai", True)
                
                return {
                    "provider": "openai",
                    "model": self.model,
                    "message": content,
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    },
                    "request_id": request_id,
                    "latency_ms": latency_ms
                }
            else:
                error_text = response.text
                logger.error(
                    f"[{request_id}] OpenAI error: "
                    f"status={response.status_code}, "
                    f"error={error_text}"
                )
                
                # Record metrics
                record_request("openai", "error", False, latency_ms)
                update_provider_availability("openai", False)
                
                return {
                    "error": f"OpenAI API error: {response.status_code}",
                    "error_details": error_text,
                    "provider": "openai",
                    "model": self.model,
                    "request_id": request_id,
                    "latency_ms": latency_ms
                }
                
        except requests.exceptions.Timeout:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{request_id}] OpenAI timeout after {latency_ms}ms")
            return {
                "error": "OpenAI API timeout",
                "provider": "openai",
                "model": self.model,
                "request_id": request_id,
                "latency_ms": latency_ms
            }
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{request_id}] OpenAI exception: {str(e)}")
            return {
                "error": f"OpenAI API exception: {str(e)}",
                "provider": "openai",
                "model": self.model,
                "request_id": request_id,
                "latency_ms": latency_ms
            }

