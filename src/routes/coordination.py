from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.agent import db, Agent, Coordination, SecurityEvent
from datetime import datetime, timezone
import time
import random
import json

coordination_bp = Blueprint('coordination', __name__)

@coordination_bp.route('/agents', methods=['GET'])
def get_agents():
    """Get all registered agents"""
    try:
        agents = Agent.query.all()
        return jsonify({
            'success': True,
            'agents': [agent.to_dict() for agent in agents],
            'total': len(agents)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@coordination_bp.route('/agents', methods=['POST'])
def register_agent():
    """Register a new agent"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name') or not data.get('language'):
            return jsonify({'success': False, 'error': 'Name and language are required'}), 400
        
        # Create new agent
        agent = Agent(
            name=data['name'],
            language=data['language'],
            version=data.get('version', '1.0.0'),
            specialization=data.get('specialization', ''),
            endpoint_url=data.get('endpoint_url', ''),
            api_key=data.get('api_key', '')
        )
        
        # Set capabilities if provided
        if data.get('capabilities'):
            agent.set_capabilities(data['capabilities'])
        
        db.session.add(agent)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'agent': agent.to_dict(),
            'message': 'Agent registered successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@coordination_bp.route('/agents/<agent_id>', methods=['PUT'])
def update_agent(agent_id):
    """Update agent information"""
    try:
        agent = Agent.query.get_or_404(agent_id)
        data = request.get_json()
        
        # Update allowed fields
        allowed_fields = ['name', 'version', 'status', 'specialization', 'endpoint_url']
        for field in allowed_fields:
            if field in data:
                setattr(agent, field, data[field])
        
        if 'capabilities' in data:
            agent.set_capabilities(data['capabilities'])
        
        agent.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'agent': agent.to_dict(),
            'message': 'Agent updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@coordination_bp.route('/agents/<agent_id>/heartbeat', methods=['POST'])
def agent_heartbeat(agent_id):
    """Update agent last seen timestamp"""
    try:
        agent = Agent.query.get_or_404(agent_id)
        agent.last_seen = datetime.now(timezone.utc)
        agent.status = 'active'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Heartbeat received',
            'timestamp': agent.last_seen.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@coordination_bp.route('/workflows', methods=['GET'])
def get_available_workflows():
    """Get available workflow types"""
    workflows = [
        {
            'id': 'data_processing',
            'name': 'Data Processing Pipeline',
            'description': 'Multi-step data ingestion, transformation, analysis, and reporting',
            'steps': ['Data Ingestion', 'Data Transformation', 'Analysis & Insights', 'Report Generation'],
            'languages': ['Node.js', 'Python', 'Python', 'Java'],
            'estimated_duration': '600-800ms'
        },
        {
            'id': 'financial_analysis',
            'name': 'Financial Analysis',
            'description': 'Market data processing with regulatory compliance',
            'steps': ['Market Data Collection', 'Risk Assessment', 'Portfolio Optimization', 'Compliance Check'],
            'languages': ['Python', 'Java', 'Go', 'C#'],
            'estimated_duration': '700-900ms'
        },
        {
            'id': 'customer_service',
            'name': 'Customer Service',
            'description': 'NLP processing with quality assurance validation',
            'steps': ['Intent Recognition', 'Knowledge Retrieval', 'Response Generation', 'Quality Assurance'],
            'languages': ['Python', 'Node.js', 'Python', 'Java'],
            'estimated_duration': '400-600ms'
        }
    ]
    
    return jsonify({
        'success': True,
        'workflows': workflows
    })

@coordination_bp.route('/workflows/<workflow_type>/execute', methods=['POST'])
def execute_workflow(workflow_type):
    """Execute a multi-agent workflow"""
    try:
        data = request.get_json() or {}
        
        # Get available agents by language
        agents_by_language = {}
        agents = Agent.query.filter_by(status='active').all()
        for agent in agents:
            if agent.language not in agents_by_language:
                agents_by_language[agent.language] = []
            agents_by_language[agent.language].append(agent)
        
        # Define workflow configurations
        workflow_configs = {
            'data_processing': {
                'steps': [
                    {'name': 'Data Ingestion', 'language': 'nodejs', 'duration_range': (20, 40)},
                    {'name': 'Data Transformation', 'language': 'python', 'duration_range': (100, 200)},
                    {'name': 'Analysis & Insights', 'language': 'python', 'duration_range': (200, 300)},
                    {'name': 'Report Generation', 'language': 'java', 'duration_range': (150, 250)}
                ]
            },
            'financial_analysis': {
                'steps': [
                    {'name': 'Market Data Collection', 'language': 'python', 'duration_range': (50, 100)},
                    {'name': 'Risk Assessment', 'language': 'java', 'duration_range': (200, 300)},
                    {'name': 'Portfolio Optimization', 'language': 'go', 'duration_range': (100, 200)},
                    {'name': 'Compliance Check', 'language': 'csharp', 'duration_range': (150, 250)}
                ]
            },
            'customer_service': {
                'steps': [
                    {'name': 'Intent Recognition', 'language': 'python', 'duration_range': (30, 60)},
                    {'name': 'Knowledge Retrieval', 'language': 'nodejs', 'duration_range': (40, 80)},
                    {'name': 'Response Generation', 'language': 'python', 'duration_range': (80, 150)},
                    {'name': 'Quality Assurance', 'language': 'java', 'duration_range': (60, 120)}
                ]
            }
        }
        
        if workflow_type not in workflow_configs:
            return jsonify({'success': False, 'error': 'Unknown workflow type'}), 400
        
        config = workflow_configs[workflow_type]
        
        # Create coordination record
        coordination = Coordination(
            workflow_type=workflow_type,
            initiator_agent_id=data.get('initiator_agent_id', 'system'),
            security_level=data.get('security_level', 'standard')
        )
        coordination.status = 'running'
        
        db.session.add(coordination)
        db.session.flush()  # Get the ID
        
        # Execute workflow steps
        workflow_results = []
        participating_agents = []
        total_start_time = time.time()
        
        for i, step in enumerate(config['steps']):
            step_start_time = time.time()
            
            # Find available agent for this language
            language_key = step['language']
            available_agents = agents_by_language.get(language_key, [])
            
            if not available_agents:
                # Create a mock agent for demo purposes
                agent_name = f"{language_key.title()} Agent"
                mock_agent = {
                    'id': f'mock_{language_key}',
                    'name': agent_name,
                    'language': language_key
                }
            else:
                # Use the first available agent
                selected_agent = available_agents[0]
                mock_agent = {
                    'id': selected_agent.id,
                    'name': selected_agent.name,
                    'language': selected_agent.language
                }
                participating_agents.append(selected_agent.id)
            
            # Simulate processing time
            processing_time = random.uniform(*step['duration_range'])
            time.sleep(processing_time / 1000)  # Convert to seconds for sleep
            
            step_end_time = time.time()
            total_latency = (step_end_time - step_start_time) * 1000  # Convert to milliseconds
            
            # Generate step result
            step_result = {
                'step': i + 1,
                'name': step['name'],
                'agent': mock_agent,
                'processing_time': round(processing_time, 2),
                'total_latency': round(total_latency, 2),
                'result': f"{step['name']} completed successfully",
                'timestamp': datetime.now(timezone.utc).strftime('%H:%M:%S %p'),
                'success': True
            }
            
            workflow_results.append(step_result)
            
            # Update agent performance if it's a real agent
            if not mock_agent['id'].startswith('mock_'):
                agent = Agent.query.get(mock_agent['id'])
                if agent:
                    agent.update_performance(processing_time, success=True)
        
        total_end_time = time.time()
        total_duration = (total_end_time - total_start_time) * 1000
        
        # Complete coordination
        coordination.set_participating_agents(participating_agents)
        coordination.set_workflow_steps([step['name'] for step in config['steps']])
        coordination.complete_coordination({
            'steps': workflow_results,
            'total_steps': len(workflow_results),
            'languages_used': len(set(step['language'] for step in config['steps'])),
            'agents_used': len(set(step['agent']['id'] for step in workflow_results))
        }, success=True)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'coordination_id': coordination.id,
            'workflow_type': workflow_type,
            'total_time': round(total_duration, 2),
            'steps_completed': len(workflow_results),
            'agents_used': len(set(step['agent']['id'] for step in workflow_results)),
            'languages_coordinated': len(set(step['language'] for step in config['steps'])),
            'average_step_latency': round(sum(step['total_latency'] for step in workflow_results) / len(workflow_results), 2),
            'results': workflow_results
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@coordination_bp.route('/coordinations', methods=['GET'])
def get_coordinations():
    """Get coordination history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        coordinations = Coordination.query.order_by(Coordination.start_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'coordinations': [coord.to_dict() for coord in coordinations.items],
            'total': coordinations.total,
            'pages': coordinations.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@coordination_bp.route('/metrics', methods=['GET'])
def get_coordination_metrics():
    """Get real-time coordination metrics"""
    try:
        # Get basic counts
        total_agents = Agent.query.count()
        active_agents = Agent.query.filter_by(status='active').count()
        total_coordinations = Coordination.query.count()
        successful_coordinations = Coordination.query.filter_by(status='completed').count()
        
        # Get today's coordinations
        today = datetime.now(timezone.utc).date()
        today_coordinations = Coordination.query.filter(
            db.func.date(Coordination.start_time) == today
        ).count()
        
        # Calculate average latency
        completed_coordinations = Coordination.query.filter_by(status='completed').all()
        if completed_coordinations:
            avg_latency = sum(coord.total_duration for coord in completed_coordinations if coord.total_duration) / len(completed_coordinations)
        else:
            avg_latency = 0
        
        # Calculate success rate
        success_rate = (successful_coordinations / max(total_coordinations, 1)) * 100
        
        # Get language distribution
        language_counts = {}
        agents = Agent.query.all()
        for agent in agents:
            language_counts[agent.language] = language_counts.get(agent.language, 0) + 1
        
        # Generate some realistic metrics for demo
        metrics = {
            'active_agents': active_agents,
            'total_languages': len(language_counts),
            'avg_latency': round(avg_latency or 152.34, 2),
            'success_rate': round(success_rate, 2),
            'coordinations_today': today_coordinations,
            'total_coordinations': total_coordinations,
            'uptime': 99.97,
            'response_time': round(avg_latency or 142, 0),
            'throughput': 2847,
            'error_rate': 0.03,
            'language_distribution': language_counts
        }
        
        return jsonify({
            'success': True,
            'metrics': metrics,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@coordination_bp.route('/setup-demo', methods=['POST'])
def setup_demo_agents():
    """Set up demo agents for testing"""
    try:
        # Clear existing demo agents
        Agent.query.filter(Agent.name.like('%Agent')).delete()
        
        # Create demo agents
        demo_agents = [
            {
                'name': 'Python AI Agent',
                'language': 'python',
                'specialization': 'data_processing, analytics, machine_learning',
                'capabilities': ['data_processing', 'analytics', 'machine_learning', 'nlp'],
                'performance_score': 94.5
            },
            {
                'name': 'Node.js API Agent',
                'language': 'nodejs',
                'specialization': 'data_ingestion, api_integration, real_time_processing',
                'capabilities': ['data_ingestion', 'api_integration', 'real_time_processing', 'websockets'],
                'performance_score': 91.2
            },
            {
                'name': 'Java Enterprise Agent',
                'language': 'java',
                'specialization': 'enterprise_integration, security, reporting',
                'capabilities': ['enterprise_integration', 'security', 'reporting', 'compliance'],
                'performance_score': 96.8
            },
            {
                'name': 'Go Performance Agent',
                'language': 'go',
                'specialization': 'high_performance, concurrent_processing, system_optimization',
                'capabilities': ['high_performance', 'concurrent_processing', 'system_optimization', 'microservices'],
                'performance_score': 98.1
            },
            {
                'name': 'Rust Systems Agent',
                'language': 'rust',
                'specialization': 'systems_programming, memory_safety, performance_critical',
                'capabilities': ['systems_programming', 'memory_safety', 'performance_critical', 'blockchain'],
                'performance_score': 97.3
            },
            {
                'name': 'C# Business Agent',
                'language': 'csharp',
                'specialization': 'business_logic, database_operations, enterprise_workflows',
                'capabilities': ['business_logic', 'database_operations', 'enterprise_workflows', 'integration'],
                'performance_score': 93.7
            }
        ]
        
        created_agents = []
        for agent_data in demo_agents:
            agent = Agent(
                name=agent_data['name'],
                language=agent_data['language'],
                specialization=agent_data['specialization'],
                performance_score=agent_data['performance_score'],
                status='active'
            )
            agent.set_capabilities(agent_data['capabilities'])
            
            # Set some realistic metrics
            agent.total_coordinations = random.randint(50, 200)
            agent.successful_coordinations = int(agent.total_coordinations * (agent_data['performance_score'] / 100))
            agent.average_response_time = random.uniform(50, 300)
            
            db.session.add(agent)
            created_agents.append(agent)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Created {len(created_agents)} demo agents',
            'agents': [agent.to_dict() for agent in created_agents]
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

