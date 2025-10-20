# Phase 7 Deployment Guide

Step-by-step guide for deploying Phase 7 features to production.

## Pre-Deployment Checklist

### 1. Database Migration

Run the Phase 7 database migration:

```bash
# Review migration script
cat migrations/phase_7_marketplace_analytics.sql

# Apply migration to production database
psql $DATABASE_URL -f migrations/phase_7_marketplace_analytics.sql

# Verify tables were created
psql $DATABASE_URL -c "\dt marketplace_*"
psql $DATABASE_URL -c "\dt agent_*"
```

### 2. Environment Variables

Ensure these environment variables are set:

```bash
# Feature Flags (Redis-based)
REDIS_URL=redis://...

# Database
DATABASE_URL=postgresql://...

# Optional: Analytics Configuration
ANALYTICS_RETENTION_DAYS=365
TRENDING_CALCULATION_SCHEDULE="0 2 * * *"  # Daily at 2 AM
```

### 3. Feature Flag Configuration

Configure feature flags in Redis:

```bash
# Enable Phase 7 features gradually
redis-cli SET feature:MARKETPLACE true
redis-cli SET feature:ANALYTICS true
redis-cli SET feature:ENHANCED_DISCOVERY true
redis-cli SET feature:REVIEWS_RATINGS true

# Or disable specific features
redis-cli SET feature:MARKETPLACE false
```

### 4. Seed Data

Load initial categories and tags:

```bash
# The migration script includes seed data
# Verify it was loaded:
psql $DATABASE_URL -c "SELECT * FROM marketplace_categories;"
psql $DATABASE_URL -c "SELECT * FROM marketplace_tags;"
```

## Deployment Steps

### Step 1: Deploy Code

```bash
# Push to main branch (triggers auto-deploy on Render)
git push origin feature/phase-7-marketplace:main

# Or deploy manually
git push render main
```

### Step 2: Run Database Migration

```bash
# SSH into production server or use Render shell
render shell

# Run migration
psql $DATABASE_URL -f migrations/phase_7_marketplace_analytics.sql
```

### Step 3: Enable Features Gradually

Start with marketplace only:

```bash
redis-cli SET feature:MARKETPLACE true
redis-cli SET feature:ANALYTICS false
redis-cli SET feature:ENHANCED_DISCOVERY false
redis-cli SET feature:REVIEWS_RATINGS false
```

Monitor for 24 hours, then enable analytics:

```bash
redis-cli SET feature:ANALYTICS true
```

Continue enabling features one at a time.

### Step 4: Schedule Background Jobs

Set up analytics aggregation jobs:

```bash
# Add to crontab or use scheduler service
# Daily aggregation at 1 AM
0 1 * * * cd /app && python3 src/services/analytics_jobs.py aggregate

# Trending calculation at 2 AM
0 2 * * * cd /app && python3 src/services/analytics_jobs.py trending
```

Or use APScheduler in the application:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from src.services.analytics_jobs import schedule_analytics_jobs

scheduler = BackgroundScheduler()
scheduler.add_job(
    schedule_analytics_jobs,
    'cron',
    hour=1,
    minute=0
)
scheduler.start()
```

### Step 5: Verify Deployment

Test each feature:

```bash
# Test marketplace
curl https://api.getbrikk.com/api/v1/marketplace/agents

# Test analytics
curl -X POST https://api.getbrikk.com/api/v1/analytics/events \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test_user" \
  -d '{"agent_id": "test", "event_type": "invocation", "success": true}'

# Test discovery
curl https://api.getbrikk.com/api/v1/agent-discovery/search?q=test

# Test reviews
curl https://api.getbrikk.com/api/v1/reviews/agents/test_agent/summary
```

## Rollback Plan

If issues occur, disable features immediately:

```bash
# Disable all Phase 7 features
redis-cli SET feature:MARKETPLACE false
redis-cli SET feature:ANALYTICS false
redis-cli SET feature:ENHANCED_DISCOVERY false
redis-cli SET feature:REVIEWS_RATINGS false
```

To rollback database changes:

```bash
# Create rollback script
cat > rollback_phase_7.sql << 'EOF'
DROP TABLE IF EXISTS review_responses CASCADE;
DROP TABLE IF EXISTS review_votes CASCADE;
DROP TABLE IF EXISTS agent_reviews CASCADE;
DROP TABLE IF EXISTS agent_rating_summaries CASCADE;
DROP TABLE IF EXISTS agent_trending_scores CASCADE;
DROP TABLE IF EXISTS user_analytics_daily CASCADE;
DROP TABLE IF EXISTS agent_analytics_daily CASCADE;
DROP TABLE IF EXISTS agent_usage_events CASCADE;
DROP TABLE IF EXISTS agent_installations CASCADE;
DROP TABLE IF EXISTS marketplace_tags CASCADE;
DROP TABLE IF EXISTS marketplace_categories CASCADE;
DROP TABLE IF EXISTS marketplace_listings CASCADE;
EOF

