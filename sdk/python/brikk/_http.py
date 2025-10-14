# -*- coding: utf-8 -*-
"""Synchronous HTTP client for Brikk SDK."""

import time
import hmac
import hashlib
import json
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .errors import (
    AuthError,
    HTTPError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)


class HTTPClient:
    """Synchronous HTTP client with retry logic and error handling."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        signing_secret: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.signing_secret = signing_secret
        self.timeout = timeout

        # Create session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        if path.startswith("http"):
            return path
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _generate_hmac_signature(self, timestamp: str, body: str) -> str:
        """Generate HMAC-SHA256 signature for request."""
        if not self.signing_secret:
            raise AuthError("Signing secret required for HMAC authentication")
        message = f"{timestamp}.{body}".encode("utf-8")
        return hmac.new(
            self.signing_secret.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle HTTP response and raise appropriate errors."""
        try:
            data = response.json() if response.content else {}
        except json.JSONDecodeError:
            data = {"text": response.text}

        if response.status_code == 200 or response.status_code == 201:
            return data

        error_msg = data.get("error", f"HTTP {response.status_code}")

        if response.status_code == 400:
            raise ValidationError(error_msg, response.status_code, response)
        elif response.status_code == 401 or response.status_code == 403:
            raise AuthError(error_msg, response.status_code, response)
        elif response.status_code == 404:
            raise NotFoundError(error_msg, response.status_code, response)
        elif response.status_code == 429:
            raise RateLimitError(error_msg, response.status_code, response)
        elif response.status_code >= 500:
            raise ServerError(error_msg, response.status_code, response)
        else:
            raise HTTPError(error_msg, response.status_code, response)

    def request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_hmac: bool = False,
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling and retries."""
        url = self._build_url(path)
        request_headers = headers or {}

        # Add authentication headers
        if use_hmac and self.signing_secret:
            timestamp = str(int(time.time()))
            body = json.dumps(json_data) if json_data else ""
            signature = self._generate_hmac_signature(timestamp, body)
            request_headers.update({
                "X-Brikk-Key": self.api_key or "",
                "X-Brikk-Timestamp": timestamp,
                "X-Brikk-Signature": signature,
            })
        elif self.api_key:
            request_headers["Authorization"] = f"Bearer {self.api_key}"

        if json_data:
            request_headers["Content-Type"] = "application/json"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                headers=request_headers,
                timeout=self.timeout,
            )
            return self._handle_response(response)
        except requests.Timeout as e:
            raise TimeoutError(f"Request timed out after {self.timeout}s") from e
        except requests.RequestException as e:
            raise HTTPError(f"Request failed: {str(e)}") from e

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request."""
        return self.request("GET", path, params=params)

    def post(
        self,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        use_hmac: bool = False,
    ) -> Dict[str, Any]:
        """Make POST request."""
        return self.request("POST", path, json_data=json_data, use_hmac=use_hmac)

    def put(
        self,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make PUT request."""
        return self.request("PUT", path, json_data=json_data)

    def delete(self, path: str) -> Dict[str, Any]:
        """Make DELETE request."""
        return self.request("DELETE", path)

