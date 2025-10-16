# Phase 7: Agent Marketplace & Analytics - Architecture Design

**Version:** 1.0  
**Date:** October 16, 2025  
**Status:** Implementation In Progress

## Overview

This document outlines the architecture and implementation plan for Phase 7 of the Brikk AI
Infrastructure project.

## Goals

1. **Agent Marketplace** - Enable users to discover, publish, and share agents
2. **Agent Analytics** - Track usage, performance, and provide insights
3. **Enhanced Discovery** - Advanced search, filtering, and recommendations
4. **Rating & Reviews** - Community feedback and quality signals
5. **Monetization Ready** - Foundation for future paid agents

## Architecture Components

### 1. Agent Marketplace

#### Features

- **Agent Listing** - Browse all available agents
- **Agent Publishing** - Submit agents to marketplace
- **Agent Details** - Comprehensive agent information pages
- **Categories & Tags** - Organize agents by function and domain
- **Featured Agents** - Curated agent highlights
- **Agent Versions** - Version management and history

#### Database Schema

```sql
-- Marketplace listings (extends agent_registry from Phase 6)
CREATE TABLE marketplace_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_registry(id) ON DELETE CASCADE,
    publisher_id UUID NOT NULL,  -- User who published
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, published, archived
    visibility VARCHAR(20) NOT NULL DEFAULT 'public',  -- public, private, unlisted
    featured BOOLEAN DEFAULT FALSE,
    featured_until TIMESTAMP,
    category VARCHAR(100),
    tags TEXT[],  -- Array of tags
    short_description TEXT,
    long_description TEXT,
    icon_url TEXT,
    screenshots TEXT[],  -- Array of screenshot URLs
    demo_url TEXT,
    documentation_url TEXT,
    source_code_url TEXT,
    license VARCHAR(50),  -- MIT, Apache, Proprietary, etc.
    pricing_model VARCHAR(20) DEFAULT 'free',  -- free, paid, freemium
    price_amount DECIMAL(10, 2),
    price_currency VARCHAR(3) DEFAULT 'USD',
    install_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent categories
CREATE TABLE agent_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50),  -- Icon identifier
    parent_id UUID REFERENCES agent_categories(id),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent tags
CREATE TABLE agent_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(50) NOT NULL UNIQUE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent installations (track who installed what)
CREATE TABLE agent_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_registry(id),
    user_id UUID NOT NULL,
    installed_version VARCHAR(50),
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    uninstalled_at TIMESTAMP,
    UNIQUE(agent_id, user_id)
);
```

### 2. Agent Analytics

#### Analytics Features

- **Usage Tracking** - Track agent invocations and performance
- **Performance Metrics** - Response time, success rate, error rate
- **User Analytics** - Active users, retention, engagement
- **Dashboard** - Visual analytics and insights
- **Trending Agents** - Identify popular and growing agents
- **Comparative Analytics** - Compare agent performance

#### Analytics Database Schema

```sql
-- Agent usage events
CREATE TABLE agent_usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_registry(id),
    user_id UUID,
    event_type VARCHAR(50) NOT NULL,  -- invocation, error, timeout, etc.
    duration_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    metadata JSONB,  -- Flexible metadata storage
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent analytics aggregates (pre-computed for performance)
CREATE TABLE agent_analytics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_registry(id),
    date DATE NOT NULL,
    invocation_count INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    avg_duration_ms DECIMAL(10, 2),
    p50_duration_ms INTEGER,
    p95_duration_ms INTEGER,
    p99_duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, date)
);

-- User analytics
CREATE TABLE user_analytics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    date DATE NOT NULL,
    agents_used INTEGER DEFAULT 0,
    total_invocations INTEGER DEFAULT 0,
    active_time_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);
```

### 3. Rating & Review System

#### Discovery Features

- **Star Ratings** - 1-5 star rating system
- **Written Reviews** - Detailed user feedback
- **Helpful Votes** - Community-driven review ranking
- **Verified Users** - Badge for users who actually used the agent
- **Response System** - Publishers can respond to reviews
- **Moderation** - Flag inappropriate reviews

#### Reviews Database Schema

