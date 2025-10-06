# Brikk Infrastructure - Local Development Script (Windows PowerShell)
# LOCAL-ONLY / NOT PROD

param(
    [switch]$Help
)

# Show help if requested
if ($Help) {
    Write-Host "Brikk Infrastructure - Local Development Script" -ForegroundColor Blue
    Write-Host ""
    Write-Host "Usage: .\scripts\dev.ps1" -ForegroundColor Green
    Write-Host ""
    Write-Host "This script sets up the local development environment and starts Flask."
    Write-Host ""
    Write-Host "Prerequisites:" -ForegroundColor Yellow
    Write-Host "  - Python 3.11+ installed and in PATH"
    Write-Host "  - pip installed"
    Write-Host "  - Redis running (via 'make up' or Docker Desktop)"
    Write-Host ""
    Write-Host "Environment Variables Set:" -ForegroundColor Yellow
    Write-Host "  FLASK_APP=src.main:app"
    Write-Host "  FLASK_ENV=development"
    Write-Host "  FLASK_RUN_PORT=8000"
    Write-Host "  REDIS_URL=redis://localhost:6379/0"
    Write-Host "  BRIKK_FEATURE_PER_ORG_KEYS=false"
    Write-Host "  BRIKK_IDEM_ENABLED=true"
    Write-Host "  BRIKK_RLIMIT_ENABLED=false"
    Write-Host ""
    exit 0
}

# Error handling
$ErrorActionPreference = "Stop"

# Banner
Write-Host "🚀 Brikk Infrastructure - Local Development Environment" -ForegroundColor Blue
Write-Host "⚠️  LOCAL-ONLY / NOT PROD" -ForegroundColor Yellow
Write-Host ""

# Check prerequisites
Write-Host "📋 Checking prerequisites..." -ForegroundColor Blue

# Check Python
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Host "✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python 3 not found. Please install Python 3.11+ and add to PATH" -ForegroundColor Red
    exit 1
}

# Check pip
try {
    $pipVersion = pip --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "pip not found"
    }
    Write-Host "✅ pip available" -ForegroundColor Green
} catch {
    Write-Host "❌ pip not found. Please install pip" -ForegroundColor Red
    exit 1
}

# Check Redis connectivity (optional)
Write-Host "🔍 Checking Redis connectivity..." -ForegroundColor Blue
try {
    # Try to connect to Redis (if redis-cli is available)
    $redisCheck = redis-cli -h localhost -p 6379 ping 2>&1
    if ($LASTEXITCODE -eq 0 -and $redisCheck -eq "PONG") {
        Write-Host "✅ Redis responding on localhost:6379" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Redis not responding. Run 'make up' to start Redis container" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  redis-cli not found. Assuming Redis is available via Docker" -ForegroundColor Yellow
}

# Set environment variables for local development
Write-Host "🔧 Setting up local development environment..." -ForegroundColor Blue

# Set environment variables (current session only)
$env:FLASK_APP = "src.main:app"
$env:FLASK_ENV = "development"
$env:FLASK_RUN_PORT = "8000"
$env:FLASK_RUN_HOST = "0.0.0.0"
$env:REDIS_URL = "redis://localhost:6379/0"

# Feature flags for local development
$env:BRIKK_FEATURE_PER_ORG_KEYS = "false"
$env:BRIKK_IDEM_ENABLED = "true"
$env:BRIKK_RLIMIT_ENABLED = "false"
$env:BRIKK_METRICS_ENABLED = "true"
$env:BRIKK_LOG_JSON = "true"
$env:BRIKK_ALLOW_UUID4 = "false"

# Development settings
$env:LOG_LEVEL = "INFO"
$env:FLASK_DEBUG = "1"

Write-Host "✅ Environment variables set for current session" -ForegroundColor Green
Write-Host ""

# Show configuration
Write-Host "📊 Local Development Configuration:" -ForegroundColor Blue
Write-Host "  Flask App:              $env:FLASK_APP"
Write-Host "  Flask Environment:      $env:FLASK_ENV"
Write-Host "  Flask Port:             $env:FLASK_RUN_PORT"
Write-Host "  Redis URL:              $env:REDIS_URL"
Write-Host "  Per-Org Keys:           $env:BRIKK_FEATURE_PER_ORG_KEYS"
Write-Host "  Idempotency:            $env:BRIKK_IDEM_ENABLED"
Write-Host "  Rate Limiting:          $env:BRIKK_RLIMIT_ENABLED"
Write-Host "  Metrics:                $env:BRIKK_METRICS_ENABLED"
Write-Host "  JSON Logging:           $env:BRIKK_LOG_JSON"
Write-Host ""

# Install dependencies if needed
Write-Host "📦 Checking Python dependencies..." -ForegroundColor Blue
if (-not (Test-Path "requirements.txt")) {
    Write-Host "❌ requirements.txt not found" -ForegroundColor Red
    exit 1
}

# Check if key packages are installed
try {
    python -c "import flask" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Flask not installed"
    }
    Write-Host "✅ Dependencies already installed" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Installing Python dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
}

# Start Flask development server
Write-Host "🚀 Starting Flask development server..." -ForegroundColor Blue
Write-Host "📍 Server will be available at: http://localhost:$env:FLASK_RUN_PORT" -ForegroundColor Green
Write-Host "📍 Health check: http://localhost:$env:FLASK_RUN_PORT/healthz" -ForegroundColor Green
Write-Host "📍 Metrics: http://localhost:$env:FLASK_RUN_PORT/metrics" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Run Flask
try {
    python -m flask run --host=$env:FLASK_RUN_HOST --port=$env:FLASK_RUN_PORT --debug
} catch {
    Write-Host "❌ Failed to start Flask server" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
