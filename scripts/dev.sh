#!/bin/bash

# Brikk Infrastructure - Local Development Script (Unix/Linux/macOS)
# LOCAL-ONLY / NOT PROD

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}🚀 Brikk Infrastructure - Local Development Environment${NC}"
echo -e "${YELLOW}⚠️  LOCAL-ONLY / NOT PROD${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}📋 Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python ${PYTHON_VERSION}${NC}"

# Check pip
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip not found. Please install pip${NC}"
    exit 1
fi

echo -e "${GREEN}✅ pip available${NC}"

# Check if Redis is running
echo -e "${BLUE}🔍 Checking Redis connectivity...${NC}"
if command -v redis-cli &> /dev/null; then
    if redis-cli -h localhost -p 6379 ping &> /dev/null; then
        echo -e "${GREEN}✅ Redis responding on localhost:6379${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis not responding. Run 'make up' to start Redis container${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  redis-cli not found. Assuming Redis is available via Docker${NC}"
fi

# Set environment variables for local development
echo -e "${BLUE}🔧 Setting up local development environment...${NC}"

# Export environment variables (current shell only)
export FLASK_APP="src.main:app"
export FLASK_ENV="development"
export FLASK_RUN_PORT="8000"
export FLASK_RUN_HOST="0.0.0.0"
export REDIS_URL="redis://localhost:6379/0"

# Feature flags for local development
export BRIKK_FEATURE_PER_ORG_KEYS="false"
export BRIKK_IDEM_ENABLED="true"
export BRIKK_RLIMIT_ENABLED="false"
export BRIKK_METRICS_ENABLED="true"
export BRIKK_LOG_JSON="true"
export BRIKK_ALLOW_UUID4="false"

# Development settings
export LOG_LEVEL="INFO"
export FLASK_DEBUG="1"

echo -e "${GREEN}✅ Environment variables set for current shell${NC}"
echo ""

# Show configuration
echo -e "${BLUE}📊 Local Development Configuration:${NC}"
echo -e "  Flask App:              ${FLASK_APP}"
echo -e "  Flask Environment:      ${FLASK_ENV}"
echo -e "  Flask Port:             ${FLASK_RUN_PORT}"
echo -e "  Redis URL:              ${REDIS_URL}"
echo -e "  Per-Org Keys:           ${BRIKK_FEATURE_PER_ORG_KEYS}"
echo -e "  Idempotency:            ${BRIKK_IDEM_ENABLED}"
echo -e "  Rate Limiting:          ${BRIKK_RLIMIT_ENABLED}"
echo -e "  Metrics:                ${BRIKK_METRICS_ENABLED}"
echo -e "  JSON Logging:           ${BRIKK_LOG_JSON}"
echo ""

# Install dependencies if needed
echo -e "${BLUE}📦 Checking Python dependencies...${NC}"
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt not found${NC}"
    exit 1
fi

# Check if key packages are installed
if ! python3 -c "import flask" &> /dev/null; then
    echo -e "${YELLOW}⚠️  Installing Python dependencies...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Dependencies already installed${NC}"
fi

# Start Flask development server
echo -e "${BLUE}🚀 Starting Flask development server...${NC}"
echo -e "${GREEN}📍 Server will be available at: http://localhost:${FLASK_RUN_PORT}${NC}"
echo -e "${GREEN}📍 Health check: http://localhost:${FLASK_RUN_PORT}/healthz${NC}"
echo -e "${GREEN}📍 Metrics: http://localhost:${FLASK_RUN_PORT}/metrics${NC}"
echo ""
echo -e "${YELLOW}💡 Press Ctrl+C to stop the server${NC}"
echo ""

# Run Flask
exec python3 -m flask run --host="${FLASK_RUN_HOST}" --port="${FLASK_RUN_PORT}" --debug