```sql
-- Agent ratings and reviews
CREATE TABLE agent_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_registry(id),
    user_id UUID NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(200),
    review_text TEXT,
    verified_user BOOLEAN DEFAULT FALSE,  -- User has actually used the agent
    helpful_count INTEGER DEFAULT 0,
    unhelpful_count INTEGER DEFAULT 0,
    flagged BOOLEAN DEFAULT FALSE,
    flag_reason TEXT,
    publisher_response TEXT,
    publisher_response_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, user_id)  -- One review per user per agent
);

-- Review helpfulness votes
CREATE TABLE review_votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID NOT NULL REFERENCES agent_reviews(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    vote VARCHAR(10) NOT NULL CHECK (vote IN ('helpful', 'unhelpful')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(review_id, user_id)
);

-- Agent rating aggregates
CREATE TABLE agent_rating_summary (
    agent_id UUID PRIMARY KEY REFERENCES agent_registry(id) ON DELETE CASCADE,
    total_reviews INTEGER DEFAULT 0,
    average_rating DECIMAL(3, 2) DEFAULT 0.0,
    rating_1_count INTEGER DEFAULT 0,
    rating_2_count INTEGER DEFAULT 0,
    rating_3_count INTEGER DEFAULT 0,
    rating_4_count INTEGER DEFAULT 0,
    rating_5_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. Enhanced Discovery

#### Enhanced Discovery Features

- **Full-Text Search** - Search agent names, descriptions, tags
- **Advanced Filtering** - Filter by category, rating, price, etc.
- **Sorting Options** - Sort by popularity, rating, recent, trending
- **Recommendations** - Personalized agent suggestions
- **Similar Agents** - Find related agents
- **Trending Calculation** - Identify rapidly growing agents

#### Implementation

- Use PostgreSQL full-text search for agent discovery
- Implement recommendation engine based on user behavior
- Calculate trending scores using time-weighted metrics
- Cache popular searches and recommendations

## API Endpoints

### Marketplace Endpoints

```http
GET    /api/v1/marketplace/agents              # List marketplace agents
GET    /api/v1/marketplace/agents/:id          # Get agent details
POST   /api/v1/marketplace/agents              # Publish new agent
PUT    /api/v1/marketplace/agents/:id          # Update agent listing
DELETE /api/v1/marketplace/agents/:id          # Remove from marketplace

GET    /api/v1/marketplace/categories          # List categories
GET    /api/v1/marketplace/tags                # List popular tags
GET    /api/v1/marketplace/featured            # Get featured agents
GET    /api/v1/marketplace/trending            # Get trending agents

POST   /api/v1/marketplace/agents/:id/install  # Install agent
DELETE /api/v1/marketplace/agents/:id/install  # Uninstall agent
GET    /api/v1/marketplace/installed           # Get user's installed agents
```

### Analytics Endpoints

```http
GET    /api/v1/analytics/agents/:id            # Get agent analytics
GET    /api/v1/analytics/agents/:id/usage      # Get usage metrics
GET    /api/v1/analytics/agents/:id/performance # Get performance metrics
GET    /api/v1/analytics/dashboard             # Get user dashboard
GET    /api/v1/analytics/trending              # Get trending analytics
```

### Review Endpoints

```http
GET    /api/v1/reviews/agents/:id              # Get agent reviews
POST   /api/v1/reviews/agents/:id              # Submit review
PUT    /api/v1/reviews/:id                     # Update review
DELETE /api/v1/reviews/:id                     # Delete review

