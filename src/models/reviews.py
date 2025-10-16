"""
Review and rating models for Phase 7
Handles agent reviews, ratings, and community feedback
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from decimal import Decimal

from src.infra.db import db


class AgentReview(db.Model):
    """
    User reviews and ratings for agents
    """
    __tablename__ = 'agent_reviews'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False)
    user_id = db.Column(db.String(36), nullable=False)
    
    # Rating and review content
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    title = db.Column(db.String(200))
    review_text = db.Column(db.Text)
    
    # Verification and helpfulness
    verified_user = db.Column(db.Boolean, default=False)  # User has actually used the agent
    helpful_count = db.Column(db.Integer, default=0)
    unhelpful_count = db.Column(db.Integer, default=0)
    
    # Moderation
    flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.Text)
    
    # Publisher response
    publisher_response = db.Column(db.Text)
    publisher_response_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Unique constraint: one review per user per agent
    __table_args__ = (
        db.UniqueConstraint('agent_id', 'user_id', name='uq_agent_user_review'),
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )
    
    # Relationships
    agent = db.relationship('Agent', backref='reviews', lazy=True)
    votes = db.relationship('ReviewVote', backref='review', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, include_votes: bool = False) -> Dict[str, Any]:
        """Convert review to dictionary"""
        result = {
            'id': self.id,
            'agent_id': self.agent_id,
            'user_id': self.user_id,
            'rating': self.rating,
            'title': self.title,
            'review_text': self.review_text,
            'verified_user': self.verified_user,
            'helpful_count': self.helpful_count,
            'unhelpful_count': self.unhelpful_count,
            'helpfulness_score': self.helpfulness_score,
            'flagged': self.flagged,
            'has_publisher_response': self.publisher_response is not None,
            'publisher_response': self.publisher_response,
            'publisher_response_at': self.publisher_response_at.isoformat() if self.publisher_response_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_votes:
            result['votes'] = [vote.to_dict() for vote in self.votes]
        
        return result
    
    @property
    def helpfulness_score(self) -> float:
        """
        Calculate helpfulness score
        Returns value between -1.0 and 1.0
        """
        total_votes = (self.helpful_count or 0) + (self.unhelpful_count or 0)
        if total_votes == 0:
            return 0.0
        
        helpful = self.helpful_count or 0
        unhelpful = self.unhelpful_count or 0
        
        return (helpful - unhelpful) / total_votes
    
    def add_helpful_vote(self):
        """Increment helpful count"""
        self.helpful_count = (self.helpful_count or 0) + 1
        db.session.commit()
    
    def remove_helpful_vote(self):
        """Decrement helpful count"""
        self.helpful_count = max(0, (self.helpful_count or 0) - 1)
        db.session.commit()
    
    def add_unhelpful_vote(self):
        """Increment unhelpful count"""
        self.unhelpful_count = (self.unhelpful_count or 0) + 1
        db.session.commit()
    
    def remove_unhelpful_vote(self):
        """Decrement unhelpful count"""
        self.unhelpful_count = max(0, (self.unhelpful_count or 0) - 1)
        db.session.commit()
    
    def flag(self, reason: str):
        """Flag review for moderation"""
        self.flagged = True
        self.flag_reason = reason
        db.session.commit()
    
    def unflag(self):
        """Remove flag from review"""
        self.flagged = False
        self.flag_reason = None
        db.session.commit()
    
    def add_publisher_response(self, response: str):
        """Add publisher response to review"""
        self.publisher_response = response
        self.publisher_response_at = datetime.now(timezone.utc)
        db.session.commit()


class ReviewVote(db.Model):
    """
    Helpfulness votes on reviews
    """
    __tablename__ = 'review_votes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = db.Column(db.String(36), db.ForeignKey('agent_reviews.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.String(36), nullable=False)
    vote = db.Column(db.String(10), nullable=False)  # 'helpful' or 'unhelpful'
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Unique constraint: one vote per user per review
    __table_args__ = (
        db.UniqueConstraint('review_id', 'user_id', name='uq_review_user_vote'),
        db.CheckConstraint("vote IN ('helpful', 'unhelpful')", name='check_vote_type'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert vote to dictionary"""
        return {
            'id': self.id,
            'review_id': self.review_id,
            'user_id': self.user_id,
            'vote': self.vote,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AgentRatingSummary(db.Model):
    """
    Aggregated rating summary for agents
    Pre-computed for performance
    """
    __tablename__ = 'agent_rating_summary'
    
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id', ondelete='CASCADE'), primary_key=True)
    
    # Aggregate metrics
    total_reviews = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Numeric(3, 2), default=0.0)
    
    # Rating distribution
    rating_1_count = db.Column(db.Integer, default=0)
    rating_2_count = db.Column(db.Integer, default=0)
    rating_3_count = db.Column(db.Integer, default=0)
    rating_4_count = db.Column(db.Integer, default=0)
    rating_5_count = db.Column(db.Integer, default=0)
    
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    agent = db.relationship('Agent', backref='rating_summary', lazy=True, uselist=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rating summary to dictionary"""
        return {
            'agent_id': self.agent_id,
            'total_reviews': self.total_reviews,
            'average_rating': float(self.average_rating) if self.average_rating else 0.0,
            'rating_distribution': {
                '1': self.rating_1_count,
                '2': self.rating_2_count,
                '3': self.rating_3_count,
                '4': self.rating_4_count,
                '5': self.rating_5_count,
            },
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def recalculate(self):
        """
        Recalculate rating summary from all reviews
        Should be called after review changes
        """
        from sqlalchemy import func
        
        # Get all reviews for this agent
        reviews = db.session.query(AgentReview).filter_by(agent_id=self.agent_id).all()
        
        # Calculate totals
        self.total_reviews = len(reviews)
        
        if self.total_reviews == 0:
            self.average_rating = 0.0
            self.rating_1_count = 0
            self.rating_2_count = 0
            self.rating_3_count = 0
            self.rating_4_count = 0
            self.rating_5_count = 0
        else:
            # Calculate average
            total_rating = sum(review.rating for review in reviews)
            self.average_rating = Decimal(total_rating) / Decimal(self.total_reviews)
            
            # Calculate distribution
            self.rating_1_count = sum(1 for r in reviews if r.rating == 1)
            self.rating_2_count = sum(1 for r in reviews if r.rating == 2)
            self.rating_3_count = sum(1 for r in reviews if r.rating == 3)
            self.rating_4_count = sum(1 for r in reviews if r.rating == 4)
            self.rating_5_count = sum(1 for r in reviews if r.rating == 5)
        
        self.updated_at = datetime.now(timezone.utc)
        db.session.commit()
    
    @staticmethod
    def get_or_create(agent_id: str) -> AgentRatingSummary:
        """Get existing summary or create new one"""
        summary = AgentRatingSummary.query.get(agent_id)
        if not summary:
            summary = AgentRatingSummary(agent_id=agent_id)
            db.session.add(summary)
            db.session.commit()
        return summary

