# JavaScript SDK Quickstart

Get started with the Brikk AI Infrastructure API using JavaScript/Node.js.

## Installation

```bash
npm install axios
# or
yarn add axios
```

## Authentication

Get your API key from the [Brikk Dashboard](https://app.getbrikk.com/settings/api-keys).

```javascript
const axios = require('axios');

const API_KEY = 'your_api_key_here';
const BASE_URL = 'https://api.getbrikk.com';

const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  }
});
```

## List Agents

```javascript
async function listAgents() {
  const response = await client.get('/api/v1/agents');
  const { agents, total } = response.data;
  
  console.log(`Found ${total} agents`);
  agents.forEach(agent => {
    console.log(`- ${agent.name}: ${agent.description}`);
  });
}

listAgents();
```

## Register an Agent

```javascript
async function registerAgent() {
  const agentData = {
    name: 'My AI Agent',
    description: 'An intelligent agent for task automation',
    endpoint_url: 'https://my-agent.example.com/invoke',
    capabilities: ['text-generation', 'data-analysis']
  };
  
  const response = await client.post('/api/v1/agents', agentData);
  const agent = response.data;
  
  console.log(`Agent registered with ID: ${agent.id}`);
  return agent;
}
```

## Search Marketplace

```javascript
async function searchMarketplace(category = 'AI/ML') {
  const response = await client.get('/api/v1/marketplace/agents', {
    params: {
      category,
      sort: 'popular',
      page: 1
    }
  });
  
  const { agents } = response.data;
  agents.forEach(listing => {
    console.log(`${listing.title} - Rating: ${listing.rating}/5`);
  });
}
```

## Track Usage

```javascript
async function trackUsage(agentId) {
  const eventData = {
    agent_id: agentId,
    event_type: 'invocation',
    duration_ms: 150,
    success: true,
    metadata: {
      model: 'gpt-4',
      tokens: 500
    }
  };
  
  await client.post('/api/v1/analytics/events', eventData);
  console.log('Usage tracked successfully');
}
```

## Submit a Review

```javascript
async function submitReview(agentId) {
  const reviewData = {
    rating: 5,
    title: 'Excellent agent!',
    comment: 'This agent works perfectly for my use case.',
    pros: 'Fast, accurate, easy to integrate',
    cons: 'None so far'
  };
  
  await client.post(`/api/v1/reviews/agents/${agentId}`, reviewData);
  console.log('Review submitted!');
}
```

## Error Handling

```javascript
async function safeRequest() {
  try {
    const response = await client.get('/api/v1/agents');
    return response.data;
  } catch (error) {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      
      if (status === 401) {
        console.error('Authentication failed. Check your API key.');
      } else if (status === 503) {
        console.error(`Feature disabled: ${data.message}`);
      } else {
        console.error(`Error ${status}: ${data.message}`);
      }
    } else if (error.request) {
      // Request made but no response
      console.error('No response from server');
    } else {
      // Error in request setup
      console.error('Request error:', error.message);
    }
    throw error;
  }
}
```

## Complete SDK Class

```javascript
class BrikkClient {
  constructor(apiKey, baseURL = 'https://api.getbrikk.com') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      }
    });
  }
  
  async listAgents(page = 1, perPage = 20) {
    const response = await this.client.get('/api/v1/agents', {
      params: { page, per_page: perPage }
    });
    return response.data;
  }
  
  async registerAgent(name, description, endpointUrl) {
    const response = await this.client.post('/api/v1/agents', {
      name,
      description,
      endpoint_url: endpointUrl
    });
    return response.data;
  }
  
  async searchMarketplace(query, limit = 10) {
    const response = await this.client.get('/api/v1/agent-discovery/search', {
      params: { q: query, limit }
    });
    return response.data.results;
  }
  
  async trackUsage(agentId, eventType, durationMs, success) {
    await this.client.post('/api/v1/analytics/events', {
      agent_id: agentId,
      event_type: eventType,
      duration_ms: durationMs,
      success
    });
  }
  
  async submitReview(agentId, rating, title, comment) {
    const response = await this.client.post(
      `/api/v1/reviews/agents/${agentId}`,
      { rating, title, comment }
    );
    return response.data;
  }
}

// Usage
const brikk = new BrikkClient('your_api_key_here');

(async () => {
  // List agents
  const agents = await brikk.listAgents();
  console.log(`Total agents: ${agents.total}`);
  
  // Register agent
  const newAgent = await brikk.registerAgent(
    'My Agent',
    'Does cool stuff',
    'https://example.com/agent'
  );
  console.log(`Registered: ${newAgent.id}`);
  
  // Search marketplace
  const results = await brikk.searchMarketplace('data analysis');
  results.forEach(agent => {
    console.log(`Found: ${agent.name}`);
  });
  
  // Track usage
  await brikk.trackUsage(newAgent.id, 'invocation', 200, true);
})();
```

## Browser Usage

```html
<!DOCTYPE html>
<html>
<head>
  <title>Brikk API Example</title>
  <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
</head>
<body>
  <h1>Brikk API Demo</h1>
  <div id="agents"></div>
  
  <script>
    const API_KEY = 'your_api_key_here';
    const BASE_URL = 'https://api.getbrikk.com';
    
    const client = axios.create({
      baseURL: BASE_URL,
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    });
    
    async function loadAgents() {
      try {
        const response = await client.get('/api/v1/agents');
        const { agents } = response.data;
        
        const container = document.getElementById('agents');
        container.innerHTML = agents.map(agent => `
          <div class="agent">
            <h3>${agent.name}</h3>
            <p>${agent.description}</p>
          </div>
        `).join('');
      } catch (error) {
        console.error('Failed to load agents:', error);
      }
    }
    
    loadAgents();
  </script>
</body>
</html>
```

## Next Steps

- [Python Quickstart](./python.md)
- [cURL Examples](./curl.md)
- [API Reference](../api/openapi.yaml)
- [Authentication Guide](../guides/authentication.md)

