# src/models/__init__.py
# Make models a regular package so modules load once
from src.database.db import db  # optional convenience re-export

# Export models here so db.create_all() (or any imports) can see them.
from .agent import Agent          # noqa: F401
from .customer_profile import CustomerProfile  # if you have/need it  # noqa: F401
from .purchase import Purchase     # if you have/need it              # noqa: F401
from .user import User             # if you have/need it              # noqa: F401
from .audit_log import AuditLog    # NEW                              # noqa: F401
