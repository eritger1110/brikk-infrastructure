# Python SDK Quickstart

Get started with the Brikk AI Infrastructure API using Python.

## Installation

```bash
pip install requests
```

## Authentication

Get your API key from the [Brikk Dashboard](https://app.getbrikk.com/settings/api-keys).

```python
import requests

API_KEY = "your_api_key_here"
BASE_URL = "https://api.getbrikk.com"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
```

## List Agents

```python
response = requests.get(
    f"{BASE_URL}/api/v1/agents",
    headers=headers
)

agents = response.json()
print(f"Found {agents['total']} agents")

for agent in agents['agents']:
    print(f"- {agent['name']}: {agent['description']}")
```

## Register an Agent

```python
agent_data = {
    "name": "My AI Agent",
    "description": "An intelligent agent for task automation",
    "endpoint_url": "https://my-agent.example.com/invoke",
    "capabilities": ["text-generation", "data-analysis"]
}

response = requests.post(
    f"{BASE_URL}/api/v1/agents",
    headers=headers,
    json=agent_data
)

agent = response.json()
print(f"Agent registered with ID: {agent['id']}")
```

## Search Marketplace

```python
response = requests.get(
    f"{BASE_URL}/api/v1/marketplace/agents",
    headers=headers,
    params={
        "category": "AI/ML",
        "sort": "popular",
        "page": 1
    }
)

listings = response.json()
for listing in listings['agents']:
    print(f"{listing['title']} - Rating: {listing['rating']}/5")
```

## Track Usage

```python
event_data = {
    "agent_id": "agent-123",
    "event_type": "invocation",
    "duration_ms": 150,
    "success": True,
    "metadata": {
        "model": "gpt-4",
        "tokens": 500
    }
}

response = requests.post(
    f"{BASE_URL}/api/v1/analytics/events",
    headers=headers,
    json=event_data
)

print("Usage tracked successfully")
```

## Submit a Review

```python
review_data = {
    "rating": 5,
    "title": "Excellent agent!",
    "comment": "This agent works perfectly for my use case.",
    "pros": "Fast, accurate, easy to integrate",
    "cons": "None so far"
}

response = requests.post(
    f"{BASE_URL}/api/v1/reviews/agents/agent-123",
    headers=headers,
    json=review_data
)

print("Review submitted!")
```

## Error Handling

```python
try:
    response = requests.get(
        f"{BASE_URL}/api/v1/agents",
        headers=headers
    )
    response.raise_for_status()
    data = response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        print("Authentication failed. Check your API key.")
    elif e.response.status_code == 503:
        error = e.response.json()
        print(f"Feature disabled: {error['message']}")
    else:
        print(f"Error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

## Complete Example

```python
import requests
from typing import List, Dict, Any

class BrikkClient:
    def __init__(self, api_key: str, base_url: str = "https://api.getbrikk.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def list_agents(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """List all registered agents"""
        response = requests.get(
            f"{self.base_url}/api/v1/agents",
            headers=self.headers,
            params={"page": page, "per_page": per_page}
        )
        response.raise_for_status()
        return response.json()
    
    def register_agent(self, name: str, description: str, endpoint_url: str) -> Dict[str, Any]:
        """Register a new agent"""
        data = {
            "name": name,
            "description": description,
            "endpoint_url": endpoint_url
        }
        response = requests.post(
            f"{self.base_url}/api/v1/agents",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def search_marketplace(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for agents in the marketplace"""
        response = requests.get(
            f"{self.base_url}/api/v1/agent-discovery/search",
            headers=self.headers,
            params={"q": query, "limit": limit}
        )
        response.raise_for_status()
        return response.json()['results']
    
    def track_usage(self, agent_id: str, event_type: str, duration_ms: int, success: bool) -> None:
        """Track agent usage"""
        data = {
            "agent_id": agent_id,
            "event_type": event_type,
            "duration_ms": duration_ms,
            "success": success
        }
        response = requests.post(
            f"{self.base_url}/api/v1/analytics/events",
            headers=self.headers,
            json=data
        )
        response.raise_for_status()

# Usage
client = BrikkClient(api_key="your_api_key_here")

# List agents
agents = client.list_agents()
print(f"Total agents: {agents['total']}")

# Register agent
new_agent = client.register_agent(
    name="My Agent",
    description="Does cool stuff",
    endpoint_url="https://example.com/agent"
)
print(f"Registered: {new_agent['id']}")

# Search marketplace
results = client.search_marketplace("data analysis")
for agent in results:
    print(f"Found: {agent['name']}")

# Track usage
client.track_usage(
    agent_id=new_agent['id'],
    event_type="invocation",
    duration_ms=200,
    success=True
)
```

## Next Steps

- [JavaScript Quickstart](./javascript.md)
- [cURL Examples](./curl.md)
- [API Reference](../api/openapi.yaml)
- [Authentication Guide](../guides/authentication.md)

