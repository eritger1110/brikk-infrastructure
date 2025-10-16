# -*- coding: utf-8 -*-
"""
API Version Configuration (Phase 6 PR-J).

Centralized version management for the Brikk API Gateway.
"""

# Semantic version of the API
API_VERSION = '1.0.0'

# Revision/phase identifier
API_REVISION = 'phase-6'

# Version history for deprecation tracking
VERSION_HISTORY = {
    '1.0.0': {
        'released': '2025-10-16',
        'phase': 'phase-6',
        'features': [
            'Agent Registry',
            'Usage Metering',
            'Rate Limiting',
            'OAuth2 Authentication',
            'Telemetry & Observability'
        ],
        'deprecated': [],
        'removed': []
    }
}

# Supported API versions (for future multi-version support)
SUPPORTED_VERSIONS = ['1.0.0']

# Minimum client version recommendations
MIN_CLIENT_VERSIONS = {
    'python-sdk': '0.1.0',
    'node-sdk': '0.1.0',
    'cli': '0.1.0'
}

