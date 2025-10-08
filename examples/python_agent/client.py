#!/usr/bin/env python3
"""
Brikk Python Agent Client
Simple SDK for communicating with the Brikk coordination protocol.
"""

import os
import json
import time
import hmac
import hashlib
import requests
from typing import Dict, Any, Optional


class BrikkClient:
    """Simple client for Brikk coordination protocol with HMAC authentication."""
    
    def __init__(self, base_url: str = None, api_key: str = None, secret: str = None):
        self.base_url = base_url or os.getenv('BRIKK_BASE_URL', 'http://localhost:5000')
        self.api_key = api_key or os.getenv('BRIKK_API_KEY')
        self.secret = secret or os.getenv('BRIKK_SECRET')
        
        if not self.api_key or not self.secret:
            raise ValueError("BRIKK_API_KEY and BRIKK_SECRET environment variables required")
    
    def _sign_request(self, method: str, path: str, body: str = "") -> str:
        """Generate HMAC signature for request authentication."""
        timestamp = str(int(time.time()))
        message = f"{method}\n{path}\n{body}\n{timestamp}"
        signature = hmac.new(
            self.secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"{timestamp}:{signature}"
    
    def send(self, to: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a coordination message to another agent."""
        envelope = {
            "version": "1.0",
            "sender": self.api_key,
            "recipient": to,
            "payload": payload,
            "timestamp": int(time.time())
        }
        
        body = json.dumps(envelope)
        path = "/api/v1/coordination"
        auth_header = self._sign_request("POST", path, body)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"HMAC {self.api_key}:{auth_header}",
        }
        
        response = requests.post(f"{self.base_url}{path}", data=body, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def poll(self) -> Dict[str, Any]:
        """Poll for incoming messages (mock implementation)."""
        return {"status": "no_messages", "messages": []}
