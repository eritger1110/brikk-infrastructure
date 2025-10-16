-- Phase 7: Marketplace, Analytics, and Reviews
-- Migration script to create all Phase 7 tables
-- Run this after Phase 6 agents table exists

-- =============================================================================
-- MARKETPLACE TABLES
-- =============================================================================

-- Marketplace listings (extends agents from Phase 6)
CREATE TABLE IF NOT EXISTS marketplace_listings (
    id VARCHAR(36) PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    publisher_id VARCHAR(36) NOT NULL,
    
    -- Status and visibility
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    visibility VARCHAR(20) NOT NULL DEFAULT 'public',
    
    -- Featured listing
    featured BOOLEAN DEFAULT FALSE,
    featured_until TIMESTAMP,
    
    -- Organization
    category VARCHAR(100),
    tags TEXT,  -- JSON array
    
    -- Description and media
    short_description TEXT,
    long_description TEXT,
    icon_url TEXT,
    screenshots TEXT,  -- JSON array
    demo_url TEXT,
    documentation_url TEXT,
    source_code_url TEXT,
    
    -- Licensing
    license VARCHAR(50),
    
    -- Pricing
    pricing_model VARCHAR(20) DEFAULT 'free',
    price_amount NUMERIC(10, 2),
    price_currency VARCHAR(3) DEFAULT 'USD',
    
    -- Metrics
    install_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    
    -- Timestamps
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (status IN ('draft', 'published', 'archived')),
    CHECK (visibility IN ('public', 'private', 'unlisted')),
    CHECK (pricing_model IN ('free', 'paid', 'freemium'))
);

