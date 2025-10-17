# cURL Quickstart

Get started with the Brikk AI Infrastructure API using cURL.

## Authentication

Set your API key as an environment variable:

```bash
export BRIKK_API_KEY="your_api_key_here"
export BRIKK_API_URL="https://api.getbrikk.com"
```

## Health Check

```bash
curl $BRIKK_API_URL/health
```

Response:
```json
{
  "service": "coordination-api",
  "status": "healthy",
  "timestamp": 1760639209.998622
}
```

## List Agents

```bash
curl -H "Authorization: Bearer $BRIKK_API_KEY" \
  "$BRIKK_API_URL/api/v1/agents?page=1&per_page=20"
```

## Register an Agent

```bash
curl -X POST \
  -H "Authorization: Bearer $BRIKK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My AI Agent",
    "description": "An intelligent agent for task automation",
    "endpoint_url": "https://my-agent.example.com/invoke",
    "capabilities": ["text-generation", "data-analysis"]
  }' \
  "$BRIKK_API_URL/api/v1/agents"
```

## Search Marketplace

```bash
curl -H "Authorization: Bearer $BRIKK_API_KEY" \
  "$BRIKK_API_URL/api/v1/marketplace/agents?category=AI/ML&sort=popular&page=1"
```

## Get Agent Details

```bash
curl -H "Authorization: Bearer $BRIKK_API_KEY" \
  "$BRIKK_API_URL/api/v1/agents/agent-123"
```

## Track Usage Event

```bash
curl -X POST \
  -H "Authorization: Bearer $BRIKK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-123",
    "event_type": "invocation",
    "duration_ms": 150,
    "success": true,
    "metadata": {
      "model": "gpt-4",
      "tokens": 500
    }
  }' \
  "$BRIKK_API_URL/api/v1/analytics/events"
```

## Get Agent Metrics

```bash
curl -H "Authorization: Bearer $BRIKK_API_KEY" \
  "$BRIKK_API_URL/api/v1/analytics/agents/agent-123/metrics?period=7d"
```

## Search Agents

```bash
curl -H "Authorization: Bearer $BRIKK_API_KEY" \
  "$BRIKK_API_URL/api/v1/agent-discovery/search?q=data+analysis&limit=10"
```

## Get Recommendations

```bash
curl -H "Authorization: Bearer $BRIKK_API_KEY" \
  -H "X-User-ID: user-123" \
  "$BRIKK_API_URL/api/v1/agent-discovery/recommendations?limit=5"
```

## Get Agent Reviews

```bash
curl "$BRIKK_API_URL/api/v1/reviews/agents/agent-123?page=1&per_page=10"
```

## Submit a Review

```bash
curl -X POST \
  -H "Authorization: Bearer $BRIKK_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user-123" \
  -d '{
    "rating": 5,
    "title": "Excellent agent!",
    "comment": "This agent works perfectly for my use case.",
    "pros": "Fast, accurate, easy to integrate",
    "cons": "None so far"
  }' \
  "$BRIKK_API_URL/api/v1/reviews/agents/agent-123"
```

## Vote on Review

```bash
curl -X POST \
  -H "Authorization: Bearer $BRIKK_API_KEY" \
  -H "X-User-ID: user-123" \
  "$BRIKK_API_URL/api/v1/reviews/review-456/vote/helpful"
```

## Get Rating Summary

```bash
curl "$BRIKK_API_URL/api/v1/reviews/agents/agent-123/summary"
```

## Error Handling Examples

### Authentication Error (401)

```bash
curl -H "Authorization: Bearer invalid_key" \
  "$BRIKK_API_URL/api/v1/agents"
```

Response:
```json
{
  "error": "auth_required",
  "message": "Authentication required. Please provide valid credentials.",
  "hint": "Include X-User-ID or Authorization header"
}
```

### Feature Disabled (503)

```bash
curl -H "Authorization: Bearer $BRIKK_API_KEY" \
  "$BRIKK_API_URL/api/v1/marketplace/agents"
```

Response:
```json
{
  "error": "marketplace_disabled",
  "message": "Marketplace feature is not enabled",
  "feature": "marketplace",
  "enabled": false
}
```

### Validation Error (400)

```bash
curl -X POST \
  -H "Authorization: Bearer $BRIKK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rating": 6}' \
  "$BRIKK_API_URL/api/v1/reviews/agents/agent-123"
```

Response:
```json
{
  "error": "validation_error",
  "message": "Rating must be between 1 and 5",
  "field": "rating"
}
```

## Useful Scripts

### Batch Register Agents

```bash
#!/bin/bash
# batch_register.sh

AGENTS=(
  "Agent1|Description1|https://agent1.example.com"
  "Agent2|Description2|https://agent2.example.com"
  "Agent3|Description3|https://agent3.example.com"
)

for agent in "${AGENTS[@]}"; do
  IFS='|' read -r name desc url <<< "$agent"
  
  echo "Registering: $name"
  curl -X POST \
    -H "Authorization: Bearer $BRIKK_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$name\",\"description\":\"$desc\",\"endpoint_url\":\"$url\"}" \
    "$BRIKK_API_URL/api/v1/agents"
  echo ""
done
```

### Monitor Agent Usage

```bash
#!/bin/bash
# monitor_usage.sh

AGENT_ID="agent-123"

while true; do
  echo "=== $(date) ==="
  curl -s -H "Authorization: Bearer $BRIKK_API_KEY" \
    "$BRIKK_API_URL/api/v1/analytics/agents/$AGENT_ID/metrics?period=1h" \
    | jq '.total_invocations, .success_rate, .avg_duration_ms'
  
  sleep 60
done
```

### Export All Agents

```bash
#!/bin/bash
# export_agents.sh

PAGE=1
PER_PAGE=100

while true; do
  response=$(curl -s -H "Authorization: Bearer $BRIKK_API_KEY" \
    "$BRIKK_API_URL/api/v1/agents?page=$PAGE&per_page=$PER_PAGE")
  
  agents=$(echo "$response" | jq -r '.agents[]')
  
  if [ -z "$agents" ]; then
    break
  fi
  
  echo "$agents" >> agents.json
  ((PAGE++))
done

echo "Exported all agents to agents.json"
```

## Next Steps

- [Python Quickstart](./python.md)
- [JavaScript Quickstart](./javascript.md)
- [API Reference](../api/openapi.yaml)
- [Authentication Guide](../guides/authentication.md)

