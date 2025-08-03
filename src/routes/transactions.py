from flask import Blueprint, request, jsonify
from src.models.agent import db, Agent, Transaction
from datetime import datetime
import stripe
import os

transactions_bp = Blueprint('transactions', __name__)

# Configure Stripe (you'll need to set these environment variables)
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')  # Replace with actual key

def authenticate_agent(api_key):
    """Authenticate agent by API key"""
    if not api_key:
        return None
    return Agent.query.filter_by(api_key=api_key).first()

@transactions_bp.route('/transactions/create', methods=['POST'])
def create_transaction():
    """Create a new transaction between agents"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        sender = authenticate_agent(api_key)
        
        if not sender:
            return jsonify({'error': 'Invalid API key'}), 401
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['receiver_id', 'transaction_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify receiver exists
        receiver = Agent.query.get(data['receiver_id'])
        if not receiver:
            return jsonify({'error': 'Receiver agent not found'}), 404
        
        if receiver.status != 'active':
            return jsonify({'error': 'Receiver agent is not active'}), 400
        
        # Validate transaction type specific requirements
        transaction_type = data['transaction_type']
        
        if transaction_type == 'payment':
            if 'amount' not in data or data['amount'] <= 0:
                return jsonify({'error': 'Payment transactions require a positive amount'}), 400
        
        # Create transaction
        transaction = Transaction(
            sender_id=sender.id,
            receiver_id=data['receiver_id'],
            transaction_type=transaction_type,
            amount=data.get('amount'),
            currency=data.get('currency', 'USD'),
            resource_type=data.get('resource_type'),
            resource_data=data.get('resource_data')
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction created successfully',
            'transaction_id': transaction.id,
            'transaction': transaction.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/transactions/payment/intent', methods=['POST'])
def create_payment_intent():
    """Create a Stripe payment intent for agent-to-agent payment"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        sender = authenticate_agent(api_key)
        
        if not sender:
            return jsonify({'error': 'Invalid API key'}), 401
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['transaction_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get transaction
        transaction = Transaction.query.get(data['transaction_id'])
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        # Verify sender owns this transaction
        if transaction.sender_id != sender.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Verify transaction is a payment type
        if transaction.transaction_type != 'payment':
            return jsonify({'error': 'Transaction is not a payment type'}), 400
        
        # Verify transaction is pending
        if transaction.status != 'pending':
            return jsonify({'error': 'Transaction is not pending'}), 400
        
        # Create Stripe payment intent
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(transaction.amount * 100),  # Stripe uses cents
                currency=transaction.currency.lower(),
                metadata={
                    'transaction_id': transaction.id,
                    'sender_id': transaction.sender_id,
                    'receiver_id': transaction.receiver_id,
                    'brikk_transaction': 'true'
                }
            )
            
            # Update transaction with payment intent ID
            transaction.stripe_payment_intent_id = intent.id
            db.session.commit()
            
            return jsonify({
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'transaction_id': transaction.id
            }), 200
            
        except stripe.error.StripeError as e:
            return jsonify({'error': f'Stripe error: {str(e)}'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/transactions/payment/confirm', methods=['POST'])
def confirm_payment():
    """Confirm a payment transaction"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        sender = authenticate_agent(api_key)
        
        if not sender:
            return jsonify({'error': 'Invalid API key'}), 401
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['transaction_id', 'payment_intent_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get transaction
        transaction = Transaction.query.get(data['transaction_id'])
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        # Verify sender owns this transaction
        if transaction.sender_id != sender.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Verify payment intent matches
        if transaction.stripe_payment_intent_id != data['payment_intent_id']:
            return jsonify({'error': 'Payment intent mismatch'}), 400
        
        # Verify payment with Stripe
        try:
            intent = stripe.PaymentIntent.retrieve(data['payment_intent_id'])
            
            if intent.status == 'succeeded':
                # Update transaction status
                transaction.status = 'completed'
                transaction.completed_at = datetime.utcnow()
                db.session.commit()
                
                return jsonify({
                    'message': 'Payment confirmed successfully',
                    'transaction': transaction.to_dict()
                }), 200
            else:
                return jsonify({
                    'error': f'Payment not completed. Status: {intent.status}'
                }), 400
                
        except stripe.error.StripeError as e:
            return jsonify({'error': f'Stripe error: {str(e)}'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/transactions', methods=['GET'])
def get_transactions():
    """Get transactions for the authenticated agent"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Get query parameters
        transaction_type = request.args.get('transaction_type')
        status = request.args.get('status')
        role = request.args.get('role', 'all')  # sender, receiver, all
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query based on role
        if role == 'sender':
            query = Transaction.query.filter_by(sender_id=agent.id)
        elif role == 'receiver':
            query = Transaction.query.filter_by(receiver_id=agent.id)
        else:
            # All transactions where agent is sender or receiver
            query = Transaction.query.filter(
                db.or_(
                    Transaction.sender_id == agent.id,
                    Transaction.receiver_id == agent.id
                )
            )
        
        if transaction_type:
            query = query.filter_by(transaction_type=transaction_type)
        
        if status:
            query = query.filter_by(status=status)
        
        # Order by creation time (newest first)
        query = query.order_by(Transaction.created_at.desc())
        
        # Apply pagination
        transactions = query.offset(offset).limit(limit).all()
        total = query.count()
        
        return jsonify({
            'transactions': [txn.to_dict() for txn in transactions],
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/transactions/<transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """Get details of a specific transaction"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        # Check if agent has access to this transaction
        has_access = (
            transaction.sender_id == agent.id or
            transaction.receiver_id == agent.id
        )
        
        if not has_access:
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify({'transaction': transaction.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/transactions/<transaction_id>/cancel', methods=['POST'])
def cancel_transaction(transaction_id):
    """Cancel a pending transaction"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        agent = authenticate_agent(api_key)
        
        if not agent:
            return jsonify({'error': 'Invalid API key'}), 401
        
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        # Only sender can cancel a transaction
        if transaction.sender_id != agent.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Can only cancel pending transactions
        if transaction.status != 'pending':
            return jsonify({'error': 'Can only cancel pending transactions'}), 400
        
        # Cancel Stripe payment intent if exists
        if transaction.stripe_payment_intent_id:
            try:
                stripe.PaymentIntent.cancel(transaction.stripe_payment_intent_id)
            except stripe.error.StripeError as e:
                # Log error but don't fail the cancellation
                print(f"Failed to cancel Stripe payment intent: {e}")
        
        # Update transaction status
        transaction.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction cancelled successfully',
            'transaction': transaction.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/transactions/resource/share', methods=['POST'])
def share_resource():
    """Share a resource between agents (non-payment transaction)"""
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        sender = authenticate_agent(api_key)
        
        if not sender:
            return jsonify({'error': 'Invalid API key'}), 401
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['receiver_id', 'resource_type', 'resource_data']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify receiver exists
        receiver = Agent.query.get(data['receiver_id'])
        if not receiver:
            return jsonify({'error': 'Receiver agent not found'}), 404
        
        # Create resource sharing transaction
        transaction = Transaction(
            sender_id=sender.id,
            receiver_id=data['receiver_id'],
            transaction_type='resource_share',
            resource_type=data['resource_type'],
            resource_data=data['resource_data'],
            status='completed'  # Resource sharing is immediate
        )
        
        transaction.completed_at = datetime.utcnow()
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'message': 'Resource shared successfully',
            'transaction_id': transaction.id,
            'transaction': transaction.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
