# Brikk Protocol Quickstart

## Overview

The Brikk coordination protocol enables AI agents to communicate across different programming languages and
frameworks. This guide shows you how to get started with the Python and Node.js demo agents.

## Prerequisites

- Python 3.11+ or Node.js 14+
- Access to a Brikk coordination endpoint
- API key and secret for authentication

## Environment Variables

Set these environment variables before running the demo agents:

```bash
export BRIKK_BASE_URL="http://localhost:5000"  # or your Brikk instance
export BRIKK_API_KEY="your-agent-api-key"
export BRIKK_SECRET="your-agent-secret"
```

## Python Agent

### Setup (Python)

```bash
cd examples/python_agent
pip install -r requirements.txt
```

### Run Demo (Python)

```bash
# Full demo (requires network access)
python demo.py

# Dry run (offline testing)
python demo.py --dry-run
```

### Example Output

```text
🤖 Brikk Python Agent Demo
========================================
✅ Connected to: http://localhost:5000
🔑 Agent ID: demo-python-agent

📤 Sending echo job to: demo-echo-agent
📦 Payload: {'job_type': 'echo', 'message': 'Hello from Python agent!', 
            'data': {'test': True, 'timestamp': 1234567890}}

✅ Response received:
📨 Status: accepted
🆔 Message ID: msg_abc123def456
```

## Node.js Agent

### Setup (Node.js)

```bash
cd examples/node_agent
# No additional dependencies required
```

### Run Demo (Node.js)

```bash
# Full demo (requires network access)
node demo.js

# Dry run (offline testing)
node demo.js --dry-run
```

## Protocol Details

### Request Format

The coordination endpoint expects a signed JSON envelope:

```json
{
  "version": "1.0",
  "sender": "your-agent-id",
  "recipient": "target-agent-id",
  "payload": {
    "job_type": "echo",
    "message": "Hello world",
    "data": {}
  },
  "timestamp": 1234567890
}
```

### Authentication

Requests are authenticated using HMAC-SHA256 signatures:

```text
Authorization: HMAC {api_key}:{timestamp}:{signature}
```

The signature is calculated over:

```text
{method}\n{path}\n{body}\n{timestamp}
```

### Response Format

Successful responses return:

```json
{
  "status": "accepted",
  "message_id": "msg_abc123def456",
  "timestamp": 1234567890
}
```

## Testing

Run the offline unit tests to validate HMAC signature generation:

```bash
# Python tests
python -m pytest tests/examples/test_python_agent.py -v

# Expected output:
# test_envelope_structure PASSED
# test_hmac_signature_calculation PASSED
# test_signature_format PASSED
```

## Troubleshooting

### Common Issues

1. **Missing environment variables**: Ensure `BRIKK_API_KEY` and `BRIKK_SECRET` are set
2. **Network connectivity**: Use `--dry-run` flag to test without network access
3. **Authentication errors**: Verify your API key and secret are correct

### Debug Mode

Enable verbose logging by setting:

```bash
export BRIKK_DEBUG=1
```

## Next Steps

- Explore the client source code in `examples/python_agent/client.py` and `examples/node_agent/client.js`
- Implement your own agent using the coordination protocol
- Review the full API documentation for advanced features
