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

```bash
# Request (example)
curl -X POST "$BRIKK_BASE_URL/api/v1/coordination" \
  -H "X-Brikk-Key: $BRIKK_API_KEY" \
  -H "X-Brikk-Signature: <HMAC_SHA256_HEX>" \
  -H "Content-Type: application/json" \
  -d '{
    "version":"1.0",
    "sender":"demo-python-agent",
    "recipient":"demo-echo-agent",
    "payload":{"job_type":"echo","message":"Hello!"}
  }'
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

The Node.js agent builds the same envelope and computes the HMAC signature in `client.js`.

### Node.js Response Format

```json
{
  "status": "accepted",
  "message_id": "...",
  "receipt_ts": 1700000000
}


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

- Explore the client source code in `examples/python_agent/client.py` and `examples/node_agent/client.js`
- Implement your own agent using the coordination protocol
- Review the full API documentation for advanced features
