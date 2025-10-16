# Database Migrations

This directory contains SQL migration scripts for the Brikk AI Infrastructure database.

## Phase 7 Migration

The Phase 7 migration creates all tables for the marketplace, analytics, discovery, and reviews systems.

### Prerequisites

- PostgreSQL database
- Phase 6 `agents` table must exist
- Database connection with CREATE TABLE permissions

### Running the Migration

#### Option 1: Via psql (Recommended for Production)

```bash
# Set your database URL
export DATABASE_URL="postgresql://user:password@host:port/database"

# Run the migration
psql $DATABASE_URL -f migrations/phase_7_marketplace_analytics.sql
```

#### Option 2: Via Render Dashboard

1. Go to your Render PostgreSQL dashboard
2. Click "Connect" and copy the External Database URL
3. Use a PostgreSQL client to connect
4. Copy and paste the contents of `phase_7_marketplace_analytics.sql`
5. Execute the script

#### Option 3: Via Python Script

```bash
# Ensure DATABASE_URL is set
python3 scripts/run_migration.py migrations/phase_7_marketplace_analytics.sql
```

### Verifying the Migration

After running the migration, verify it was successful:

```bash
python3 scripts/verify_phase7_migration.py
```

This will check that all 11 Phase 7 tables exist and are properly populated with seed data.

### Tables Created

The migration creates the following tables:

**Marketplace (5 tables):**
- `marketplace_listings` - Agent listings in the marketplace
- `marketplace_categories` - Categories for organizing agents
- `marketplace_tags` - Tags for agent discovery
- `agent_installations` - Tracks agent installations by users

**Analytics (3 tables):**
- `agent_usage_events` - Real-time usage tracking
- `agent_daily_stats` - Aggregated daily statistics
- `agent_trending_scores` - Trending algorithm scores

**Reviews (4 tables):**
- `agent_reviews` - User reviews and ratings
- `review_votes` - Helpful/not helpful votes on reviews
- `agent_rating_summaries` - Aggregated rating statistics
- `publisher_review_responses` - Publisher responses to reviews

### Seed Data

The migration automatically populates:
- **10 categories:** AI/ML, Data Processing, DevOps, etc.
- **15 tags:** python, javascript, automation, etc.

### Rollback

To rollback the Phase 7 migration:

```sql
DROP TABLE IF EXISTS publisher_review_responses CASCADE;
DROP TABLE IF EXISTS agent_rating_summaries CASCADE;
DROP TABLE IF EXISTS review_votes CASCADE;
DROP TABLE IF EXISTS agent_reviews CASCADE;
DROP TABLE IF EXISTS agent_trending_scores CASCADE;
DROP TABLE IF EXISTS agent_daily_stats CASCADE;
DROP TABLE IF EXISTS agent_usage_events CASCADE;
DROP TABLE IF EXISTS agent_installations CASCADE;
DROP TABLE IF EXISTS marketplace_tags CASCADE;
DROP TABLE IF EXISTS marketplace_categories CASCADE;
DROP TABLE IF EXISTS marketplace_listings CASCADE;
```

### Troubleshooting

**Error: relation "agents" does not exist**
- The Phase 6 `agents` table must exist before running this migration
- Check that Phase 6 is fully deployed

**Error: permission denied**
- Ensure your database user has CREATE TABLE permissions
- Contact your database administrator

**Seed data not inserted**
- Check that the migration completed without errors
- Run the verification script to see what's missing
- Manually insert seed data if needed

### Next Steps

After successful migration:
1. Run verification script
2. Deploy Phase 7 code
3. Enable feature flags gradually
4. Monitor logs for errors

