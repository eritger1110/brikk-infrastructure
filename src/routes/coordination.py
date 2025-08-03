from flask import Blueprint, request, jsonify
from src.models.agent import db, Agent, Message, CoordinationSession
from datetime import datetime
import json

coordination_bp = Blueprint('coordination', __name__)

def authenticate_agent(api_key):
    """Authenticate agent by API key"""
    if not api_key:
        return None
    return Agent.query.filter_by(api_key=api_key).first()

@coordination_bp.route('/messages/send', methods=['POST'])
def send_message():
    """Send a message from one agent to another"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        sender = authenticate_agent(api_key)
        
        if not sender:
            return jsonify({'error': 'Invalid API key'}), 401
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['receiver_id', 'message_type', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify receiver exists
        receiver = Agent.query.get(data['receiver_id'])
        if not receiver:
            return jsonify({'error': 'Receiver agent not found'}), 404
        
        if receiver.status != 'active':
            return jsonify({'error': 'Receiver agent is not active'}), 400
        
        # Create message
        message = Message(
            sender_id=sender.id,
            receiver_id=data['receiver_id'],
            message_type=data['message_type'],
            content=data['content']
        )
        
        db.session.add(message)
        db.session.commit()
        
        # TODO: Implement actual message delivery to receiver's endpoint
        # For now, we'll just store it in the database
        
        return jsonify({
            'message': 'Message sent successfully',
            'message_id': message.id,
            'message_data': message.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@coordination_bp.route('/messages/inbox', methods=['GET'])
def get_inbox():
    """Get messages for the authenticated agent"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Get query parameters
        status = request.args.get('status', 'all')
        message_type = request.args.get('message_type')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = Message.query.filter_by(receiver_id=agent.id)
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        if message_type:
            query = query.filter_by(message_type=message_type)
        
        # Order by creation time (newest first)
        query = query.order_by(Message.created_at.desc())
        
        # Apply pagination
        messages = query.offset(offset).limit(limit).all()
        total = query.count()
        
        return jsonify({
            'messages': [msg.to_dict() for msg in messages],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@coordination_bp.route('/messages/outbox', methods=['GET'])
def get_outbox():
    """Get sent messages for the authenticated agent"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Get query parameters
        status = request.args.get('status', 'all')
        message_type = request.args.get('message_type')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = Message.query.filter_by(sender_id=agent.id)
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        if message_type:
            query = query.filter_by(message_type=message_type)
        
        # Order by creation time (newest first)
        query = query.order_by(Message.created_at.desc())
        
        # Apply pagination
        messages = query.offset(offset).limit(limit).all()
        total = query.count()
        
        return jsonify({
            'messages': [msg.to_dict() for msg in messages],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@coordination_bp.route('/messages/<message_id>/read', methods=['POST'])
def mark_message_read():
    """Mark a message as read"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        message = Message.query.get(message_id)
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        # Only the receiver can mark a message as read
        if message.receiver_id != agent.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        message.status = 'read'
        message.delivered_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Message marked as read',
            'message_data': message.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@coordination_bp.route('/sessions/create', methods=['POST'])
def create_coordination_session():
    """Create a new coordination session"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        coordinator = authenticate_agent(api_key)
        
        if not coordinator:
            return jsonify({'error': 'Invalid API key'}), 401
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'session_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate participants
        participants = data.get('participants', [])
        if participants:
            # Verify all participants exist and are active
            for participant_id in participants:
                participant = Agent.query.get(participant_id)
                if not participant:
                    return jsonify({'error': f'Participant {participant_id} not found'}), 404
                if participant.status != 'active':
                    return jsonify({'error': f'Participant {participant_id} is not active'}), 400
        
        # Create coordination session
        session = CoordinationSession(
            name=data['name'],
            description=data.get('description', ''),
            coordinator_id=coordinator.id,
            participants=participants,
            session_type=data['session_type'],
            session_metadata=data.get('session_metadata', {})
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'message': 'Coordination session created successfully',
            'session_id': session.id,
            'session': session.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@coordination_bp.route('/sessions', methods=['GET'])
def get_coordination_sessions():
    """Get coordination sessions for the authenticated agent"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Get query parameters
        status = request.args.get('status', 'all')
        session_type = request.args.get('session_type')
        role = request.args.get('role', 'all')  # coordinator, participant, all
        
        # Build query based on role
        if role == 'coordinator':
            query = CoordinationSession.query.filter_by(coordinator_id=agent.id)
        elif role == 'participant':
            # Find sessions where agent is a participant
            query = CoordinationSession.query.filter(
                CoordinationSession.participants.contains(agent.id)
            )
        else:
            # All sessions where agent is coordinator or participant
            query = CoordinationSession.query.filter(
                db.or_(
                    CoordinationSession.coordinator_id == agent.id,
                    CoordinationSession.participants.contains(agent.id)
                )
            )
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        if session_type:
            query = query.filter_by(session_type=session_type)
        
        # Order by creation time (newest first)
        sessions = query.order_by(CoordinationSession.created_at.desc()).all()
        
        return jsonify({
            'sessions': [session.to_dict() for session in sessions],
            'total': len(sessions)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@coordination_bp.route('/sessions/<session_id>', methods=['GET'])
def get_coordination_session(session_id):
    """Get details of a specific coordination session"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        session = CoordinationSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check if agent has access to this session
        has_access = (
            session.coordinator_id == agent.id or
            agent.id in (session.participants or [])
        )
        
        if not has_access:
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify({'session': session.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@coordination_bp.route('/sessions/<session_id>/join', methods=['POST'])
def join_coordination_session(session_id):
    """Join a coordination session"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        session = CoordinationSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if session.status != 'active':
            return jsonify({'error': 'Session is not active'}), 400
        
        # Check if agent is already a participant
        participants = session.participants or []
        if agent.id in participants:
            return jsonify({'error': 'Already a participant'}), 400
        
        # Add agent to participants
        participants.append(agent.id)
        session.participants = participants
        db.session.commit()
        
        return jsonify({
            'message': 'Successfully joined coordination session',
            'session': session.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@coordination_bp.route('/sessions/<session_id>/leave', methods=['POST'])
def leave_coordination_session(session_id):
    """Leave a coordination session"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        session = CoordinationSession.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check if agent is a participant
        participants = session.participants or []
        if agent.id not in participants:
            return jsonify({'error': 'Not a participant'}), 400
        
        # Remove agent from participants
        participants.remove(agent.id)
        session.participants = participants
        db.session.commit()
        
        return jsonify({
            'message': 'Successfully left coordination session',
            'session': session.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