POST   /api/v1/reviews/:id/vote                # Vote on review helpfulness
POST   /api/v1/reviews/:id/flag                # Flag inappropriate review
POST   /api/v1/reviews/:id/respond             # Publisher response
```

### Search & Discovery Endpoints

```http
GET    /api/v1/search/agents                   # Search agents
GET    /api/v1/discover/recommended            # Get recommendations
GET    /api/v1/discover/similar/:id            # Get similar agents
GET    /api/v1/discover/popular                # Get popular agents
```

## Feature Flags

Phase 7 features will be controlled by feature flags for safe rollout:

```python
# Feature flags for Phase 7
AGENT_MARKETPLACE = "agent_marketplace"
AGENT_ANALYTICS = "agent_analytics"
AGENT_REVIEWS = "agent_reviews"
ENHANCED_DISCOVERY = "enhanced_discovery"
TRENDING_AGENTS = "trending_agents"
AGENT_RECOMMENDATIONS = "agent_recommendations"
```

## Security Considerations

### Authentication & Authorization
- All marketplace operations require authentication
- Publishers can only modify their own agents
- Admin role for marketplace moderation
- Rate limiting on all API endpoints

### Data Privacy
- Analytics data is anonymized where possible
- User IDs are hashed in public-facing analytics
- GDPR compliance for user data
- Option to opt-out of analytics tracking

### Content Moderation
- Review flagging system
- Automated spam detection
- Manual moderation queue
- Publisher verification system

## Performance Optimization

### Caching Strategy
- Cache popular agent listings (Redis, 5 min TTL)
- Cache category and tag lists (Redis, 1 hour TTL)
- Cache trending agents (Redis, 15 min TTL)
- Cache user recommendations (Redis, 30 min TTL)

### Database Optimization
- Indexes on frequently queried columns
- Materialized views for complex analytics
- Partitioning for large event tables
- Regular VACUUM and ANALYZE operations

### Background Jobs
- Analytics aggregation (hourly)
- Trending calculation (every 15 minutes)
- Recommendation updates (daily)
- Review spam detection (real-time)

## Migration Strategy

### Phase 1: Database Schema
1. Create new tables for marketplace, analytics, reviews
2. Add indexes and constraints
3. Migrate existing agent_registry data to marketplace_listings
4. Validate data integrity

### Phase 2: Core Functionality
1. Implement marketplace listing endpoints
2. Add agent publishing workflow
3. Implement basic analytics tracking
4. Deploy with feature flags disabled

### Phase 3: Advanced Features
1. Enable marketplace feature flag
2. Implement review system
3. Add enhanced discovery
4. Enable analytics feature flag

### Phase 4: Optimization
1. Monitor performance metrics
2. Optimize slow queries
3. Implement caching
4. Enable all feature flags

## Testing Strategy

### Unit Tests
- Test all business logic functions
- Test database models and relationships
- Test API endpoint handlers
- Test analytics calculations

### Integration Tests
- Test full marketplace workflow
- Test analytics data flow
- Test review submission and moderation
- Test search and discovery

### Performance Tests
- Load test marketplace listing endpoints
- Stress test analytics aggregation
- Test search performance with large datasets
- Test concurrent review submissions

## Monitoring & Observability

### Metrics to Track
- Marketplace listing views and installs
- Agent usage and performance metrics
- Review submission rate and quality
- Search query performance
- API endpoint latency and error rates

### Alerts
- High error rate on marketplace endpoints
- Slow analytics aggregation
- Unusual review patterns (spam detection)
- Database performance degradation

## Documentation Requirements

### User Documentation
- Marketplace user guide
- Agent publishing guide
- Analytics dashboard guide
- Review guidelines

### Developer Documentation
- API reference for all endpoints
- Database schema documentation
- Analytics data model
- Integration examples

## Timeline

### Week 1: Foundation
- Database schema implementation
- Core marketplace models
- Basic API endpoints

### Week 2: Marketplace
- Agent listing and publishing
- Category and tag management
- Installation tracking

### Week 3: Analytics
- Usage event tracking
- Analytics aggregation
- Dashboard endpoints

### Week 4: Reviews & Discovery
- Review system implementation
- Enhanced search
- Recommendations engine

### Week 5: Testing & Polish
- Integration testing
- Performance optimization
- Documentation
- Feature flag rollout

## Success Metrics

### Marketplace Adoption
- Number of published agents
- Number of agent installations
- Active marketplace users
- Featured agent engagement

### Analytics Usage
- Dashboard views
- Analytics API usage
- Trending agent views
- Performance insights accessed

### Community Engagement
- Number of reviews submitted
- Review helpfulness votes
- Publisher responses
- User retention rate

## Future Enhancements

### Phase 8 Considerations
- Paid agent marketplace
- Agent bundles and collections
- Advanced analytics (ML-powered insights)
- Agent certification program
- Marketplace API for third-party integrations
- White-label marketplace options

## Conclusion

Phase 7 transforms the Brikk AI Infrastructure from a simple agent registry into a comprehensive agent ecosystem with marketplace, analytics, and community features. This foundation enables future monetization, enterprise features, and ecosystem growth.
