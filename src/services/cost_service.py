# -*- coding: utf-8 -*-
"""
Cost calculation service for Brikk API
Server-side cost calculation for usage-based billing
Part of Phase 10-12: Production-ready billing
"""

from decimal import Decimal
from typing import Dict

# Cost per 1M tokens (as of 2025-10-26)
COST_PER_MILLION_TOKENS = {
    'openai': {
        'gpt-4o-mini': {
            'input': Decimal('0.15'),    # $0.15 per 1M input tokens
            'output': Decimal('0.60'),   # $0.60 per 1M output tokens
        },
        'gpt-4o': {
            'input': Decimal('5.00'),
            'output': Decimal('15.00'),
        },
        'gpt-3.5-turbo': {
            'input': Decimal('0.50'),
            'output': Decimal('1.50'),
        },
    },
    'mistral': {
        'mistral-small-latest': {
            'input': Decimal('0.10'),    # $0.10 per 1M input tokens
            'output': Decimal('0.30'),   # $0.30 per 1M output tokens
        },
        'mistral-medium-latest': {
            'input': Decimal('2.70'),
            'output': Decimal('8.10'),
        },
        'mistral-large-latest': {
            'input': Decimal('4.00'),
            'output': Decimal('12.00'),
        },
    },
}


def calc_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    """
    Calculate cost for a request based on provider, model, and token usage.
    
    Args:
        provider: Provider name (openai, mistral)
        model: Model name (gpt-4o-mini, mistral-small-latest, etc.)
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
    
    Returns:
        Cost in USD as Decimal, rounded to 6 decimal places
    """
    provider = provider.lower()
    
    # Get pricing for provider and model
    if provider not in COST_PER_MILLION_TOKENS:
        # Unknown provider - return 0 cost
        return Decimal('0')
    
    provider_pricing = COST_PER_MILLION_TOKENS[provider]
    
    if model not in provider_pricing:
        # Unknown model - try to find a default or return 0
        # For OpenAI, default to gpt-4o-mini pricing
        if provider == 'openai':
            model_pricing = provider_pricing.get('gpt-4o-mini', {})
        # For Mistral, default to mistral-small-latest pricing
        elif provider == 'mistral':
            model_pricing = provider_pricing.get('mistral-small-latest', {})
        else:
            return Decimal('0')
    else:
        model_pricing = provider_pricing[model]
    
    # Calculate cost
    input_cost_per_token = model_pricing.get('input', Decimal('0')) / Decimal('1000000')
    output_cost_per_token = model_pricing.get('output', Decimal('0')) / Decimal('1000000')
    
    input_cost = Decimal(prompt_tokens) * input_cost_per_token
    output_cost = Decimal(completion_tokens) * output_cost_per_token
    
    total_cost = input_cost + output_cost
    
    # Round to 6 decimal places (microdollars)
    return total_cost.quantize(Decimal('0.000001'))


def get_pricing_info() -> Dict:
    """
    Get pricing information for all providers and models.
    Useful for displaying pricing to users.
    """
    pricing_info = {}
    
    for provider, models in COST_PER_MILLION_TOKENS.items():
        pricing_info[provider] = {}
        for model, costs in models.items():
            pricing_info[provider][model] = {
                'input_per_1m': float(costs['input']),
                'output_per_1m': float(costs['output']),
            }
    
    return pricing_info


def estimate_max_cost(provider: str, model: str, prompt_length: int, max_tokens: int = 500) -> Decimal:
    """
    Estimate maximum cost for a request based on prompt length and max output tokens.
    Useful for budget pre-checks.
    
    Args:
        provider: Provider name
        model: Model name
        prompt_length: Approximate number of characters in prompt (will estimate tokens)
        max_tokens: Maximum completion tokens
    
    Returns:
        Estimated maximum cost in USD
    """
    # Rough estimation: 1 token ~ 4 characters
    estimated_prompt_tokens = prompt_length // 4
    
    return calc_cost(provider, model, estimated_prompt_tokens, max_tokens)


# Example usage and tests
if __name__ == '__main__':
    # Test OpenAI pricing
    cost = calc_cost('openai', 'gpt-4o-mini', 1000, 500)
    print(f"OpenAI gpt-4o-mini (1000 input, 500 output): ${cost}")
    
    # Test Mistral pricing
    cost = calc_cost('mistral', 'mistral-small-latest', 1000, 500)
    print(f"Mistral small (1000 input, 500 output): ${cost}")
    
    # Test unknown model (should default)
    cost = calc_cost('openai', 'unknown-model', 1000, 500)
    print(f"OpenAI unknown model (1000 input, 500 output): ${cost}")
    
    # Get all pricing info
    pricing = get_pricing_info()
    print(f"\nAll pricing: {pricing}")

