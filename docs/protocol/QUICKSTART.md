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
```## Python Agent

### Setup (Python)

```bash
cd examples/python_agent
pip install -r requirements.txt
```

### Run Demo (Python)

Run locally with dry-run to see the signed request envelope:

```bash
# Dry run (no network, prints envelope)
python examples/python_agent/demo.py --dry-run
```

### Signed Request Example (Python)

```python
import requests
import hmac
import hashlib
import json
import time

# Build the coordination envelope
envelope = {
    "version": "1.0",
    "sender": "demo-python-agent",
    "recipient": "demo-echo-agent",
    "payload": {"job_type": "echo", "message": "Hello!"}
}

# Calculate HMAC signature
timestamp = int(time.time())
body = json.dumps(envelope)
message = f"POST\n/api/v1/coordination\n{body}\n{timestamp}"
signature = hmac.new(
    "your-secret-key".encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

# Send request
response = requests.post(
    "http://localhost:5000/api/v1/coordination",
    headers={
        "X-Brikk-Key": "your-api-key",
        "X-Brikk-Signature": signature,
        "Content-Type": "application/json"
    },
    json=envelope
)
```

### Python Response Format

```json
{
  "status": "accepted",
  "message_id": "...",
  "receipt_ts": 1700000000
}
```

## Node.js Agent

### Setup (Node.js)

```bash
cd examples/node_agent
# No additional dependencies required
```

### Run Demo (Node.js)

Run locally with dry-run to see the signed request envelope:

```bash
# Dry run (no network, prints envelope)
node examples/node_agent/demo.js --dry-run
```

### Signed Request Example (Node.js)

```javascript
const crypto = require('crypto');

// Build the coordination envelope
const envelope = {
    version: '1.0',
    sender: 'demo-node-agent',
    recipient: 'demo-echo-agent',
    payload: { job_type: 'echo', message: 'Hello!' }
};

// Calculate HMAC signature
const timestamp = Math.floor(Date.now() / 1000);
const body = JSON.stringify(envelope);
const message = `POST\n/api/v1/coordination\n${body}\n${timestamp}`;
const signature = crypto
    .createHmac('sha256', 'your-secret-key')
    .update(message)
    .digest('hex');

// Send request using fetch
const response = await fetch('http://localhost:5000/api/v1/coordination', {
    method: 'POST',
    headers: {
        'X-Brikk-Key': 'your-api-key',
        'X-Brikk-Signature': signature,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(envelope)
});
```

### Node.js Response Format

```json
{
  "status": "accepted",
  "message_id": "...",
  "receipt_ts": 1700000000
}
```

## Run Locally (Dry-Run)

Execute the demo agents locally in dry-run mode using the `NO_NETWORK=1` environment variable:

```bash
# Python agent dry-run
cd examples/python_agent
NO_NETWORK=1 python demo.py --dry-run

# Node.js agent dry-run  
cd examples/node_agent
NO_NETWORK=1 node demo.js --dry-run
```

This mode builds and displays the coordination envelope without making network calls, perfect for:

- Testing HMAC signature generation
- Validating envelope structure
- CI/CD environments without network access
- Development and debugging

## HMAC Signature Calculation

The signature is calculated over the following message format:

```text
{method}\n{path}\n{body}\n{timestamp}
```

### Successful Response Format

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

- Explore the client source code in [examples/python_agent/](../../examples/python_agent/) and
  [examples/node_agent/](../../examples/node_agent/)
- Implement your own agent using the coordination protocol
- Review the full API documentation for advanced features
- Run the unit tests to validate HMAC signature generation
