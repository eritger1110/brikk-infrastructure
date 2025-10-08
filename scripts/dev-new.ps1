# Brikk Infrastructure - Windows Development Script (New Command-Based)
# PowerShell wrapper for Makefile targets to provide Windows compatibility
# Usage: .\scripts\dev-new.ps1 <command>
# Commands: venv, install, lint, format, test, run, clean, help

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("venv", "install", "lint", "format", "test", "run", "clean", "help", "check")]
    [string]$Command
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "💡 $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }

# Check if we're in the right directory
if (-not (Test-Path "requirements.txt")) {
    Write-Error "Please run this script from the brikk-infrastructure root directory"
    exit 1
}

# Check Python installation
function Test-Python {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python 3\.1[1-9]") {
            Write-Success "Python found: $pythonVersion"
            return $true
        } else {
            Write-Warning "Python 3.11+ recommended. Found: $pythonVersion"
            return $true
        }
    } catch {
        Write-Error "Python not found. Please install Python 3.11+ and add it to PATH"
        Write-Info "Download from: https://www.python.org/downloads/"
        return $false
    }
}

# Main command execution
switch ($Command) {
    "help" {
        Write-Host ""
        Write-Host "Brikk Infrastructure - Windows Development Commands" -ForegroundColor Yellow
        Write-Host "=================================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Usage: .\scripts\dev-new.ps1 <command>" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  venv     Create Python virtual environment (.venv)"
        Write-Host "  install  Install all dependencies (prod + dev)"
        Write-Host "  lint     Run code linting (flake8)"
        Write-Host "  format   Format code (black, isort)"
        Write-Host "  test     Run tests (pytest)"
        Write-Host "  run      Start development server"
        Write-Host "  clean    Remove virtual environment and cache files"
        Write-Host "  check    Run all checks (lint + test)"
        Write-Host "  help     Show this help message"
        Write-Host ""
        Write-Host "Quick Start:" -ForegroundColor Green
        Write-Host "  .\scripts\dev-new.ps1 venv"
        Write-Host "  .\scripts\dev-new.ps1 install"
        Write-Host "  .\.venv\Scripts\Activate.ps1"
        Write-Host "  .\scripts\dev-new.ps1 test"
        Write-Host "  .\scripts\dev-new.ps1 run"
        Write-Host ""
        Write-Host "Important Notes:" -ForegroundColor Yellow
        Write-Host "  • Clone repository outside OneDrive (e.g., C:\dev\brikk-infrastructure)"
        Write-Host "  • Run PowerShell as Administrator if you encounter permission issues"
        Write-Host "  • Activate virtual environment before running commands (except venv/install)"
        Write-Host ""
        Write-Host "Legacy Script:" -ForegroundColor Cyan
        Write-Host "  Use .\scripts\dev.ps1 for the original Docker-based workflow"
        Write-Host ""
    }

    "venv" {
        Write-Info "Creating Python virtual environment..."
        
        if (-not (Test-Python)) { exit 1 }
        
        if (Test-Path ".venv") {
            Write-Warning "Virtual environment already exists at .venv"
            $response = Read-Host "Do you want to recreate it? (y/N)"
            if ($response -eq "y" -or $response -eq "Y") {
                Remove-Item -Recurse -Force ".venv"
            } else {
                Write-Info "Keeping existing virtual environment"
                exit 0
            }
        }
        
        python -m venv .venv
        Write-Success "Virtual environment created at .venv"
        Write-Info "Activate with: .\.venv\Scripts\Activate.ps1"
        Write-Info "Next step: .\scripts\dev-new.ps1 install"
    }

    "install" {
        Write-Info "Installing all dependencies..."
        
        if (-not (Test-Path ".venv")) {
            Write-Error "Virtual environment not found. Run: .\scripts\dev-new.ps1 venv"
            exit 1
        }
        
        # Activate virtual environment and install dependencies
        & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
        & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
        & ".\.venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
        
        Write-Success "All dependencies installed successfully"
        Write-Info "Activate environment: .\.venv\Scripts\Activate.ps1"
    }

    "lint" {
        Write-Info "Running code linting..."
        
        if (-not (Test-Path ".venv\Scripts\flake8.exe")) {
            Write-Error "flake8 not found. Run: .\scripts\dev-new.ps1 install"
            exit 1
        }
        
        & ".\.venv\Scripts\flake8.exe" src/ --select=E9,F63,F7,F82 --max-line-length=88 --exclude=__pycache__
        Write-Success "Linting completed"
    }

    "format" {
        Write-Info "Formatting code..."
        
        if (-not (Test-Path ".venv\Scripts\black.exe")) {
            Write-Error "black not found. Run: .\scripts\dev-new.ps1 install"
            exit 1
        }
        
        & ".\.venv\Scripts\black.exe" . --exclude="__pycache__|\.git|\.pytest_cache"
        & ".\.venv\Scripts\isort.exe" . --profile black
        Write-Success "Code formatting completed"
    }

    "test" {
        Write-Info "Running tests..."
        
        if (-not (Test-Path ".venv\Scripts\pytest.exe")) {
            Write-Error "pytest not found. Run: .\scripts\dev-new.ps1 install"
            exit 1
        }
        
        & ".\.venv\Scripts\pytest.exe" -q
        Write-Success "Tests completed"
    }

    "run" {
        Write-Info "Starting Flask development server on http://localhost:5000"
        Write-Info "Press Ctrl+C to stop"
        
        if (-not (Test-Path ".venv\Scripts\python.exe")) {
            Write-Error "Virtual environment not found. Run: .\scripts\dev-new.ps1 venv && .\scripts\dev-new.ps1 install"
            exit 1
        }
        
        $env:FLASK_APP = "src.main:create_app"
        $env:FLASK_ENV = "development"
        & ".\.venv\Scripts\python.exe" -m flask run --host=0.0.0.0 --port=5000
    }

    "clean" {
        Write-Info "Cleaning up..."
        
        if (Test-Path ".venv") {
            Remove-Item -Recurse -Force ".venv"
        }
        
        Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | ForEach-Object {
            Remove-Item -Recurse -Force $_
        }
        
        Get-ChildItem -Path . -Recurse -File -Name "*.pyc" | ForEach-Object {
            Remove-Item -Force $_
        }
        
        if (Test-Path ".pytest_cache") {
            Remove-Item -Recurse -Force ".pytest_cache"
        }
        
        Write-Success "Cleanup completed"
    }

    "check" {
        Write-Info "Running all checks..."
        
        # Run lint
        & $PSCommandPath lint
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        
        # Run tests
        & $PSCommandPath test
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        
        Write-Success "All checks passed!"
    }
}
