.PHONY: help up down logs test clean

# Default target
help: ## Show this help message
	@echo "Brikk Infrastructure - Local Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Docker and Docker Compose installed"
	@echo "  - Python 3.11+ with pip"
	@echo "  - Redis running (via 'make up')"
	@echo ""
	@echo "Quick Start:"
	@echo "  1. make up          # Start Redis container"
	@echo "  2. ./scripts/dev.sh # Start Flask app (Unix/Linux/macOS)"
	@echo "  3. make test        # Run smoke tests"
	@echo ""

up: ## Start local development environment (Redis)
	@echo "🚀 Starting local development environment..."
	docker compose -f docker-compose.local.yml up -d
	@echo "✅ Redis container started on localhost:6379"
	@echo "💡 Next: Run './scripts/dev.sh' to start Flask app"

down: ## Stop local development environment
	@echo "🛑 Stopping local development environment..."
	docker compose -f docker-compose.local.yml down -v
	@echo "✅ Local environment stopped and volumes removed"

logs: ## Show logs from local development environment
	@echo "📋 Showing logs from local development environment..."
	docker compose -f docker-compose.local.yml logs -f

test: ## Run local smoke tests only (NOT wired to CI)
	@echo "🧪 Running local smoke tests..."
	@echo "⚠️  These tests are LOCAL-ONLY and NOT wired to CI"
	@echo ""
	pytest -q tests/smoke/
	@echo ""
	@echo "✅ Smoke tests completed"

clean: ## Clean up development environment and artifacts
	@echo "🧹 Cleaning up development environment..."
	docker compose -f docker-compose.local.yml down -v --remove-orphans
	docker system prune -f --volumes
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Development environment cleaned"

status: ## Show status of local development environment
	@echo "📊 Local Development Environment Status"
	@echo ""
	@echo "Docker Containers:"
	@docker ps --filter "name=brikk-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "  No containers running"
	@echo ""
	@echo "Redis Connectivity:"
	@docker exec brikk-redis redis-cli ping 2>/dev/null && echo "  ✅ Redis responding" || echo "  ❌ Redis not responding"
	@echo ""
	@echo "Flask App:"
	@curl -s http://localhost:8000/healthz >/dev/null 2>&1 && echo "  ✅ Flask app responding on :8000" || echo "  ❌ Flask app not responding on :8000"

install: ## Install Python dependencies for local development
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt
	pip install pytest requests  # Additional dev dependencies
	@echo "✅ Dependencies installed"

dev-setup: install up ## Complete development setup (install deps + start environment)
	@echo "🎯 Development environment setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run './scripts/dev.sh' to start Flask app"
	@echo "  2. Visit http://localhost:8000/healthz to verify"
	@echo "  3. Run 'make test' to run smoke tests"

# Internal targets (not shown in help)
_check-docker:
	@docker --version >/dev/null 2>&1 || (echo "❌ Docker not found. Please install Docker." && exit 1)
	@docker compose version >/dev/null 2>&1 || (echo "❌ Docker Compose not found. Please install Docker Compose." && exit 1)

_check-python:
	@python3 --version >/dev/null 2>&1 || (echo "❌ Python 3 not found. Please install Python 3.11+." && exit 1)
	@pip --version >/dev/null 2>&1 || (echo "❌ pip not found. Please install pip." && exit 1)
