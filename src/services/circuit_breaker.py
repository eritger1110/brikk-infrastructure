# -*- coding: utf-8 -*-
"""
Circuit breaker implementation for provider resilience
Part of Phase 10-12: Production-ready resilience
"""

import time
from enum import Enum
from typing import Callable, Any
from functools import wraps


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Lightweight circuit breaker for provider calls.
    Prevents cascading failures by failing fast when a service is down.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call a function through the circuit breaker.
        
        Args:
            func: Function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
        
        Returns:
            Function result
        
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def reset(self):
        """Manually reset circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
        }


# Global circuit breakers for each provider
_circuit_breakers = {}


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    """Get or create circuit breaker for a provider"""
    if provider not in _circuit_breakers:
        _circuit_breakers[provider] = CircuitBreaker(
            name=f"{provider}_circuit",
            failure_threshold=5,
            recovery_timeout=60
        )
    return _circuit_breakers[provider]


def circuit_breaker(provider: str):
    """
    Decorator to wrap a function with circuit breaker protection.
    
    Usage:
        @circuit_breaker('openai')
        def call_openai_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cb = get_circuit_breaker(provider)
            return cb.call(func, *args, **kwargs)
        return wrapper
    return decorator


def get_all_circuit_states() -> dict:
    """Get states of all circuit breakers"""
    return {
        name: cb.get_state()
        for name, cb in _circuit_breakers.items()
    }

