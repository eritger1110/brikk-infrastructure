-- Migration: 003_create_usage_events
-- Description: Create usage_events table for cost tracking and billing
-- Date: 2025-10-26

CREATE TABLE IF NOT EXISTS usage_events (
  id SERIAL PRIMARY KEY,
  request_id UUID NOT NULL,
  api_key_id INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  provider VARCHAR(50) NOT NULL,
  model VARCHAR(100) NOT NULL,
  prompt_tokens INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  cost_usd NUMERIC(12,6) NOT NULL DEFAULT 0,
  latency_ms INTEGER NOT NULL DEFAULT 0,
  fallback BOOLEAN NOT NULL DEFAULT FALSE,
  error_message VARCHAR(500),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_usage_request_id ON usage_events(request_id);
CREATE INDEX IF NOT EXISTS idx_usage_api_key_id ON usage_events(api_key_id);
CREATE INDEX IF NOT EXISTS idx_usage_provider ON usage_events(provider);
CREATE INDEX IF NOT EXISTS idx_usage_created_at ON usage_events(created_at);
CREATE INDEX IF NOT EXISTS idx_usage_key_created ON usage_events(api_key_id, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_provider_created ON usage_events(provider, created_at);

