"""
Reviews routes for Phase 7
Handles agent reviews, ratings, and feedback
"""
from flask import Blueprint, request, jsonify
from typing import Optional
from datetime import datetime, timezone

from src.infra.db import db
from src.models.reviews import AgentReview, ReviewVote, AgentRatingSummary
from src.models.marketplace import MarketplaceListing, AgentInstallation
from src.utils.feature_flags import FeatureFlagManager, FeatureFlag
from src.infra.log import get_logger

logger = get_logger(__name__)
reviews_bp = Blueprint('reviews', __name__, url_prefix='/api/v1/reviews')


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def check_reviews_enabled():
    """Check if reviews feature is enabled"""
    feature_flags = FeatureFlagManager()
    if not feature_flags.is_enabled(FeatureFlag.REVIEWS_RATINGS):
        return jsonify({'error': 'reviews_disabled', 'message': 'Reviews feature is not enabled'}), 503
    return None


def get_current_user_id() -> Optional[str]:
    """Get current user ID from request context"""
    return request.headers.get('X-User-ID')


def require_auth():
    """Require authentication for protected endpoints"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'auth_required', 'message': 'Authentication required'}), 401
    return None


# =============================================================================
# REVIEW SUBMISSION
# =============================================================================

@reviews_bp.route('/agents/<agent_id>', methods=['POST'])
def submit_review(agent_id: str):
    """
    Submit a review for an agent
    
    Request Body:
    - rating: Rating (1-5 stars)
    - title: Review title
    - content: Review content
    - pros: List of pros
    - cons: List of cons
    """
    # Check if reviews are enabled
    error_response = check_reviews_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('rating') or not isinstance(data['rating'], int):
            return jsonify({'error': 'validation_error', 'message': 'Valid rating (1-5) is required'}), 400
        
        rating = data['rating']
        if rating < 1 or rating > 5:
            return jsonify({'error': 'validation_error', 'message': 'Rating must be between 1 and 5'}), 400
        
        # Check if agent exists in marketplace
        listing = MarketplaceListing.query.filter_by(agent_id=agent_id, status='published').first()
        if not listing:
            return jsonify({'error': 'not_found', 'message': 'Agent not found in marketplace'}), 404
        
        # Check if user has installed the agent (optional requirement)
        # installation = AgentInstallation.query.filter_by(
        #     agent_id=agent_id,
        #     user_id=user_id
        # ).filter(AgentInstallation.uninstalled_at == None).first()
        # 
        # if not installation:
        #     return jsonify({'error': 'not_installed', 'message': 'You must install the agent before reviewing'}), 403
        
        # Check if user already reviewed this agent
        existing_review = AgentReview.query.filter_by(
            agent_id=agent_id,
            user_id=user_id
        ).first()
        
        if existing_review:
            return jsonify({'error': 'already_reviewed', 'message': 'You have already reviewed this agent'}), 409
        
        # Create review
        review = AgentReview(
            agent_id=agent_id,
            user_id=user_id,
            rating=rating,
            title=data.get('title'),
            content=data.get('content'),
            pros=data.get('pros', []),
            cons=data.get('cons', [])
        )
        
        db.session.add(review)
        db.session.commit()
        
        # Update rating summary
        _update_rating_summary(agent_id)
        
        logger.info(f"Review submitted for agent {agent_id} by user {user_id}")
        
        return jsonify(review.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting review: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@reviews_bp.route('/<review_id>', methods=['PUT'])
def update_review(review_id: str):
    """
    Update an existing review
    
    Request Body:
    - rating: Updated rating (1-5 stars)
    - title: Updated title
    - content: Updated content
    - pros: Updated pros
    - cons: Updated cons
    """
    # Check if reviews are enabled
    error_response = check_reviews_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        review = AgentReview.query.get(review_id)
        
        if not review:
            return jsonify({'error': 'not_found', 'message': 'Review not found'}), 404
        
        # Check ownership
        if review.user_id != user_id:
            return jsonify({'error': 'forbidden', 'message': 'You can only edit your own reviews'}), 403
        
        # Update fields
        data = request.get_json()
        
        if 'rating' in data:
            rating = data['rating']
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return jsonify({'error': 'validation_error', 'message': 'Rating must be between 1 and 5'}), 400
            review.rating = rating
        
        if 'title' in data:
            review.title = data['title']
        if 'content' in data:
            review.content = data['content']
        if 'pros' in data:
            review.pros = data['pros']
        if 'cons' in data:
            review.cons = data['cons']
        
        review.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Update rating summary
        _update_rating_summary(review.agent_id)
        
        logger.info(f"Review {review_id} updated by user {user_id}")
        
        return jsonify(review.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating review: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@reviews_bp.route('/<review_id>', methods=['DELETE'])
def delete_review(review_id: str):
    """Delete a review"""
    # Check if reviews are enabled
    error_response = check_reviews_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        review = AgentReview.query.get(review_id)
        
        if not review:
            return jsonify({'error': 'not_found', 'message': 'Review not found'}), 404
        
        # Check ownership
        if review.user_id != user_id:
            return jsonify({'error': 'forbidden', 'message': 'You can only delete your own reviews'}), 403
        
        agent_id = review.agent_id
        db.session.delete(review)
        db.session.commit()
        
        # Update rating summary
        _update_rating_summary(agent_id)
        
        logger.info(f"Review {review_id} deleted by user {user_id}")
        
        return jsonify({'message': 'Review deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting review: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# REVIEW RETRIEVAL
# =============================================================================

@reviews_bp.route('/agents/<agent_id>', methods=['GET'])
def get_agent_reviews(agent_id: str):
    """
    Get reviews for an agent
    
    Query Parameters:
    - sort: Sort order (recent, helpful, rating_high, rating_low)
    - rating: Filter by rating (1-5)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    """
    # Check if reviews are enabled
    error_response = check_reviews_enabled()
    if error_response:
        return error_response
    
    try:
        # Parse query parameters
        sort = request.args.get('sort', 'recent')
        rating_filter = request.args.get('rating')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # Build query
        query = AgentReview.query.filter_by(agent_id=agent_id)
        
        # Apply rating filter
        if rating_filter:
            query = query.filter_by(rating=int(rating_filter))
        
        # Apply sorting
        if sort == 'helpful':
            query = query.order_by(AgentReview.helpful_count.desc())
        elif sort == 'rating_high':
            query = query.order_by(AgentReview.rating.desc())
        elif sort == 'rating_low':
            query = query.order_by(AgentReview.rating.asc())
        else:  # 'recent'
            query = query.order_by(AgentReview.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Build response
        reviews = []
        user_id = get_current_user_id()
        
        for review in pagination.items:
            review_dict = review.to_dict()
            
            # Check if current user voted on this review
            if user_id:
                vote = ReviewVote.query.filter_by(
                    review_id=review.id,
                    user_id=user_id
                ).first()
                if vote:
                    review_dict['user_vote'] = vote.vote_type
            
            # Include publisher response if exists
            response = ReviewResponse.query.filter_by(review_id=review.id).first()
            if response:
                review_dict['publisher_response'] = response.to_dict()
            
            reviews.append(review_dict)
        
        return jsonify({
            'reviews': reviews,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting agent reviews: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@reviews_bp.route('/<review_id>', methods=['GET'])
def get_review(review_id: str):
    """Get a specific review"""
    # Check if reviews are enabled
    error_response = check_reviews_enabled()
    if error_response:
        return error_response
    
    try:
        review = AgentReview.query.get(review_id)
        
        if not review:
            return jsonify({'error': 'not_found', 'message': 'Review not found'}), 404
        
        review_dict = review.to_dict()
        
        # Include publisher response if exists
        response = ReviewResponse.query.filter_by(review_id=review_id).first()
        if response:
            review_dict['publisher_response'] = response.to_dict()
        
        return jsonify(review_dict), 200
        
    except Exception as e:
        logger.error(f"Error getting review: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# REVIEW VOTING
# =============================================================================

@reviews_bp.route('/<review_id>/vote', methods=['POST'])
def vote_on_review(review_id: str):
    """
    Vote on a review (helpful/not helpful)
    
    Request Body:
    - vote_type: 'helpful' or 'not_helpful'
    """
    # Check if reviews are enabled
    error_response = check_reviews_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        
        # Validate vote type
        vote_type = data.get('vote_type')
        if vote_type not in ['helpful', 'not_helpful']:
            return jsonify({'error': 'validation_error', 'message': 'vote_type must be helpful or not_helpful'}), 400
        
        # Check if review exists
        review = AgentReview.query.get(review_id)
        if not review:
            return jsonify({'error': 'not_found', 'message': 'Review not found'}), 404
        
        # Check if user already voted
        existing_vote = ReviewVote.query.filter_by(
            review_id=review_id,
            user_id=user_id
        ).first()
        
        if existing_vote:
            # Update existing vote
            old_vote_type = existing_vote.vote_type
            existing_vote.vote_type = vote_type
            existing_vote.updated_at = datetime.now(timezone.utc)
            
            # Update review counters
            if old_vote_type == 'helpful' and vote_type == 'not_helpful':
                review.helpful_count = max(0, review.helpful_count - 1)
                review.not_helpful_count += 1
            elif old_vote_type == 'not_helpful' and vote_type == 'helpful':
                review.not_helpful_count = max(0, review.not_helpful_count - 1)
                review.helpful_count += 1
        else:
            # Create new vote
            vote = ReviewVote(
                review_id=review_id,
                user_id=user_id,
                vote_type=vote_type
            )
            db.session.add(vote)
            
            # Update review counters
            if vote_type == 'helpful':
                review.helpful_count += 1
            else:
                review.not_helpful_count += 1
        
        db.session.commit()
        
        logger.info(f"Vote {vote_type} on review {review_id} by user {user_id}")
        
        return jsonify({
            'message': 'Vote recorded successfully',
            'helpful_count': review.helpful_count,
            'not_helpful_count': review.not_helpful_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error voting on review: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@reviews_bp.route('/<review_id>/vote', methods=['DELETE'])
def remove_vote(review_id: str):
    """Remove vote from a review"""
    # Check if reviews are enabled
    error_response = check_reviews_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        
        vote = ReviewVote.query.filter_by(
            review_id=review_id,
            user_id=user_id
        ).first()
        
        if not vote:
            return jsonify({'error': 'not_found', 'message': 'Vote not found'}), 404
        
        # Update review counters
        review = AgentReview.query.get(review_id)
        if review:
            if vote.vote_type == 'helpful':
                review.helpful_count = max(0, review.helpful_count - 1)
            else:
                review.not_helpful_count = max(0, review.not_helpful_count - 1)
        
        db.session.delete(vote)
        db.session.commit()
        
        logger.info(f"Vote removed from review {review_id} by user {user_id}")
        
        return jsonify({'message': 'Vote removed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing vote: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# PUBLISHER RESPONSES
# =============================================================================

@reviews_bp.route('/<review_id>/response', methods=['POST'])
def respond_to_review(review_id: str):
    """
    Publisher responds to a review
    
    Request Body:
    - content: Response content
    """
    # Check if reviews are enabled
    error_response = check_reviews_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        
        # Validate content
        if not data.get('content'):
            return jsonify({'error': 'validation_error', 'message': 'Response content is required'}), 400
        
        # Check if review exists
        review = AgentReview.query.get(review_id)
        if not review:
            return jsonify({'error': 'not_found', 'message': 'Review not found'}), 404
        
        # Check if user is the publisher
        listing = MarketplaceListing.query.filter_by(agent_id=review.agent_id).first()
        if not listing or listing.publisher_id != user_id:
            return jsonify({'error': 'forbidden', 'message': 'Only the publisher can respond to reviews'}), 403
        
        # Check if response already exists
        existing_response = ReviewResponse.query.filter_by(review_id=review_id).first()
        if existing_response:
            return jsonify({'error': 'already_responded', 'message': 'You have already responded to this review'}), 409
        
        # Create response
        response = ReviewResponse(
            review_id=review_id,
            publisher_id=user_id,
            content=data['content']
        )
        
        db.session.add(response)
        db.session.commit()
        
        logger.info(f"Publisher response added to review {review_id}")
        
        return jsonify(response.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error responding to review: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# RATING SUMMARY
# =============================================================================

@reviews_bp.route('/agents/<agent_id>/summary', methods=['GET'])
def get_rating_summary(agent_id: str):
    """Get rating summary for an agent"""
    # Check if reviews are enabled
    error_response = check_reviews_enabled()
    if error_response:
        return error_response
    
    try:
        summary = AgentRatingSummary.query.get(agent_id)
        
        if not summary:
            # Return empty summary
            return jsonify({
                'agent_id': agent_id,
                'total_reviews': 0,
                'average_rating': 0.0,
                'rating_distribution': {
                    '5': 0,
                    '4': 0,
                    '3': 0,
                    '2': 0,
                    '1': 0
                }
            }), 200
        
        return jsonify(summary.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting rating summary: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _update_rating_summary(agent_id: str):
    """Update or create rating summary for an agent"""
    try:
        # Get all reviews for the agent
        reviews = AgentReview.query.filter_by(agent_id=agent_id).all()
        
        if not reviews:
            # Delete summary if no reviews
            summary = AgentRatingSummary.query.get(agent_id)
            if summary:
                db.session.delete(summary)
                db.session.commit()
            return
        
        # Calculate metrics
        total_reviews = len(reviews)
        total_rating = sum(r.rating for r in reviews)
        average_rating = total_rating / total_reviews
        
        # Calculate rating distribution
        rating_distribution = {
            5: sum(1 for r in reviews if r.rating == 5),
            4: sum(1 for r in reviews if r.rating == 4),
            3: sum(1 for r in reviews if r.rating == 3),
            2: sum(1 for r in reviews if r.rating == 2),
            1: sum(1 for r in reviews if r.rating == 1)
        }
        
        # Update or create summary
        summary = AgentRatingSummary.query.get(agent_id)
        if summary:
            summary.update_summary(
                total_reviews=total_reviews,
                average_rating=average_rating,
                rating_distribution=rating_distribution
            )
        else:
            summary = AgentRatingSummary(
                agent_id=agent_id,
                total_reviews=total_reviews,
                average_rating=average_rating,
                rating_1_count=rating_distribution[1],
                rating_2_count=rating_distribution[2],
                rating_3_count=rating_distribution[3],
                rating_4_count=rating_distribution[4],
                rating_5_count=rating_distribution[5]
            )
            db.session.add(summary)
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating rating summary for agent {agent_id}: {str(e)}")
        raise

