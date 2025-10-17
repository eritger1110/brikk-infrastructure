"""
Feature Flags System

Provides a simple, flexible feature flag system for enabling/disabling features
dynamically without code deployments.

Features:
- Environment variable-based configuration
- Redis-backed dynamic flags (optional)
- Default values for safety
- Easy-to-use API
- Type-safe flag definitions

Usage:
    from src.utils.feature_flags import is_enabled, FeatureFlag

    if is_enabled(FeatureFlag.AGENT_REGISTRY):
        # Feature is enabled
        pass

Environment Variables:
    FEATURE_FLAG_<NAME>=true|false  - Override flag value
    REDIS_URL=redis://...           - Enable Redis-backed flags (optional)
"""

import os
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FeatureFlag(str, Enum):
    """
    Centralized feature flag definitions.
    
    Add new flags here with descriptive names and default values.
    """
    # Phase 6: Agent Registry
    AGENT_REGISTRY = "agent_registry"
    AGENT_DISCOVERY = "agent_discovery"
    AGENT_VERSIONING = "agent_versioning"
    
    # Phase 7: Planned features
    AGENT_MARKETPLACE = "agent_marketplace"
    AGENT_ANALYTICS = "agent_analytics"
    ENHANCED_DISCOVERY = "enhanced_discovery"
    REVIEWS_RATINGS = "reviews_ratings"
    
    # Infrastructure features
    RATE_LIMITING = "rate_limiting"
    CACHING = "caching"
    METRICS = "metrics"
    
    # Development features
    DEBUG_MODE = "debug_mode"
    VERBOSE_LOGGING = "verbose_logging"


# Default flag values (can be overridden by environment variables or Redis)
DEFAULT_FLAGS = {
    # Phase 6 features - enabled by default
    FeatureFlag.AGENT_REGISTRY: True,
    FeatureFlag.AGENT_DISCOVERY: True,
    FeatureFlag.AGENT_VERSIONING: True,
    
    # Phase 7 features - disabled by default
    FeatureFlag.AGENT_MARKETPLACE: False,
    FeatureFlag.AGENT_ANALYTICS: False,
    FeatureFlag.ENHANCED_DISCOVERY: False,
    FeatureFlag.REVIEWS_RATINGS: False,
    
    # Infrastructure - enabled by default
    FeatureFlag.RATE_LIMITING: True,
    FeatureFlag.CACHING: True,
    FeatureFlag.METRICS: True,
    
    # Development - disabled by default in production
    FeatureFlag.DEBUG_MODE: False,
    FeatureFlag.VERBOSE_LOGGING: False,
}


class FeatureFlagManager:
    """
    Manages feature flags with support for environment variables and Redis.
    """
    
    def __init__(self, redis_client: Optional[object] = None):
        """
        Initialize the feature flag manager.
        
        Args:
            redis_client: Optional Redis client for dynamic flags
        """
        self.redis_client = redis_client
        self._cache = {}
        
        if redis_client:
            logger.info("Feature flags initialized with Redis backend")
        else:
            logger.info("Feature flags initialized with environment variables only")
    
    def is_enabled(self, flag: FeatureFlag) -> bool:
        """
        Check if a feature flag is enabled.
        
        Priority order:
        1. Environment variable (FEATURE_FLAG_<NAME>=true|false)
        2. Redis value (if Redis is configured)
        3. Default value
        
        Args:
            flag: The feature flag to check
            
        Returns:
            True if the feature is enabled, False otherwise
        """
        # Check environment variable first
        env_key = f"FEATURE_FLAG_{flag.value.upper()}"
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            result = env_value.lower() in ("true", "1", "yes", "on")
            logger.debug(f"Feature flag {flag.value} from env: {result}")
            return result
        
        # Check Redis if available
        if self.redis_client:
            try:
                redis_key = f"feature_flag:{flag.value}"
                redis_value = self.redis_client.get(redis_key)
                
                if redis_value is not None:
                    result = redis_value.decode("utf-8").lower() in ("true", "1", "yes", "on")
                    logger.debug(f"Feature flag {flag.value} from Redis: {result}")
                    return result
            except Exception as e:
                logger.warning(f"Failed to get feature flag {flag.value} from Redis: {e}")
        
        # Fall back to default value
        result = DEFAULT_FLAGS.get(flag, False)
        logger.debug(f"Feature flag {flag.value} from default: {result}")
        return result
    
    def set_flag(self, flag: FeatureFlag, enabled: bool, ttl: Optional[int] = None) -> bool:
        """
        Set a feature flag value in Redis.
        
        Note: This only works if Redis is configured. Environment variables
        take precedence and cannot be overridden.
        
        Args:
            flag: The feature flag to set
            enabled: Whether to enable or disable the feature
            ttl: Optional time-to-live in seconds
            
        Returns:
            True if the flag was set successfully, False otherwise
        """
        if not self.redis_client:
            logger.warning(f"Cannot set feature flag {flag.value}: Redis not configured")
            return False
        
        try:
            redis_key = f"feature_flag:{flag.value}"
            value = "true" if enabled else "false"
            
            if ttl:
                self.redis_client.setex(redis_key, ttl, value)
            else:
                self.redis_client.set(redis_key, value)
            
            logger.info(f"Feature flag {flag.value} set to {enabled} (TTL: {ttl})")
            return True
        except Exception as e:
            logger.error(f"Failed to set feature flag {flag.value}: {e}")
            return False
    
    def get_all_flags(self) -> dict:
        """
        Get the current state of all feature flags.
        
        Returns:
            Dictionary mapping flag names to their current values
        """
        return {
            flag.value: self.is_enabled(flag)
            for flag in FeatureFlag
        }


# Global instance (initialized by application factory)
_manager: Optional[FeatureFlagManager] = None


def init_feature_flags(redis_client: Optional[object] = None):
    """
    Initialize the global feature flag manager.
    
    This should be called once during application startup.
    
    Args:
        redis_client: Optional Redis client for dynamic flags
    """
    global _manager
    _manager = FeatureFlagManager(redis_client)
    logger.info("Feature flags system initialized")


def is_enabled(flag: FeatureFlag) -> bool:
    """
    Check if a feature flag is enabled.
    
    This is a convenience function that uses the global manager instance.
    
    Args:
        flag: The feature flag to check
        
    Returns:
        True if the feature is enabled, False otherwise
    """
    if _manager is None:
        # Auto-initialize if not already done
        init_feature_flags()
    
    return _manager.is_enabled(flag)


def set_flag(flag: FeatureFlag, enabled: bool, ttl: Optional[int] = None) -> bool:
    """
    Set a feature flag value.
    
    This is a convenience function that uses the global manager instance.
    
    Args:
        flag: The feature flag to set
        enabled: Whether to enable or disable the feature
        ttl: Optional time-to-live in seconds
        
        Returns:
            True if the flag was set successfully, False otherwise
    """
    if _manager is None:
        init_feature_flags()
    
    return _manager.set_flag(flag, enabled, ttl)


def get_all_flags() -> dict:
    """
    Get the current state of all feature flags.
    
    Returns:
        Dictionary mapping flag names to their current values
    """
    if _manager is None:
        init_feature_flags()
    
    return _manager.get_all_flags()

