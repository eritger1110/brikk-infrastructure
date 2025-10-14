# -*- coding: utf-8 -*-
"""Resource modules for Brikk SDK."""

from .health import HealthResource
from .agents import AgentsResource
from .coordination import CoordinationResource
from .economy import EconomyResource
from .reputation import ReputationResource

__all__ = [
    "HealthResource",
    "AgentsResource",
    "CoordinationResource",
    "EconomyResource",
    "ReputationResource",
]

