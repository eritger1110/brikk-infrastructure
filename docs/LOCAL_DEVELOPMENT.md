# Local Development Environment

This document describes how to set up and use the local development environment for Brikk Infrastructure.

## 🚀 Quick Start

1. **Start Redis container:**
   ```bash
   make up
   ```

2. **Start Flask application:**
   ```bash
   # Unix/Linux/macOS
   ./scripts/dev.sh
   
   # Windows PowerShell
   .\scripts\dev.ps1
   ```

3. **Run smoke tests:**
   ```bash
   make test
   ```

4. **Access the application:**
   - Health check: http://localhost:8000/healthz
   - Metrics: http://localhost:8000/metrics
   - Coordination API: http://localhost:8000/api/v1/coordination

## 📋 Prerequisites

- **Docker & Docker Compose** - For Redis container
- **Python 3.11+** - For Flask application
- **pip** - For Python package management
- **make** - For development commands (optional but recommended)

## 🔧 Available Commands

### Make Targets

```bash
make help        # Show all available commands
make up          # Start Redis container
make down        # Stop Redis container and remove volumes
make logs        # Show Redis container logs
make test        # Run smoke tests (LOCAL-ONLY, not wired to CI)
make status      # Show development environment status
make clean       # Clean up containers and artifacts
make install     # Install Python dependencies
make dev-setup   # Complete development setup
```

### Development Scripts

#### Unix/Linux/macOS
```bash
./scripts/dev.sh
```

#### Windows PowerShell
```powershell
.\scripts\dev.ps1
```

Both scripts:
- Check prerequisites (Python, pip, Redis)
- Set environment variables for local development
- Install dependencies if needed
- Start Flask development server on http://localhost:8000

## 🏗️ Architecture

### Local Environment Components

1. **Redis Container** (`brikk-redis`)
   - Port: 6379
   - Used for: Rate limiting, idempotency, caching
   - Health checks enabled
   - Data persistence with volumes

2. **Flask Application**
   - Port: 8000
   - Debug mode enabled
   - Auto-reload on code changes
   - Comprehensive logging

3. **Smoke Tests** (`tests/smoke/`)
   - Local development validation
   - NOT wired to CI
   - Run via `make test`

### Feature Flags (Local Development)

| Flag | Default | Description |
|------|---------|-------------|
| `BRIKK_FEATURE_PER_ORG_KEYS` | `false` | Per-organization API keys |
| `BRIKK_IDEM_ENABLED` | `true` | Request idempotency |
| `BRIKK_RLIMIT_ENABLED` | `false` | Rate limiting |
| `BRIKK_METRICS_ENABLED` | `true` | Prometheus metrics |
| `BRIKK_LOG_JSON` | `true` | Structured JSON logging |
| `BRIKK_ALLOW_UUID4` | `false` | Allow UUID4 (strict UUIDv7) |

## 🧪 Testing

### Smoke Tests

Smoke tests are designed for local development validation and are **NOT wired to CI**.

```bash
# Run all smoke tests
make test

# Run specific test file
pytest tests/smoke/test_app_startup.py -v

# Run with more verbose output
pytest tests/smoke/ -v -s
```

### Test Categories

1. **App Startup Tests** (`test_app_startup.py`)
   - Flask application health
   - Endpoint availability
   - Request ID propagation
   - Metrics endpoint functionality

2. **Coordination API Tests** (`test_coordination_api.py`)
   - Request validation
   - Authentication behavior
   - Rate limiting (when enabled)
   - Idempotency (when enabled)
   - Error handling

### Test Requirements

- Flask app running on localhost:8000
- Redis container running (via `make up`)
- All tests gracefully skip if dependencies unavailable

## 🔍 Troubleshooting

### Common Issues

#### Redis Connection Failed
```bash
# Check if Redis container is running
docker ps --filter "name=brikk-redis"

# Start Redis if not running
make up

# Check Redis logs
make logs
```

#### Flask App Won't Start
```bash
# Check Python version
python3 --version  # Should be 3.11+

# Install dependencies
make install

# Check for port conflicts
lsof -i :8000  # Unix/Linux/macOS
netstat -an | findstr :8000  # Windows
```

#### Dependencies Missing
```bash
# Install all dependencies
pip install -r requirements.txt

# Or use make command
make install
```

#### Permission Denied (Unix/Linux/macOS)
```bash
# Make script executable
chmod +x scripts/dev.sh
```

### Environment Variables

The development scripts set these environment variables automatically:

```bash
FLASK_APP=src.main:app
FLASK_ENV=development
FLASK_RUN_PORT=8000
FLASK_RUN_HOST=0.0.0.0
REDIS_URL=redis://localhost:6379/0
BRIKK_FEATURE_PER_ORG_KEYS=false
BRIKK_IDEM_ENABLED=true
BRIKK_RLIMIT_ENABLED=false
BRIKK_METRICS_ENABLED=true
BRIKK_LOG_JSON=true
BRIKK_ALLOW_UUID4=false
LOG_LEVEL=INFO
FLASK_DEBUG=1
```

### Logs and Debugging

#### Flask Application Logs
- Structured JSON logs when `BRIKK_LOG_JSON=true`
- Request IDs for correlation
- Performance and security event logging

#### Redis Container Logs
```bash
make logs
```

#### Application Health Checks
```bash
# Basic health
curl http://localhost:8000/healthz

# Readiness (includes dependency checks)
curl http://localhost:8000/readyz

# Metrics (if enabled)
curl http://localhost:8000/metrics
```

## 🔒 Security Notes

### Local Development Only

- **Scripts are LOCAL-ONLY** and clearly marked as NOT PROD
- Environment variables are set for current shell session only
- No global system changes made
- Feature flags default to safe values

### Production Differences

| Aspect | Local Development | Production |
|--------|------------------|------------|
| Authentication | Disabled by default | Enabled |
| Rate Limiting | Disabled | Enabled |
| Logging | JSON + Debug | JSON only |
| Database | SQLite | PostgreSQL |
| Redis | Local container | Managed service |

## 📁 File Structure

```
brikk-infrastructure/
├── docker-compose.local.yml    # Local Redis container
├── Makefile                    # Development commands
├── scripts/
│   ├── dev.sh                 # Unix/Linux/macOS development script
│   └── dev.ps1                # Windows PowerShell development script
├── tests/smoke/               # Local smoke tests (NOT in CI)
│   ├── test_app_startup.py    # Flask app validation
│   └── test_coordination_api.py # API functionality tests
├── docs/
│   └── LOCAL_DEVELOPMENT.md   # This file
└── .env.example               # Environment configuration template
```

## 🚫 What This PR Does NOT Change

- **No runtime code changes** under `src/`
- **No CI/CD modifications** - GitHub Actions unchanged
- **No production behavior changes** - feature flags control everything
- **No global system modifications** - all changes are local and isolated

## 🎯 Goals Achieved

- ✅ **Easy local development setup** with single command
- ✅ **Isolated environment** with Docker Compose
- ✅ **Comprehensive testing** with smoke tests
- ✅ **Clear documentation** and troubleshooting guides
- ✅ **Cross-platform support** (Unix/Linux/macOS/Windows)
- ✅ **Zero production impact** - completely isolated
- ✅ **Developer-friendly** with helpful scripts and commands
