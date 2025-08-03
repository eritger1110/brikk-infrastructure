from flask import Blueprint, request, jsonify
from src.models.agent import db, Agent, Message, Transaction, CoordinationSession
from datetime import datetime
import secrets
import hashlib

agents_bp = Blueprint('agents', __name__)

def generate_api_key():
    """Generate a secure API key for agent authentication"""
    return secrets.token_urlsafe(32)

def authenticate_agent(api_key):
    """Authenticate agent by API key"""
    if not api_key:
        return None
    return Agent.query.filter_by(api_key=api_key).first()

@agents_bp.route('/agents/register', methods=['POST'])
def register_agent():
    """Register a new AI agent in the Brikk network"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'organization']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Generate API key
        api_key = generate_api_key()
        
        # Create new agent
        agent = Agent(
            name=data['name'],
            description=data.get('description', ''),
            organization=data['organization'],
            framework=data.get('framework', ''),
            capabilities=data.get('capabilities', []),
            endpoints=data.get('endpoints', {}),
            api_key=api_key
        )
        
        db.session.add(agent)
        db.session.commit()
        
        return jsonify({
            'message': 'Agent registered successfully',
            'agent_id': agent.id,
            'api_key': api_key,
            'agent': agent.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agents_bp.route('/agents/discover', methods=['GET'])
def discover_agents():
    """Discover other agents in the network"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        requesting_agent = authenticate_agent(api_key)
        
        if not requesting_agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Update last seen
        requesting_agent.last_seen = datetime.utcnow()
        db.session.commit()
        
        # Get query parameters
        framework = request.args.get('framework')
        capabilities = request.args.getlist('capabilities')
        organization = request.args.get('organization')
        
        # Build query
        query = Agent.query.filter(Agent.status == 'active')
        
        if framework:
            query = query.filter(Agent.framework == framework)
        
        if organization:
            query = query.filter(Agent.organization == organization)
        
        # Execute query
        agents = query.all()
        
        # Filter by capabilities if specified
        if capabilities:
            filtered_agents = []
            for agent in agents:
                if agent.capabilities and any(cap in agent.capabilities for cap in capabilities):
                    filtered_agents.append(agent)
            agents = filtered_agents
        
        # Convert to dict and exclude sensitive info
        agent_list = []
        for agent in agents:
            agent_dict = agent.to_dict()
            # Don't expose API keys to other agents
            agent_dict.pop('api_key', None)
            agent_list.append(agent_dict)
        
        return jsonify({
            'agents': agent_list,
            'total': len(agent_list)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agents_bp.route('/agents/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """Get details of a specific agent"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        requesting_agent = authenticate_agent(api_key)
        
        if not requesting_agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        
        agent_dict = agent.to_dict()
        # Don't expose API key
        agent_dict.pop('api_key', None)
        
        return jsonify({'agent': agent_dict}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agents_bp.route('/agents/me', methods=['GET'])
def get_my_agent():
    """Get details of the authenticated agent"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        return jsonify({'agent': agent.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agents_bp.route('/agents/me', methods=['PUT'])
def update_my_agent():
    """Update the authenticated agent's information"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        data = request.get_json()
        
        # Update allowed fields
        updatable_fields = ['name', 'description', 'capabilities', 'endpoints', 'status']
        for field in updatable_fields:
            if field in data:
                setattr(agent, field, data[field])
        
        agent.last_seen = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Agent updated successfully',
            'agent': agent.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agents_bp.route('/agents/heartbeat', methods=['POST'])
def agent_heartbeat():
    """Update agent's last seen timestamp"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        agent.last_seen = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Heartbeat received',
            'timestamp': agent.last_seen.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agents_bp.route('/agents/stats', methods=['GET'])
def get_network_stats():
    """Get network statistics"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        requesting_agent = authenticate_agent(api_key)
        
        if not requesting_agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Calculate stats
        total_agents = Agent.query.count()
        active_agents = Agent.query.filter_by(status='active').count()
        total_messages = Message.query.count()
        total_transactions = Transaction.query.count()
        active_sessions = CoordinationSession.query.filter_by(status='active').count()
        
        # Framework breakdown
        frameworks = db.session.query(Agent.framework, db.func.count(Agent.id)).group_by(Agent.framework).all()
        framework_stats = {framework: count for framework, count in frameworks if framework}
        
        return jsonify({
            'network_stats': {
                'total_agents': total_agents,
                'active_agents': active_agents,
                'total_messages': total_messages,
                'total_transactions': total_transactions,
                'active_coordination_sessions': active_sessions,
                'frameworks': framework_stats
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
