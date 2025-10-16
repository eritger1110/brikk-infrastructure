# -*- coding: utf-8 -*-
"""
Pricing Configuration (Phase 6 PR-2).

Defines per-call pricing for different tiers.
Supports environment-based overrides via BRIKK_PRICING_JSON.
"""
import os
import json
from decimal import Decimal
from typing import Dict, Optional

# Default pricing per API call by tier
DEFAULT_TIER_PRICING = {
    'FREE': Decimal('0.0000'),      # Free tier: no charge
    'HACKER': Decimal('0.0050'),    # $0.005 per call
    'STARTER': Decimal('0.0100'),   # $0.01 per call (standard rate)
    'PRO': Decimal('0.0075'),       # $0.0075 per call (volume discount)
    'ENT': Decimal('0.0050'),       # $0.005 per call (enterprise discount)
    'INTERNAL': Decimal('0.0000'),  # Internal/HMAC: no charge
    'DEFAULT': Decimal('0.0100'),   # Default: $0.01 per call
}

# Load pricing overrides from environment if available
def load_pricing_config() -> Dict[str, Decimal]:
    """
    Load pricing configuration with optional environment overrides.
    
    Returns:
        Dictionary of tier -> unit_cost mappings
    """
    pricing = DEFAULT_TIER_PRICING.copy()
    
    # Check for environment override
    pricing_json = os.getenv('BRIKK_PRICING_JSON')
    if pricing_json:
        try:
            overrides = json.loads(pricing_json)
            for tier, cost in overrides.items():
                pricing[tier] = Decimal(str(cost))
        except (json.JSONDecodeError, ValueError) as e:
            # Log error but continue with defaults
            print(f"Warning: Failed to parse BRIKK_PRICING_JSON: {e}")
    
    return pricing


# Global pricing configuration
TIER_PRICING = load_pricing_config()


def get_unit_cost(tier: Optional[str] = None) -> Decimal:
    """
    Get unit cost for a tier.
    
    Args:
        tier: Tier name (FREE, HACKER, STARTER, PRO, ENT, INTERNAL)
        
    Returns:
        Unit cost as Decimal
    """
    if not tier or tier not in TIER_PRICING:
        return TIER_PRICING['DEFAULT']
    
    return TIER_PRICING[tier]


def calculate_cost(tier: Optional[str], usage_units: int = 1) -> Decimal:
    """
    Calculate total cost for usage.
    
    Args:
        tier: Tier name
        usage_units: Number of units consumed
        
    Returns:
        Total cost as Decimal
    """
    unit_cost = get_unit_cost(tier)
    return unit_cost * Decimal(str(usage_units))

