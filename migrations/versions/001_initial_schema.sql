-- Migration: 001_initial_schema
-- Description: Create api_keys, usage_events, and audit_logs tables
-- Date: 2025-10-26

-- 1) API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
  id BIGSERIAL PRIMARY KEY,
  owner_email TEXT NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,          -- store hash, never plaintext
  label TEXT,
  plan TEXT NOT NULL DEFAULT 'free',      -- free | pro | enterprise
  status TEXT NOT NULL DEFAULT 'active',  -- active | disabled
  soft_cap_usd NUMERIC(10,4) DEFAULT 5.00,
  hard_cap_usd NUMERIC(10,4) DEFAULT 10.00,
  rate_limit_per_min INT DEFAULT 60,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  rotated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_owner ON api_keys(owner_email);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);

-- 2) Usage Events table
CREATE TABLE IF NOT EXISTS usage_events (
  id BIGSERIAL PRIMARY KEY,
  request_id UUID NOT NULL,
  key_id BIGINT NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,                 -- openai | mistral
  model TEXT NOT NULL,
  prompt_tokens INT NOT NULL DEFAULT 0,
  completion_tokens INT NOT NULL DEFAULT 0,
  cost_usd NUMERIC(12,6) NOT NULL DEFAULT 0,
  latency_ms INT NOT NULL DEFAULT 0,
  fallback BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usage_key_created ON usage_events(key_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_request ON usage_events(request_id);
CREATE INDEX IF NOT EXISTS idx_usage_provider ON usage_events(provider);

-- 3) Audit Logs table
CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  request_id UUID NOT NULL,
  key_id BIGINT REFERENCES api_keys(id) ON DELETE SET NULL,
  path TEXT NOT NULL,
  method TEXT NOT NULL,
  status_code INT NOT NULL,
  ip TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_key ON audit_logs(key_id);
CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_logs(status_code);

-- Insert a test API key for development (key: test_brikk_dev_key_123)
-- Hash of "test_brikk_dev_key_123" using SHA256
INSERT INTO api_keys (owner_email, key_hash, label, plan, soft_cap_usd, hard_cap_usd, rate_limit_per_min)
VALUES (
  'dev@getbrikk.com',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',  -- SHA256 hash placeholder
  'Development Test Key',
  'pro',
  100.00,
  200.00,
  1000
)
ON CONFLICT (key_hash) DO NOTHING;