# Run rollback (CAUTION: This deletes all Phase 7 data!)
psql $DATABASE_URL -f rollback_phase_7.sql
```

## Monitoring

### Key Metrics to Monitor

1. **API Response Times**
   - Marketplace endpoints: < 200ms
   - Analytics endpoints: < 500ms
   - Discovery/Search: < 1s

2. **Database Performance**
   - Query times for trending calculation
   - Index usage on marketplace_listings
   - Connection pool utilization

3. **Feature Flag Status**
   - Monitor Redis connectivity
   - Track feature flag changes

4. **Background Jobs**
   - Analytics aggregation completion time
   - Trending calculation success rate
   - Job failure alerts

### Monitoring Queries

```sql
-- Check marketplace activity
SELECT COUNT(*) as total_listings,
       COUNT(*) FILTER (WHERE status = 'published') as published,
       COUNT(*) FILTER (WHERE featured = true) as featured
FROM marketplace_listings;

-- Check analytics volume
SELECT DATE(created_at) as date,
       COUNT(*) as events,
       COUNT(DISTINCT agent_id) as unique_agents,
       COUNT(DISTINCT user_id) as unique_users
FROM agent_usage_events
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Check review activity
SELECT COUNT(*) as total_reviews,
       AVG(rating) as avg_rating,
       COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') as recent_reviews
FROM agent_reviews;

-- Check trending scores
SELECT COUNT(*) as agents_with_scores,
       AVG(trending_score) as avg_score,
       MAX(trending_score) as max_score
FROM agent_trending_scores;
```

## Performance Optimization

### Database Indexes

Ensure these indexes exist (created by migration):

```sql
-- Verify indexes
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename LIKE 'marketplace_%'
   OR tablename LIKE 'agent_%';
```

### Caching Strategy

Implement caching for frequently accessed data:

```python
# Cache trending agents for 1 hour
@cache.memoize(timeout=3600)
def get_trending_agents(limit=10):
    return DiscoveryService._get_trending_recommendations(limit)

# Cache rating summaries for 5 minutes
@cache.memoize(timeout=300)
def get_rating_summary(agent_id):
    return AgentRatingSummary.query.get(agent_id)
```

### Query Optimization

Monitor slow queries:

```sql
-- Enable slow query logging
ALTER DATABASE brikk_production SET log_min_duration_statement = 1000;

-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC
LIMIT 10;
```

## Security Considerations

### 1. Rate Limiting

Ensure rate limiting is enabled:

```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.headers.get('X-User-ID', request.remote_addr),
    default_limits=["1000 per hour"]
)

# Apply to Phase 7 routes
limiter.limit("100 per hour")(marketplace_bp)
limiter.limit("500 per hour")(analytics_bp)
```

### 2. Input Validation

All user input is validated:

- Review content: Max 5000 characters
- Search queries: Max 200 characters
- Tags: Max 10 per listing
- Rating: Must be 1-5

### 3. Authorization

Verify authorization checks:

- Publishers can only edit their own listings
- Users can only edit their own reviews
- Analytics data respects user privacy

### 4. SQL Injection Prevention

All queries use parameterized statements via SQLAlchemy ORM.

## Troubleshooting

### Issue: Trending Scores Not Updating

**Symptoms:** Trending agents list is stale

**Solution:**

```bash
# Manually trigger trending calculation
python3 src/services/analytics_jobs.py trending

# Check last update time
psql $DATABASE_URL -c "SELECT MAX(updated_at) FROM agent_trending_scores;"

# Verify cron job is running
crontab -l | grep trending
```

### Issue: High Database Load

**Symptoms:** Slow queries, timeouts

**Solution:**

```sql
-- Check active connections
SELECT COUNT(*) FROM pg_stat_activity;

-- Kill long-running queries
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'active'
  AND query_start < NOW() - INTERVAL '5 minutes';

-- Add missing indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usage_events_agent_date
ON agent_usage_events(agent_id, created_at);
```

### Issue: Feature Flag Not Working

**Symptoms:** Feature still disabled/enabled

**Solution:**

```bash
# Check Redis connection
redis-cli PING

# Verify flag value
redis-cli GET feature:MARKETPLACE

# Clear cache
redis-cli FLUSHDB

# Restart application
render restart
```

## Post-Deployment Tasks

### Week 1

- [ ] Monitor error rates and response times
- [ ] Verify background jobs are running
- [ ] Check database performance
- [ ] Review user feedback

### Week 2

- [ ] Enable remaining features if stable
- [ ] Optimize slow queries
- [ ] Adjust rate limits if needed
- [ ] Update documentation based on issues

### Month 1

- [ ] Analyze usage patterns
- [ ] Optimize trending algorithm
- [ ] Review and adjust caching strategy
- [ ] Plan Phase 8 features

## Support

For deployment issues, contact:

- **Engineering:** <engineering@getbrikk.com>
- **DevOps:** <devops@getbrikk.com>
- **On-call:** Use PagerDuty for critical issues
