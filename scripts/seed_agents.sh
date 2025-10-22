#!/bin/bash

# Seed Agents Deployment Script
# Deploys the three seed agents to the Brikk marketplace

set -e  # Exit on error

# Configuration
API_BASE="${API_BASE:-https://brikk-infrastructure.onrender.com}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

if [ -z "$ADMIN_TOKEN" ]; then
    echo "Error: ADMIN_TOKEN environment variable is required"
    echo "Usage: ADMIN_TOKEN=your_token ./seed_agents.sh"
    exit 1
fi

echo "🚀 Deploying seed agents to $API_BASE"
echo ""

# Agent 1: CSV Analyzer
echo "📊 Creating CSV Analyzer..."
curl -X POST "$API_BASE/api/v1/marketplace/agents" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CSV Analyzer",
    "description": "Analyze CSV files and extract insights, trends, and patterns",
    "category": "data-analysis",
    "tags": ["csv", "data", "analytics", "insights"],
    "pricing": {
      "model": "free",
      "price": 0
    },
    "capabilities": ["file-analysis", "data-extraction", "trend-detection"],
    "endpoint_url": "https://api.getbrikk.com/agents/csv-analyzer",
    "documentation_url": "https://docs.getbrikk.com/agents/csv-analyzer",
    "featured": true,
    "verified": true
  }' \
  --silent --show-error | jq '.'

echo ""

# Agent 2: Email Summarizer
echo "📧 Creating Email Summarizer..."
curl -X POST "$API_BASE/api/v1/marketplace/agents" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Email Summarizer",
    "description": "Summarize email threads and extract action items automatically",
    "category": "productivity",
    "tags": ["email", "summarization", "productivity", "nlp"],
    "pricing": {
      "model": "free",
      "price": 0
    },
    "capabilities": ["text-summarization", "action-extraction", "sentiment-analysis"],
    "endpoint_url": "https://api.getbrikk.com/agents/email-summarizer",
    "documentation_url": "https://docs.getbrikk.com/agents/email-summarizer",
    "featured": true,
    "verified": true
  }' \
  --silent --show-error | jq '.'

echo ""

# Agent 3: Code Reviewer
echo "💻 Creating Code Reviewer..."
curl -X POST "$API_BASE/api/v1/marketplace/agents" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "X-User-ID: admin" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Code Reviewer",
    "description": "Review code and provide improvement suggestions, bug detection, and best practices",
    "category": "development",
    "tags": ["code-review", "static-analysis", "best-practices", "quality"],
    "pricing": {
      "model": "free",
      "price": 0
    },
    "capabilities": ["code-analysis", "bug-detection", "style-checking"],
    "endpoint_url": "https://api.getbrikk.com/agents/code-reviewer",
    "documentation_url": "https://docs.getbrikk.com/agents/code-reviewer",
    "featured": true,
    "verified": true
  }' \
  --silent --show-error | jq '.'

echo ""
echo "✅ All seed agents deployed successfully!"
echo ""
echo "Verify with:"
echo "  curl $API_BASE/api/v1/marketplace/featured"

