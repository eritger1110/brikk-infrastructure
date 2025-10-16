# Phase 7: Agent Marketplace & Analytics

Complete agent ecosystem with marketplace, analytics, discovery, and reviews.

## Overview

Phase 7 introduces a comprehensive agent marketplace and analytics platform, enabling users to discover, install, rate, and track agent usage across the Brikk platform.

## Features

### 🏪 Agent Marketplace

- **Agent Listings:** Publish agents with descriptions, categories, tags, and pricing
- **Installation Tracking:** Track agent installations and usage
- **Categories & Tags:** Organize agents for easy discovery
- **Featured Agents:** Highlight top agents
- **Publisher Profiles:** Track agent publishers

### 📊 Analytics System

- **Usage Tracking:** Real-time event tracking for all agent invocations
- **Performance Metrics:** P50, P95, P99 latency tracking
- **Daily Aggregation:** Automated daily analytics rollup
- **Trending Algorithm:** Multi-factor trending score calculation
- **User Dashboards:** Personal analytics for users
- **Publisher Insights:** Detailed metrics for agent publishers

### 🔍 Enhanced Discovery

- **Full-Text Search:** Search agents by name, description, tags
- **Advanced Filtering:** Filter by category, pricing, rating
- **Personalized Recommendations:** AI-powered agent suggestions
- **Similar Agents:** Find related agents
- **Curated Collections:** Trending, New & Noteworthy, Most Popular
- **Category Browsing:** Explore agents by category

### ⭐ Reviews & Ratings

- **5-Star Ratings:** User ratings for agents
- **Written Reviews:** Detailed feedback with pros/cons
- **Helpful Voting:** Community-driven review quality
- **Publisher Responses:** Engage with user feedback
- **Rating Summaries:** Aggregated ratings and distributions
- **Review Moderation:** Tools for managing reviews

## Architecture

### Database Schema

**11 new tables:**

1. `marketplace_listings` - Agent marketplace listings
2. `marketplace_categories` - Marketplace categories
3. `marketplace_tags` - Available tags
4. `agent_installations` - User agent installations
5. `agent_usage_events` - Raw usage events
6. `agent_analytics_daily` - Daily analytics aggregates
7. `user_analytics_daily` - User activity aggregates
8. `agent_trending_scores` - Trending algorithm scores
9. `agent_reviews` - User reviews
10. `review_votes` - Helpful/not helpful votes
11. `agent_rating_summaries` - Aggregated ratings
12. `review_responses` - Publisher responses to reviews

### API Endpoints

**43 new endpoints across 4 blueprints:**

- **Marketplace:** 15 endpoints
- **Analytics:** 10 endpoints
- **Discovery:** 7 endpoints
- **Reviews:** 11 endpoints

### Background Jobs

- **Daily Aggregation:** Rolls up usage events into daily summaries
- **Trending Calculation:** Calculates trending scores using velocity, momentum, recency, and popularity
- **Scheduled:** Runs daily at 1 AM (aggregation) and 2 AM (trending)

## Technology Stack

- **Backend:** Flask, SQLAlchemy
- **Database:** PostgreSQL with JSONB for flexible data
- **Caching:** Redis for feature flags and caching
- **Scheduling:** APScheduler for background jobs
- **Search:** PostgreSQL full-text search (can be upgraded to Elasticsearch)

## Getting Started

### 1. Database Setup

```bash
# Run migration
psql $DATABASE_URL -f migrations/phase_7_marketplace_analytics.sql

# Verify tables
psql $DATABASE_URL -c "\dt marketplace_*"
```

### 2. Enable Features

```bash
# Enable all Phase 7 features
redis-cli SET feature:MARKETPLACE true
redis-cli SET feature:ANALYTICS true
redis-cli SET feature:ENHANCED_DISCOVERY true
redis-cli SET feature:REVIEWS_RATINGS true
```

### 3. Start Background Jobs

```bash
# Test jobs manually
python3 src/services/analytics_jobs.py aggregate
python3 src/services/analytics_jobs.py trending

# Or schedule via cron
0 1 * * * cd /app && python3 src/services/analytics_jobs.py aggregate
0 2 * * * cd /app && python3 src/services/analytics_jobs.py trending
```

### 4. Test Endpoints

