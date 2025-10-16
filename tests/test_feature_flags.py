"""
Tests for Feature Flags System
"""

import pytest
import os
from src.utils.feature_flags import (
    FeatureFlag,
    FeatureFlagManager,
    is_enabled,
    init_feature_flags,
    get_all_flags,
)


class TestFeatureFlagManager:
    """Tests for FeatureFlagManager class"""
    
    def test_default_values(self):
        """Test that default values are returned when no overrides exist"""
        manager = FeatureFlagManager()
        
        # Phase 6 features should be enabled by default
        assert manager.is_enabled(FeatureFlag.AGENT_REGISTRY) is True
        assert manager.is_enabled(FeatureFlag.AGENT_DISCOVERY) is True
        
        # Phase 7 features should be disabled by default
        assert manager.is_enabled(FeatureFlag.AGENT_MARKETPLACE) is False
        assert manager.is_enabled(FeatureFlag.AGENT_ANALYTICS) is False
    
    def test_environment_variable_override(self, monkeypatch):
        """Test that environment variables override default values"""
        # Override a flag that's enabled by default
        monkeypatch.setenv("FEATURE_FLAG_AGENT_REGISTRY", "false")
        
        # Override a flag that's disabled by default
        monkeypatch.setenv("FEATURE_FLAG_AGENT_MARKETPLACE", "true")
        
        manager = FeatureFlagManager()
        
        assert manager.is_enabled(FeatureFlag.AGENT_REGISTRY) is False
        assert manager.is_enabled(FeatureFlag.AGENT_MARKETPLACE) is True
    
    def test_environment_variable_formats(self, monkeypatch):
        """Test different environment variable value formats"""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ]
        
        for value, expected in test_cases:
            monkeypatch.setenv("FEATURE_FLAG_DEBUG_MODE", value)
            manager = FeatureFlagManager()
            assert manager.is_enabled(FeatureFlag.DEBUG_MODE) is expected
    
    def test_get_all_flags(self):
        """Test getting all flags at once"""
        manager = FeatureFlagManager()
        all_flags = manager.get_all_flags()
        
        # Should return a dictionary
        assert isinstance(all_flags, dict)
        
        # Should include all defined flags
        assert len(all_flags) == len(FeatureFlag)
        
        # Should have string keys and boolean values
        for key, value in all_flags.items():
            assert isinstance(key, str)
            assert isinstance(value, bool)


class TestGlobalFunctions:
    """Tests for global convenience functions"""
    
    def test_is_enabled_auto_initializes(self):
        """Test that is_enabled() auto-initializes if needed"""
        # This should not raise an error even if not explicitly initialized
        result = is_enabled(FeatureFlag.AGENT_REGISTRY)
        assert isinstance(result, bool)
    
    def test_init_feature_flags(self):
        """Test explicit initialization"""
        init_feature_flags()
        result = is_enabled(FeatureFlag.AGENT_REGISTRY)
        assert isinstance(result, bool)
    
    def test_get_all_flags_global(self):
        """Test global get_all_flags function"""
        all_flags = get_all_flags()
        assert isinstance(all_flags, dict)
        assert len(all_flags) > 0


class TestFeatureFlagEnum:
    """Tests for FeatureFlag enum"""
    
    def test_flag_values_are_strings(self):
        """Test that all flag values are strings"""
        for flag in FeatureFlag:
            assert isinstance(flag.value, str)
            assert len(flag.value) > 0
    
    def test_flag_names_are_descriptive(self):
        """Test that flag names follow naming conventions"""
        for flag in FeatureFlag:
            # Should be lowercase with underscores
            assert flag.value == flag.value.lower()
            assert " " not in flag.value

