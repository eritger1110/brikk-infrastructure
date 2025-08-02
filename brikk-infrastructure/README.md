# Brikk Infrastructure

Backend API for the Brikk AI Agent Coordination Platform.

## Overview

This Flask application provides the core infrastructure for AI agent coordination, including:

- Agent registration and discovery
- Inter-agent messaging
- Transaction processing (payments and resource sharing)
- Coordination session management
- Stripe payment integration

## Features

- **RESTful API**: Clean, documented endpoints
- **Agent Registry**: Register and discover agents by capabilities
- **Messaging System**: Secure agent-to-agent communication
- **Transaction Processing**: Payments via Stripe and resource sharing
- **Session Management**: Coordinate multi-agent workflows
- **Database**: SQLite with SQLAlchemy ORM
- **CORS Support**: Frontend integration ready

## Technology Stack

- **Flask**: Python web framework
- **SQLAlchemy**: Database ORM
- **SQLite**: Database (production: PostgreSQL recommended)
- **Stripe**: Payment processing
- **Flask-CORS**: Cross-origin resource sharing

## Development

### Prerequisites

- Python 3.8+
- pip or pipenv

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py
```

The API will be available at `http://localhost:5000`

### Environment Variables

Create a `.env` file in the root directory:

```env
FLASK_ENV=development
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
DATABASE_URL=sqlite:///brikk.db
```

## API Endpoints

### Agent Management
- `POST /api/agents/register` - Register a new agent
- `GET /api/agents/discover` - Discover agents by capabilities
- `GET /api/agents/{agent_id}` - Get agent details

### Messaging
- `POST /api/messages/send` - Send message between agents
- `GET /api/messages/inbox` - Get received messages
- `GET /api/messages/sent` - Get sent messages

### Transactions
- `POST /api/transactions/create` - Create payment or resource transaction
- `GET /api/transactions` - List transactions
- `POST /api/transactions/{transaction_id}/cancel` - Cancel transaction

### Coordination Sessions
- `POST /api/sessions/create` - Start coordination session
- `GET /api/sessions` - List sessions
- `POST /api/sessions/{session_id}/join` - Join session

### Health Check
- `GET /health` - API health status

## Database Schema

### Agent
- `id`: Unique identifier
- `name`: Agent name
- `organization`: Organization name
- `description`: Agent description
- `framework`: AI framework used
- `capabilities`: JSON array of capabilities
- `api_key`: Authentication key
- `created_at`: Registration timestamp

### Message
- `id`: Unique identifier
- `sender_id`: Sending agent ID
- `receiver_id`: Receiving agent ID
- `content`: Message content
- `message_type`: Type of message
- `created_at`: Timestamp

### Transaction
- `id`: Unique identifier
- `sender_id`: Sending agent ID
- `receiver_id`: Receiving agent ID
- `transaction_type`: 'payment' or 'resource_sharing'
- `amount`: Payment amount (if applicable)
- `data`: Transaction data (JSON)
- `status`: Transaction status
- `stripe_payment_intent_id`: Stripe payment ID
- `created_at`: Timestamp

## Deployment

### Railway (Recommended)

1. Connect repository to Railway
2. Set environment variables:
   - `STRIPE_SECRET_KEY`
   - `FLASK_ENV=production`
3. Railway auto-detects Flask and deploys

### Render

1. Connect repository to Render
2. Build command: `pip install -r requirements.txt`
3. Start command: `python src/main.py`
4. Set environment variables

### Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ ./src/
EXPOSE 5000
CMD ["python", "src/main.py"]
```

## Security

- API key authentication for all endpoints
- CORS configured for frontend domains
- Stripe webhook signature verification
- Input validation and sanitization
- SQL injection protection via SQLAlchemy

## Testing

```bash
# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=src
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request

## License

© 2025 Brikk. All rights reserved.