```bash
# List marketplace agents
curl https://api.getbrikk.com/api/v1/marketplace/agents

# Search agents
curl "https://api.getbrikk.com/api/v1/agent-discovery/search?q=productivity"

# Get recommendations
curl -H "X-User-ID: user_123" \
  https://api.getbrikk.com/api/v1/agent-discovery/recommendations

# Get trending agents
curl https://api.getbrikk.com/api/v1/analytics/trending
```

## Key Concepts

### Trending Algorithm

The trending score is calculated using four factors:

1. **Velocity (40%):** Growth rate over last 7 days vs previous 7 days
2. **Momentum (30%):** Acceleration of growth within the last week
3. **Recency (20%):** Boost for agents with recent activity
4. **Popularity (10%):** Base score from current install count

Formula:

```
Trending Score = (Velocity × 0.4) + (Momentum × 0.3) + (Recency × 0.2) + (Popularity × 0.1)
```

Normalized to 0-100 scale.

### Recommendation Engine

Uses three strategies:

1. **Collaborative Filtering:** Agents installed by similar users
2. **Content-Based Filtering:** Agents in same categories/tags
3. **Trending-Based:** Popular agents for new users

### Feature Flags

All Phase 7 features are controlled by feature flags:

```python
from src.utils.feature_flags import FeatureFlagManager, FeatureFlag

flags = FeatureFlagManager()

if flags.is_enabled(FeatureFlag.MARKETPLACE):
    # Marketplace features enabled
    pass
```

## API Documentation

See [Phase 7 API Documentation](./api/phase-7-api.md) for complete API reference.

## Deployment Guide

See [Phase 7 Deployment Guide](./deployment/phase-7-deployment.md) for deployment instructions.

## Performance

### Expected Load

- **Marketplace:** 1000 req/min
- **Analytics Events:** 5000 events/min
- **Discovery/Search:** 500 req/min
- **Reviews:** 100 req/min

### Optimization

- **Database Indexes:** All critical queries indexed
- **Caching:** Redis caching for trending agents, rating summaries
- **Background Jobs:** Heavy computations moved to background
- **Pagination:** All list endpoints support pagination

### Monitoring

Key metrics to monitor:

- API response times (< 200ms for marketplace, < 500ms for analytics)
- Background job completion time
- Database query performance
- Feature flag availability

## Security

- **Authentication:** X-User-ID header for authenticated requests
- **Authorization:** Users can only edit their own content
- **Rate Limiting:** 1000 req/hour for authenticated, 100 for anonymous
- **Input Validation:** All inputs validated and sanitized
- **SQL Injection:** Protected via SQLAlchemy ORM

## Testing

Run tests:

```bash
# All Phase 7 tests
pytest tests/test_marketplace.py
pytest tests/test_analytics.py
pytest tests/test_discovery.py
pytest tests/test_reviews.py

# Integration tests
pytest tests/integration/test_phase_7.py
```

## Troubleshooting

### Trending Scores Not Updating

```bash
# Manually trigger calculation
python3 src/services/analytics_jobs.py trending

# Check last update
psql $DATABASE_URL -c "SELECT MAX(updated_at) FROM agent_trending_scores;"
```

### Feature Not Working

```bash
# Check feature flag
redis-cli GET feature:MARKETPLACE

# Enable feature
redis-cli SET feature:MARKETPLACE true
```

### Slow Queries

```sql
-- Check slow queries
SELECT query, mean_time
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC;

-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_name ON table_name(column);
```

## Roadmap

### Phase 7.1 (Future)

- Elasticsearch integration for better search
- Agent versioning and updates
- Subscription management
- Advanced analytics dashboards
- Review moderation tools

### Phase 7.2 (Future)

- Agent collections and bundles
- Social features (following, sharing)
- Agent recommendations API
- Webhook notifications
- GraphQL API

## Contributing

When contributing to Phase 7:

1. Follow existing code patterns
2. Add tests for new features
3. Update documentation
4. Use feature flags for new features
5. Run CI guards before committing

## Support

- **Documentation:** See `/docs` directory
- **API Reference:** `/docs/api/phase-7-api.md`
- **Deployment:** `/docs/deployment/phase-7-deployment.md`
- **Architecture:** `/docs/architecture/phase-7-design.md`

## License

Copyright © 2025 Brikk. All rights reserved.

