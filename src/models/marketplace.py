"""
Marketplace models for Phase 7
Handles agent marketplace listings, categories, tags, and installations
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal

from src.infra.db import db
from src.models.agent import JSONList, JSONDict


class MarketplaceListing(db.Model):
    """
    Marketplace listing for an agent
    Extends agent_registry with marketplace-specific metadata
    """
    __tablename__ = 'marketplace_listings'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    publisher_id = db.Column(db.String(36), nullable=False)  # User who published
    
    # Status and visibility
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, published, archived
    visibility = db.Column(db.String(20), nullable=False, default='public')  # public, private, unlisted
    
    # Featured listing
    featured = db.Column(db.Boolean, default=False)
    featured_until = db.Column(db.DateTime)
    
    # Organization
    category = db.Column(db.String(100))
    tags = db.Column(JSONList)  # Array of tags
    
    # Description and media
    short_description = db.Column(db.Text)
    long_description = db.Column(db.Text)
    icon_url = db.Column(db.Text)
    screenshots = db.Column(JSONList)  # Array of screenshot URLs
    demo_url = db.Column(db.Text)
    documentation_url = db.Column(db.Text)
    source_code_url = db.Column(db.Text)
    
    # Licensing
    license = db.Column(db.String(50))  # MIT, Apache, Proprietary, etc.
    
    # Pricing
    pricing_model = db.Column(db.String(20), default='free')  # free, paid, freemium
    price_amount = db.Column(db.Numeric(10, 2))
    price_currency = db.Column(db.String(3), default='USD')
    
    # Metrics
    install_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    agent = db.relationship('Agent', backref='marketplace_listing', lazy=True)
    installations = db.relationship('AgentInstallation', backref='listing', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert listing to dictionary"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'publisher_id': self.publisher_id,
            'status': self.status,
            'visibility': self.visibility,
            'featured': self.featured,
            'featured_until': self.featured_until.isoformat() if self.featured_until else None,
            'category': self.category,
            'tags': self.tags or [],
            'short_description': self.short_description,
            'long_description': self.long_description,
            'icon_url': self.icon_url,
            'screenshots': self.screenshots or [],
            'demo_url': self.demo_url,
            'documentation_url': self.documentation_url,
            'source_code_url': self.source_code_url,
            'license': self.license,
            'pricing_model': self.pricing_model,
            'price_amount': float(self.price_amount) if self.price_amount else None,
            'price_currency': self.price_currency,
            'install_count': self.install_count,
            'view_count': self.view_count,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def increment_views(self):
        """Increment view count"""
        self.view_count = (self.view_count or 0) + 1
        db.session.commit()
    
    def increment_installs(self):
        """Increment install count"""
        self.install_count = (self.install_count or 0) + 1
        db.session.commit()
    
    def publish(self):
        """Publish the listing"""
        self.status = 'published'
        self.published_at = datetime.now(timezone.utc)
        db.session.commit()
    
    def archive(self):
        """Archive the listing"""
        self.status = 'archived'
        db.session.commit()


class AgentCategory(db.Model):
    """Agent categories for organization"""
    __tablename__ = 'agent_categories'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Icon identifier
    parent_id = db.Column(db.String(36), db.ForeignKey('agent_categories.id'))
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Self-referential relationship for hierarchy
    children = db.relationship('AgentCategory', backref=db.backref('parent', remote_side=[id]))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert category to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'icon': self.icon,
            'parent_id': self.parent_id,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AgentTag(db.Model):
    """Tags for agent discovery"""
    __tablename__ = 'agent_tags'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(50), nullable=False, unique=True)
    slug = db.Column(db.String(50), nullable=False, unique=True)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tag to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count = (self.usage_count or 0) + 1
        db.session.commit()


class AgentInstallation(db.Model):
    """Track agent installations by users"""
    __tablename__ = 'agent_installations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False)
    user_id = db.Column(db.String(36), nullable=False)
    installed_version = db.Column(db.String(50))
    installed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = db.Column(db.DateTime)
    uninstalled_at = db.Column(db.DateTime)
    
    # Unique constraint: one installation per user per agent
    __table_args__ = (
        db.UniqueConstraint('agent_id', 'user_id', name='uq_agent_user_installation'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert installation to dictionary"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'user_id': self.user_id,
            'installed_version': self.installed_version,
            'installed_at': self.installed_at.isoformat() if self.installed_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'uninstalled_at': self.uninstalled_at.isoformat() if self.uninstalled_at else None,
            'is_active': self.uninstalled_at is None,
        }
    
    def uninstall(self):
        """Mark as uninstalled"""
        self.uninstalled_at = datetime.now(timezone.utc)
        db.session.commit()
    
    def update_last_used(self):
        """Update last used timestamp"""
        self.last_used_at = datetime.now(timezone.utc)
        db.session.commit()

