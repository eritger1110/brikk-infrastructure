# -*- coding: utf-8 -*-
"""
Usage Ledger Model (Phase 6 PR-2).

Tracks API usage for metered billing and Stripe synchronization.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, Text, Integer, TIMESTAMP, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import db


class UsageLedger(db.Model):
    """
    Usage Ledger for metered billing.
    
    Records API usage per organization with cost calculation.
    Supports Stripe synchronization for invoice generation.
    """
    __tablename__ = 'usage_ledger'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Organization and Actor
    org_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    actor_id = Column(Text, nullable=False)  # API key or OAuth client ID
    
    # Optional Agent Reference
    agent_id = Column(String(36), ForeignKey('agents.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Usage Details
    route = Column(Text, nullable=False)
    usage_units = Column(Integer, nullable=False, default=1, server_default='1')
    
    # Cost Calculation
    unit_cost = Column(Numeric(10, 4), nullable=False)
    total_cost = Column(Numeric(10, 4), nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, server_default=db.func.now())
    billed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Relationships
    organization = relationship('Organization', foreign_keys=[org_id])
    agent = relationship('Agent', foreign_keys=[agent_id])
    
    # Indexes (defined in migration, documented here)
    __table_args__ = (
        Index('ix_usage_ledger_org_id', 'org_id'),
        Index('ix_usage_ledger_agent_id', 'agent_id'),
        Index('ix_usage_ledger_created_at', 'created_at'),
        Index('ix_usage_ledger_billed_at', 'billed_at'),
        Index('ix_usage_ledger_unbilled', 'org_id', 'created_at', 
              postgresql_where=db.text('billed_at IS NULL')),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': str(self.id),
            'org_id': self.org_id,
            'actor_id': self.actor_id,
            'agent_id': self.agent_id,
            'route': self.route,
            'usage_units': self.usage_units,
            'unit_cost': float(self.unit_cost),
            'total_cost': float(self.total_cost),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'billed_at': self.billed_at.isoformat() if self.billed_at else None,
        }
    
    @classmethod
    def record_usage(cls,
                     org_id: int,
                     actor_id: str,
                     route: str,
                     unit_cost: Decimal,
                     usage_units: int = 1,
                     agent_id: Optional[str] = None) -> 'UsageLedger':
        """
        Record a usage entry in the ledger.
        
        Args:
            org_id: Organization ID
            actor_id: API key or OAuth client ID
            route: API route accessed
            unit_cost: Cost per unit from tier configuration
            usage_units: Number of units consumed (default: 1)
            agent_id: Optional agent ID if agent-related
            
        Returns:
            Created UsageLedger entry
        """
        total_cost = Decimal(str(usage_units)) * unit_cost
        
        entry = cls(
            org_id=org_id,
            actor_id=actor_id,
            route=route,
            usage_units=usage_units,
            unit_cost=unit_cost,
            total_cost=total_cost,
            agent_id=agent_id
        )
        
        db.session.add(entry)
        db.session.commit()
        
        return entry
    
    @classmethod
    def get_unbilled(cls, org_id: Optional[int] = None, 
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> List['UsageLedger']:
        """
        Get unbilled usage entries.
        
        Args:
            org_id: Optional filter by organization
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of unbilled usage entries
        """
        query = cls.query.filter(cls.billed_at.is_(None))
        
        if org_id:
            query = query.filter(cls.org_id == org_id)
        
        if start_date:
            query = query.filter(cls.created_at >= start_date)
        
        if end_date:
            query = query.filter(cls.created_at <= end_date)
        
        return query.order_by(cls.created_at.asc()).all()
    
    @classmethod
    def mark_as_billed(cls, entry_ids: List[uuid.UUID]) -> int:
        """
        Mark entries as billed.
        
        Args:
            entry_ids: List of entry IDs to mark as billed
            
        Returns:
            Number of entries updated
        """
        count = cls.query.filter(cls.id.in_(entry_ids)).update(
            {'billed_at': datetime.utcnow()},
            synchronize_session=False
        )
        db.session.commit()
        return count
    
    def __repr__(self) -> str:
        return f"<UsageLedger org={self.org_id} route={self.route} cost={self.total_cost}>"

