# -*- coding: utf-8 -*-
"""
API Key Service for managing API keys with Stripe integration.
"""
from typing import Dict, Optional
from src.models.api_key import ApiKey
from src.infra.db import db


class APIKeyService:
    """Service for creating and managing API keys."""
    
    @staticmethod
    def create_key(
        user_id: int,
        name: str,
        tier: str = 'free',
        stripe_subscription_id: Optional[str] = None,
        organization_id: Optional[int] = None,
        agent_id: Optional[str] = None,
        description: Optional[str] = None,
        expires_days: Optional[int] = None
    ) -> Dict:
        """
        Create a new API key for a user.
        
        Args:
            user_id: User ID
            name: Human-readable name for the key
            tier: Subscription tier (free, starter, pro, hacker)
            stripe_subscription_id: Stripe subscription ID
            organization_id: Optional organization ID
            agent_id: Optional agent ID
            description: Optional description
            expires_days: Optional expiration in days
            
        Returns:
            Dict with 'api_key' (plaintext, one-time only) and 'key_id'
        """
        try:
            # Create the API key using the model's class method
            api_key_record, plaintext_key = ApiKey.create_api_key(
                organization_id=organization_id or 0,  # Temporary: use 0 if no org
                name=name,
                description=description,
                agent_id=agent_id,
                expires_days=expires_days
            )
            
            # Update with Stripe and tier info
            api_key_record.user_id = user_id
            api_key_record.tier = tier
            api_key_record.stripe_subscription_id = stripe_subscription_id
            
            # Set budget caps based on tier
            caps = APIKeyService.get_tier_caps(tier)
            api_key_record.soft_cap_usd = caps['soft_cap']
            api_key_record.hard_cap_usd = caps['hard_cap']
            api_key_record.requests_per_minute = caps['rpm']
            api_key_record.requests_per_hour = caps['rph']
            
            db.session.commit()
            
            return {
                'api_key': plaintext_key,
                'key_id': api_key_record.key_id,
                'tier': tier,
                'created_at': api_key_record.created_at.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}
    
    @staticmethod
    def get_tier_caps(tier: str) -> Dict:
        """
        Get budget caps and rate limits for a tier.
        
        Returns:
            Dict with soft_cap, hard_cap, rpm, rph
        """
        tiers = {
            'free': {
                'soft_cap': 5.00,
                'hard_cap': 10.00,
                'rpm': 10,
                'rph': 100
            },
            'starter': {
                'soft_cap': 50.00,
                'hard_cap': 100.00,
                'rpm': 100,
                'rph': 1000
            },
            'pro': {
                'soft_cap': 250.00,
                'hard_cap': 500.00,
                'rpm': 500,
                'rph': 5000
            },
            'hacker': {
                'soft_cap': 500.00,
                'hard_cap': 1000.00,
                'rpm': 1000,
                'rph': 10000
            }
        }
        
        return tiers.get(tier, tiers['free'])

