#!/bin/bash
# Smoke Tests for Phase 7 & 8 Deployment
# Tests all critical endpoints to verify deployment success

# set -e removed - we want to continue even if individual tests fail

API_BASE="${API_BASE:-https://api.getbrikk.com}"
ORG_ID="${ORG_ID:-demo-org-id}"

echo "🔍 Running Smoke Tests for Brikk API"
echo "API Base: $API_BASE"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test function
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="$3"
    
    echo -n "Testing $name... "
    
    response=$(curl -s -w "\n%{http_code}" "$url")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} ($status_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_status, got $status_code)"
        echo "Response: $body"
        ((FAILED++))
        return 1
    fi
}

echo ""
echo "📋 Core API Tests"
echo "----------------------------------------"

# Health check
test_endpoint "Health Check" "$API_BASE/health" "200"

# Agent Registry (Phase 6)
test_endpoint "Agent Registry" "$API_BASE/api/v1/agents" "401"  # Requires auth

echo ""
echo "🏪 Phase 7: Marketplace Tests"
echo "----------------------------------------"

# Marketplace endpoints
test_endpoint "Marketplace Agents" "$API_BASE/api/v1/marketplace/agents" "200"
test_endpoint "Marketplace Categories" "$API_BASE/api/v1/marketplace/categories" "200"
test_endpoint "Marketplace Tags" "$API_BASE/api/v1/marketplace/tags" "200"
test_endpoint "Featured Agents" "$API_BASE/api/v1/marketplace/agents/featured" "200"

# Analytics endpoints
test_endpoint "Analytics Events" "$API_BASE/api/v1/analytics/events" "405"  # POST-only endpoint, GET returns 405
test_endpoint "Trending Agents" "$API_BASE/api/v1/analytics/trending" "200"

# Discovery endpoints
test_endpoint "Agent Search" "$API_BASE/api/v1/agent-discovery/search?q=test" "200"
test_endpoint "Agent Recommendations" "$API_BASE/api/v1/agent-discovery/recommendations" "200"  # Returns trending agents when not authenticated

# Reviews endpoints
test_endpoint "Agent Reviews" "$API_BASE/api/v1/reviews/agent/test-agent-id" "200"

echo ""
echo "👨‍💻 Phase 8: Developer Experience Tests"
echo "----------------------------------------"

# Usage stats endpoints
test_endpoint "Usage Summary" "$API_BASE/api/v1/usage/summary?org_id=$ORG_ID" "200"
test_endpoint "Current Usage" "$API_BASE/api/v1/usage/current?org_id=$ORG_ID" "200"

# API Keys endpoints
test_endpoint "API Keys List" "$API_BASE/api/v1/keys" "401"  # Requires auth

# Static files
test_endpoint "Developer Dashboard" "$API_BASE/static/developer-dashboard.html" "200"
test_endpoint "Usage Dashboard" "$API_BASE/static/usage-dashboard.html" "200"

echo ""
echo "📚 Documentation Tests"
echo "----------------------------------------"

# API docs
test_endpoint "API Docs" "$API_BASE/docs" "200"

echo ""
echo "=========================================="
echo "📊 Test Results"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Total: $((PASSED + FAILED))"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All smoke tests passed!${NC}"
    echo "🚀 Deployment verified successfully!"
    exit 0
else
    echo ""
    echo -e "${RED}✗ Some tests failed!${NC}"
    echo "⚠️  Please investigate failed endpoints"
    exit 1
fi

