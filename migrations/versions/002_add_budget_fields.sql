-- Migration: 002_add_budget_fields
-- Description: Add soft_cap_usd and hard_cap_usd to api_keys table
-- Date: 2025-10-26

-- Add budget cap columns to existing api_keys table
ALTER TABLE api_keys 
ADD COLUMN IF NOT EXISTS soft_cap_usd NUMERIC(10,4) DEFAULT 5.00,
ADD COLUMN IF NOT EXISTS hard_cap_usd NUMERIC(10,4) DEFAULT 10.00;

-- Update existing keys to have default budget caps
UPDATE api_keys 
SET soft_cap_usd = 5.00, hard_cap_usd = 10.00 
WHERE soft_cap_usd IS NULL OR hard_cap_usd IS NULL;

