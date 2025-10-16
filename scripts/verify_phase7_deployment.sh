#!/bin/bash
# Phase 7 Deployment Verification Script
# Verifies that Phase 7 is deployed correctly

set -e

API_URL="${API_URL:-https://api.getbrikk.com}"
VERBOSE="${VERBOSE:-0}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Phase 7 Deployment Verification"
echo "========================================"
echo "API URL: $API_URL"
echo ""

# Function to test endpoint
test_endpoint() {
    local name=$1
    local endpoint=$2
    local expected_status=$3
    local method=${4:-GET}
    
    if [ "$VERBOSE" = "1" ]; then
        echo "Testing: $name ($method $endpoint)"
    fi
    
    status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$API_URL$endpoint")
    
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}[PASS]${NC} $name (HTTP $status)"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} $name (Expected $expected_status, got $status)"
        return 1
    fi
}

# Function to test JSON response
test_json_field() {
    local name=$1
    local endpoint=$2
    local field=$3
    local expected=$4
    
    response=$(curl -s "$API_URL$endpoint")
    value=$(echo "$response" | jq -r ".$field" 2>/dev/null || echo "null")
    
    if [ "$value" = "$expected" ]; then
        echo -e "${GREEN}[PASS]${NC} $name ($field=$expected)"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} $name ($field: expected '$expected', got '$value')"
        if [ "$VERBOSE" = "1" ]; then
            echo "Response: $response"
        fi
        return 1
    fi
}

passed=0
failed=0

echo "Testing Core API..."
echo "-------------------"

# Test health endpoint
if test_endpoint "Health Check" "/health" "200"; then
    ((passed++))
else
    ((failed++))
fi

echo ""
echo "Testing Phase 7 Endpoints..."
echo "----------------------------"

# Marketplace endpoints
if test_endpoint "Marketplace Listing" "/api/v1/marketplace/agents" "503"; then
    ((passed++))
else
    ((failed++))
fi

if test_json_field "Marketplace Feature Flag" "/api/v1/marketplace/agents" "enabled" "false"; then
    ((passed++))
else
    ((failed++))
fi

if test_endpoint "Marketplace Categories" "/api/v1/marketplace/categories" "503"; then
    ((passed++))
else
    ((failed++))
fi

# Analytics endpoints
if test_endpoint "Analytics Events" "/api/v1/analytics/events" "503" "POST"; then
    ((passed++))
else
    ((failed++))
fi

if test_endpoint "Analytics Trending" "/api/v1/analytics/trending" "503"; then
    ((passed++))
else
    ((failed++))
fi

# Discovery endpoints
if test_endpoint "Agent Search" "/api/v1/agent-discovery/search?q=test" "503"; then
    ((passed++))
else
    ((failed++))
fi

# Reviews endpoints
if test_endpoint "Agent Reviews" "/api/v1/reviews/agents/test-agent" "503"; then
    ((passed++))
else
    ((failed++))
fi

echo ""
echo "========================================"
echo "Verification Summary"
echo "========================================"
echo -e "Passed: ${GREEN}$passed${NC}"
echo -e "Failed: ${RED}$failed${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Phase 7 Status:"
    echo "- All endpoints are deployed"
    echo "- Features are disabled by feature flags (expected)"
    echo "- Error handling is working correctly"
    echo ""
    echo "Next Steps:"
    echo "1. Run database migration: psql \$DATABASE_URL -f migrations/phase_7_marketplace_analytics.sql"
    echo "2. Enable features via feature flags"
    echo "3. Test with real data"
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo ""
    echo "Please review the failures above and:"
    echo "1. Check deployment logs"
    echo "2. Verify all Phase 7 routes are registered"
    echo "3. Ensure error handlers are configured"
    exit 1
fi

