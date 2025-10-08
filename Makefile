.PHONY: help up down logs test clean venv install install-dev lint format run check-python dev-run

# Default target
help: ## Show this help message
	@echo "Brikk Infrastructure - Local Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development Setup (New):"
	@echo "  venv         Create Python virtual environment (.venv)"
	@echo "  install-dev  Install all dependencies (prod + dev)"
	@echo "  lint         Run code linting (flake8)"
	@echo "  format       Format code (black, isort)"
	@echo "  dev-run      Start Flask development server"
	@echo ""
	@echo "Docker Environment (Legacy):"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick Start (New Python Workflow):"
	@echo "  1. make venv && make install-dev"
	@echo "  2. source .venv/bin/activate"
	@echo "  3. make dev-run"
	@echo ""
	@echo "Quick Start (Legacy Docker Workflow):"
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


# New Development Setup Targets
# =============================

# Check if Python 3.11 is available
check-python:
	@python3.11 --version >/dev/null 2>&1 || python3 --version >/dev/null 2>&1 || (echo "❌ Python 3.11+ is required but not found. Please install Python 3.11+." && exit 1)

# Create virtual environment
venv: check-python
	@echo "📦 Creating Python virtual environment..."
	python3.11 -m venv .venv 2>/dev/null || python3 -m venv .venv
	@echo "✅ Virtual environment created at .venv"
	@echo "💡 Activate with: source .venv/bin/activate (Linux/Mac) or .venv\\Scripts\\activate (Windows)"

# Install all dependencies (production + development)
install-dev: check-python
	@echo "📦 Installing all dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	@echo "✅ All dependencies installed successfully"

# Run linting
lint:
	@echo "🔍 Running code linting..."
	flake8 src/ --select=E9,F63,F7,F82 --max-line-length=88 --exclude=__pycache__
	@echo "✅ Linting completed"

# Format code
format:
	@echo "🎨 Formatting code..."
	black . --exclude="__pycache__|\.git|\.pytest_cache"
	isort . --profile black
	@echo "✅ Code formatting completed"

# Run development server (new Python workflow)
dev-run:
	@echo "🚀 Starting Flask development server on http://localhost:5000"
	@echo "💡 Press Ctrl+C to stop"
	FLASK_APP=src.main:create_app FLASK_ENV=development python -m flask run --host=0.0.0.0 --port=5000

# Run all checks
check: lint test
	@echo "✅ All checks passed!"

# Complete development setup from scratch
dev-setup-new: venv install-dev
	@echo ""
	@echo "🎯 New development setup completed!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Activate virtual environment: source .venv/bin/activate"
	@echo "2. Run tests: make test"
	@echo "3. Start development server: make dev-run"
