# Phase 7 API Documentation

Complete API reference for Agent Marketplace, Analytics, Discovery, and Reviews features.

## Table of Contents

- [Authentication](#authentication)
- [Marketplace API](#marketplace-api)
- [Analytics API](#analytics-api)
- [Discovery API](#discovery-api)
- [Reviews API](#reviews-api)
- [Error Codes](#error-codes)

## Authentication

All authenticated endpoints require the `X-User-ID` header:

```http
X-User-ID: user_123456
```

## Marketplace API

Base URL: `/api/v1/marketplace`

### List Agents

Get published agents with filtering and pagination.

```http
GET /api/v1/marketplace/agents
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Filter by category |
| `tags` | string | Comma-separated tags |
| `pricing` | string | Filter by pricing (free, paid, freemium) |
| `featured` | boolean | Show only featured agents |
| `sort` | string | Sort order (popular, recent, rating) |
| `limit` | integer | Results per page (max: 100) |
| `offset` | integer | Pagination offset |

**Response:**

```json
{
  "agents": [
    {
      "id": "listing_123",
      "agent_id": "agent_456",
      "short_description": "AI assistant for data analysis",
      "category": "productivity",
      "tags": ["data", "analytics"],
      "pricing_model": "freemium",
      "install_count": 1250,
      "featured": true,
      "published_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

### Get Agent Details

Get detailed information about a specific agent listing.

```http
GET /api/v1/marketplace/agents/{agent_id}
```

**Response:**

```json
{
  "id": "listing_123",
  "agent_id": "agent_456",
  "short_description": "AI assistant for data analysis",
  "long_description": "Comprehensive description...",
  "category": "productivity",
  "tags": ["data", "analytics"],
  "pricing_model": "freemium",
  "pricing_details": {...},
  "install_count": 1250,
  "featured": true,
  "publisher_id": "user_789",
  "published_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-20T14:22:00Z"
}
```

### Publish Agent

Publish an agent to the marketplace.

```http
POST /api/v1/marketplace/agents
```

**Request Body:**

```json
{
  "agent_id": "agent_456",
  "short_description": "AI assistant for data analysis",
  "long_description": "Comprehensive description...",
  "category": "productivity",
  "tags": ["data", "analytics"],
  "pricing_model": "freemium",
  "pricing_details": {
    "free_tier": "100 requests/month",
    "paid_tier": "$9.99/month for unlimited"
  }
}
```

**Response:** `201 Created`

### Install Agent

Install an agent for the current user.

```http
POST /api/v1/marketplace/agents/{agent_id}/install
```

**Response:** `201 Created`

### Uninstall Agent

Uninstall an agent for the current user.

```http
POST /api/v1/marketplace/agents/{agent_id}/uninstall
```

**Response:** `200 OK`

### Get Categories

Get all available marketplace categories.

```http
GET /api/v1/marketplace/categories
```

**Response:**

```json
{
  "categories": [
    {
      "slug": "productivity",
      "name": "Productivity",
      "description": "Tools to boost your productivity",
      "agent_count": 45
    }
  ]
}
```

### Get Tags

Get all available tags.

```http
GET /api/v1/marketplace/tags
```

**Response:**

```json
{
  "tags": [
    {
      "slug": "data-analysis",
      "name": "Data Analysis",
      "usage_count": 23
    }
  ]
}
```

## Analytics API

Base URL: `/api/v1/analytics`

### Track Usage Event

Record an agent usage event.

```http
POST /api/v1/analytics/events
```

**Request Body:**

```json
{
  "agent_id": "agent_456",
  "event_type": "invocation",
  "success": true,
  "duration_ms": 1250,
  "error_message": null,
  "event_metadata": {
    "model": "gpt-4",
    "tokens": 500
  }
}
```

**Response:** `201 Created`

### Get Agent Analytics

Get analytics for a specific agent.

```http
GET /api/v1/analytics/agents/{agent_id}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | date | Start date (YYYY-MM-DD) |
| `end_date` | date | End date (YYYY-MM-DD) |
| `granularity` | string | daily, weekly, monthly |

**Response:**

```json
{
  "agent_id": "agent_456",
  "period": {
    "start": "2025-01-01",
    "end": "2025-01-31",
    "granularity": "daily"
  },
  "metrics": [
    {
      "date": "2025-01-15",
      "invocation_count": 150,
      "unique_users": 45,
      "success_count": 145,
      "error_count": 5,
      "avg_duration_ms": 1250.5,
      "p95_duration_ms": 2100.0
    }
  ],
  "summary": {
    "total_invocations": 4500,
    "total_unique_users": 320,
    "success_rate": 0.967,
    "avg_duration_ms": 1180.3
  }
}
```

### Get Trending Agents

Get currently trending agents.

```http
GET /api/v1/analytics/trending
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Max agents to return (max: 100) |
| `category` | string | Filter by category |

**Response:**

```json
{
  "trending_agents": [
    {
      "agent_id": "agent_456",
      "trending_score": 85.5,
      "rank": 1,
      "velocity": 1.25,
      "momentum": 0.85,
      "listing": {...}
    }
  ]
}
```

### Get User Dashboard

Get analytics dashboard for the current user.

```http
GET /api/v1/analytics/dashboard
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | week, month, year |

**Response:**

```json
{
  "user_id": "user_123",
  "period": "month",
  "summary": {
    "agents_used": 12,
    "total_invocations": 450,
    "active_time_minutes": 320,
    "favorite_agent": "agent_456"
  },
  "daily_activity": [...]
}
```

## Discovery API

Base URL: `/api/v1/agent-discovery`

### Search Agents

Search for agents with advanced filtering.

```http
GET /api/v1/agent-discovery/search
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query |
| `category` | string | Filter by category |
| `tags` | string | Comma-separated tags |
| `pricing` | string | Filter by pricing |
| `min_rating` | float | Minimum rating (1-5) |
| `limit` | integer | Results per page (max: 100) |
| `offset` | integer | Pagination offset |

**Response:**

```json
{
  "results": [...],
  "total": 45,
  "limit": 20,
  "offset": 0,
  "query": "data analysis"
}
```

### Get Recommendations

Get personalized agent recommendations.

```http
GET /api/v1/agent-discovery/recommendations
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Max recommendations (max: 50) |
| `exclude_installed` | boolean | Exclude installed agents |

**Response:**

```json
{
  "recommendations": [
    {
      "agent_id": "agent_789",
      "recommendation_reason": "popular_with_similar_users",
      "recommendation_score": 0.85,
      "listing": {...}
    }
  ],
  "personalized": true,
  "user_id": "user_123"
}
```

### Get Similar Agents

Find agents similar to a specific agent.

```http
GET /api/v1/agent-discovery/similar/{agent_id}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Max similar agents (max: 20) |

**Response:**

```json
{
  "agent_id": "agent_456",
  "similar_agents": [
    {
      "agent_id": "agent_789",
      "similarity_score": 0.85,
      "listing": {...}
    }
  ],
  "count": 5
}
```

### Get Popular in Category

Get most popular agents in a category.

```http
GET /api/v1/agent-discovery/popular/{category}
```

**Response:**

```json
{
  "category": "productivity",
  "popular_agents": [...],
  "count": 10
}
```

### Get New Releases

Get recently published agents.

```http
GET /api/v1/agent-discovery/new-releases
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `days` | integer | Days to look back (max: 90) |
| `limit` | integer | Max agents (max: 50) |

**Response:**

```json
{
  "new_releases": [...],
  "days": 30,
  "count": 15
}
```

### Get Collections

Get curated collections of agents.

```http
GET /api/v1/agent-discovery/collections
```

**Response:**

```json
{
  "collections": [
    {
      "id": "trending",
      "title": "Trending Now",
      "description": "Agents gaining popularity",
      "agents": [...]
    }
  ],
  "count": 3
}
```

## Reviews API

Base URL: `/api/v1/reviews`

### Submit Review

Submit a review for an agent.

```http
POST /api/v1/reviews/agents/{agent_id}
```

**Request Body:**

```json
{
  "rating": 5,
  "title": "Excellent agent!",
  "content": "This agent has been incredibly helpful...",
  "pros": ["Fast", "Accurate", "Easy to use"],
  "cons": ["Could use more features"]
}
```

**Response:** `201 Created`

### Update Review

Update an existing review.

```http
PUT /api/v1/reviews/{review_id}
```

**Request Body:**

```json
{
  "rating": 4,
  "title": "Updated title",
  "content": "Updated content..."
}
```

**Response:** `200 OK`

### Delete Review

Delete a review.

```http
DELETE /api/v1/reviews/{review_id}
```

**Response:** `200 OK`

### Get Agent Reviews

Get reviews for an agent.

```http
GET /api/v1/reviews/agents/{agent_id}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `sort` | string | recent, helpful, rating_high, rating_low |
| `rating` | integer | Filter by rating (1-5) |
| `page` | integer | Page number |
| `per_page` | integer | Items per page (max: 100) |

**Response:**

```json
{
  "reviews": [
    {
      "id": "review_123",
      "agent_id": "agent_456",
      "user_id": "user_789",
      "rating": 5,
      "title": "Excellent agent!",
      "content": "This agent has been incredibly helpful...",
      "pros": ["Fast", "Accurate"],
      "cons": [],
      "helpful_count": 15,
      "not_helpful_count": 2,
      "created_at": "2025-01-15T10:30:00Z",
      "publisher_response": {
        "content": "Thank you for your feedback!",
        "created_at": "2025-01-16T09:00:00Z"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "pages": 3
  }
}
```

### Vote on Review

Vote on a review (helpful/not helpful).

```http
POST /api/v1/reviews/{review_id}/vote
```

**Request Body:**

```json
{
  "vote_type": "helpful"
}
```

**Response:** `200 OK`

### Remove Vote

Remove your vote from a review.

```http
DELETE /api/v1/reviews/{review_id}/vote
```

**Response:** `200 OK`

### Respond to Review

Publisher responds to a review.

```http
POST /api/v1/reviews/{review_id}/response
```

**Request Body:**

```json
{
  "content": "Thank you for your feedback! We're working on..."
}
```

**Response:** `201 Created`

### Get Rating Summary

Get rating summary for an agent.

```http
GET /api/v1/reviews/agents/{agent_id}/summary
```

**Response:**

```json
{
  "agent_id": "agent_456",
  "total_reviews": 45,
  "average_rating": 4.5,
  "rating_distribution": {
    "5": 25,
    "4": 15,
    "3": 3,
    "2": 1,
    "1": 1
  }
}
```

## Error Codes

Standard HTTP status codes are used:

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request - Invalid input |
| `401` | Unauthorized - Authentication required |
| `403` | Forbidden - Insufficient permissions |
| `404` | Not Found - Resource doesn't exist |
| `409` | Conflict - Resource already exists |
| `500` | Internal Server Error |
| `503` | Service Unavailable - Feature disabled |

**Error Response Format:**

```json
{
  "error": "error_code",
  "message": "Human-readable error message"
}
```

## Rate Limiting

All API endpoints are rate-limited:

- **Authenticated requests:** 1000 requests/hour
- **Anonymous requests:** 100 requests/hour

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1642435200
```

## Feature Flags

Phase 7 features can be enabled/disabled via feature flags:

- `MARKETPLACE` - Agent marketplace features
- `ANALYTICS` - Analytics tracking and dashboards
- `ENHANCED_DISCOVERY` - Advanced search and recommendations
- `REVIEWS_RATINGS` - Review and rating system

When a feature is disabled, endpoints return `503 Service Unavailable`.