CREATE INDEX IF NOT EXISTS idx_marketplace_agent_id ON marketplace_listings(agent_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_publisher_id ON marketplace_listings(publisher_id);
CREATE INDEX IF NOT EXISTS idx_marketplace_status ON marketplace_listings(status);
CREATE INDEX IF NOT EXISTS idx_marketplace_category ON marketplace_listings(category);
CREATE INDEX IF NOT EXISTS idx_marketplace_featured ON marketplace_listings(featured) WHERE featured = TRUE;

-- Agent categories
CREATE TABLE IF NOT EXISTS agent_categories (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50),
    parent_id VARCHAR(36) REFERENCES agent_categories(id),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON agent_categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_slug ON agent_categories(slug);

-- Agent tags
CREATE TABLE IF NOT EXISTS agent_tags (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(50) NOT NULL UNIQUE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tags_slug ON agent_tags(slug);
CREATE INDEX IF NOT EXISTS idx_tags_usage_count ON agent_tags(usage_count DESC);

-- Agent installations
CREATE TABLE IF NOT EXISTS agent_installations (
    id VARCHAR(36) PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL REFERENCES agents(id),
    user_id VARCHAR(36) NOT NULL,
    installed_version VARCHAR(50),
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    uninstalled_at TIMESTAMP,
    
    UNIQUE(agent_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_installations_agent_id ON agent_installations(agent_id);
CREATE INDEX IF NOT EXISTS idx_installations_user_id ON agent_installations(user_id);
CREATE INDEX IF NOT EXISTS idx_installations_active ON agent_installations(agent_id, user_id) WHERE uninstalled_at IS NULL;

-- =============================================================================
-- ANALYTICS TABLES
-- =============================================================================

-- Agent usage events (high-volume table)
CREATE TABLE IF NOT EXISTS agent_usage_events (
    id VARCHAR(36) PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL REFERENCES agents(id),
    user_id VARCHAR(36),
    
    -- Event details
    event_type VARCHAR(50) NOT NULL,
    duration_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    
    -- Flexible metadata
    metadata TEXT,  -- JSON object
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usage_events_agent_id ON agent_usage_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_user_id ON agent_usage_events(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_created_at ON agent_usage_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_events_type ON agent_usage_events(event_type);

-- Agent analytics daily aggregates
CREATE TABLE IF NOT EXISTS agent_analytics_daily (
    id VARCHAR(36) PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL REFERENCES agents(id),
    date DATE NOT NULL,
    
    -- Volume metrics
    invocation_count INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    
    -- Performance metrics
    avg_duration_ms NUMERIC(10, 2),
    p50_duration_ms INTEGER,
    p95_duration_ms INTEGER,
    p99_duration_ms INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(agent_id, date)
);

CREATE INDEX IF NOT EXISTS idx_analytics_daily_agent_id ON agent_analytics_daily(agent_id);
CREATE INDEX IF NOT EXISTS idx_analytics_daily_date ON agent_analytics_daily(date DESC);

-- User analytics daily aggregates
CREATE TABLE IF NOT EXISTS user_analytics_daily (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    date DATE NOT NULL,
    
    -- Activity metrics
    agents_used INTEGER DEFAULT 0,
    total_invocations INTEGER DEFAULT 0,
    active_time_minutes INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_user_analytics_daily_user_id ON user_analytics_daily(user_id);
CREATE INDEX IF NOT EXISTS idx_user_analytics_daily_date ON user_analytics_daily(date DESC);

-- Agent trending scores
CREATE TABLE IF NOT EXISTS agent_trending_scores (
    id VARCHAR(36) PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL UNIQUE REFERENCES agents(id),
    
    -- Trending metrics
    trending_score NUMERIC(10, 4) DEFAULT 0.0,
    velocity NUMERIC(10, 4) DEFAULT 0.0,
    momentum NUMERIC(10, 4) DEFAULT 0.0,
    
    -- Contributing factors
    recent_installs INTEGER DEFAULT 0,
    recent_views INTEGER DEFAULT 0,
    recent_reviews INTEGER DEFAULT 0,
    recent_usage INTEGER DEFAULT 0,
    
    -- Timestamps
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trending_scores_score ON agent_trending_scores(trending_score DESC);
CREATE INDEX IF NOT EXISTS idx_trending_scores_agent_id ON agent_trending_scores(agent_id);

-- =============================================================================
-- REVIEW TABLES
-- =============================================================================

-- Agent reviews and ratings
CREATE TABLE IF NOT EXISTS agent_reviews (
    id VARCHAR(36) PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL REFERENCES agents(id),
    user_id VARCHAR(36) NOT NULL,
    
    -- Rating and review content
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(200),
    review_text TEXT,
    
    -- Verification and helpfulness
    verified_user BOOLEAN DEFAULT FALSE,
    helpful_count INTEGER DEFAULT 0,
    unhelpful_count INTEGER DEFAULT 0,
    
    -- Moderation
    flagged BOOLEAN DEFAULT FALSE,
    flag_reason TEXT,
    
    -- Publisher response
    publisher_response TEXT,
    publisher_response_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(agent_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_agent_id ON agent_reviews(agent_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON agent_reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON agent_reviews(rating);
CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON agent_reviews(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_flagged ON agent_reviews(flagged) WHERE flagged = TRUE;

-- Review helpfulness votes
CREATE TABLE IF NOT EXISTS review_votes (
    id VARCHAR(36) PRIMARY KEY,
    review_id VARCHAR(36) NOT NULL REFERENCES agent_reviews(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL,
    vote VARCHAR(10) NOT NULL CHECK (vote IN ('helpful', 'unhelpful')),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(review_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_review_votes_review_id ON review_votes(review_id);
CREATE INDEX IF NOT EXISTS idx_review_votes_user_id ON review_votes(user_id);

-- Agent rating summary (pre-computed)
CREATE TABLE IF NOT EXISTS agent_rating_summary (
    agent_id VARCHAR(36) PRIMARY KEY REFERENCES agents(id) ON DELETE CASCADE,
    
    -- Aggregate metrics
    total_reviews INTEGER DEFAULT 0,
    average_rating NUMERIC(3, 2) DEFAULT 0.0,
    
    -- Rating distribution
    rating_1_count INTEGER DEFAULT 0,
    rating_2_count INTEGER DEFAULT 0,
    rating_3_count INTEGER DEFAULT 0,
    rating_4_count INTEGER DEFAULT 0,
    rating_5_count INTEGER DEFAULT 0,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rating_summary_avg_rating ON agent_rating_summary(average_rating DESC);
CREATE INDEX IF NOT EXISTS idx_rating_summary_total_reviews ON agent_rating_summary(total_reviews DESC);

-- =============================================================================
-- SEED DATA: Default Categories
-- =============================================================================

INSERT INTO agent_categories (id, name, slug, description, icon, display_order) VALUES
('cat-productivity', 'Productivity', 'productivity', 'Agents that help you get work done faster', 'briefcase', 1),
('cat-communication', 'Communication', 'communication', 'Agents for messaging, email, and collaboration', 'message-circle', 2),
('cat-data', 'Data & Analytics', 'data-analytics', 'Agents for data processing and analysis', 'bar-chart', 3),
('cat-development', 'Development', 'development', 'Agents for software development and DevOps', 'code', 4),
('cat-creative', 'Creative', 'creative', 'Agents for design, content creation, and media', 'palette', 5),
('cat-business', 'Business', 'business', 'Agents for business operations and management', 'trending-up', 6),
('cat-education', 'Education', 'education', 'Agents for learning and training', 'book', 7),
('cat-automation', 'Automation', 'automation', 'Agents for workflow automation and integration', 'zap', 8),
('cat-ai-ml', 'AI & Machine Learning', 'ai-ml', 'Agents powered by AI and ML capabilities', 'cpu', 9),
('cat-utilities', 'Utilities', 'utilities', 'General-purpose utility agents', 'tool', 10)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- SEED DATA: Common Tags
-- =============================================================================

INSERT INTO agent_tags (id, name, slug) VALUES
('tag-popular', 'Popular', 'popular'),
('tag-new', 'New', 'new'),
('tag-trending', 'Trending', 'trending'),
('tag-verified', 'Verified', 'verified'),
('tag-enterprise', 'Enterprise', 'enterprise'),
('tag-free', 'Free', 'free'),
('tag-premium', 'Premium', 'premium'),
('tag-api', 'API', 'api'),
('tag-webhook', 'Webhook', 'webhook'),
('tag-automation', 'Automation', 'automation'),
('tag-integration', 'Integration', 'integration'),
('tag-ai-powered', 'AI-Powered', 'ai-powered'),
('tag-real-time', 'Real-time', 'real-time'),
('tag-batch', 'Batch Processing', 'batch'),
('tag-scheduled', 'Scheduled', 'scheduled')
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

-- Verify tables were created
SELECT 
    'marketplace_listings' as table_name, COUNT(*) as row_count FROM marketplace_listings
UNION ALL
SELECT 'agent_categories', COUNT(*) FROM agent_categories
UNION ALL
SELECT 'agent_tags', COUNT(*) FROM agent_tags
UNION ALL
SELECT 'agent_installations', COUNT(*) FROM agent_installations
UNION ALL
SELECT 'agent_usage_events', COUNT(*) FROM agent_usage_events
UNION ALL
SELECT 'agent_analytics_daily', COUNT(*) FROM agent_analytics_daily
UNION ALL
SELECT 'user_analytics_daily', COUNT(*) FROM user_analytics_daily
UNION ALL
SELECT 'agent_trending_scores', COUNT(*) FROM agent_trending_scores
UNION ALL
SELECT 'agent_reviews', COUNT(*) FROM agent_reviews
UNION ALL
SELECT 'review_votes', COUNT(*) FROM review_votes
UNION ALL
SELECT 'agent_rating_summary', COUNT(*) FROM agent_rating_summary;

