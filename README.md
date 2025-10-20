# Brikk Infrastructure

The backend infrastructure for Brikk's Universal Coordination Protocol for AI Agents.

## Quick Start for Development

### Prerequisites

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/downloads))

### Setup (Linux/macOS)

```bash
# Clone the repository
git clone https://github.com/eritger1110/brikk-infrastructure.git
cd brikk-infrastructure

# Create virtual environment and install dependencies
make venv && make install-dev

# Activate virtual environment
source .venv/bin/activate

# Run tests to verify setup
make test

# Start development server
make dev-run
```

### Setup (Windows)

**Important**: Clone the repository outside OneDrive (e.g., `C:\dev\brikk-infrastructure`) to avoid file sync issues.

```powershell
# Clone the repository
git clone https://github.com/eritger1110/brikk-infrastructure.git
cd brikk-infrastructure

# Create virtual environment and install dependencies
.\scripts\dev-new.ps1 venv
.\scripts\dev-new.ps1 install

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run tests to verify setup
.\scripts\dev-new.ps1 test

# Start development server
.\scripts\dev-new.ps1 run
```

## Development Commands

### Linux/macOS (Makefile)

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make venv` | Create Python virtual environment |
| `make install-dev` | Install all dependencies (prod + dev) |
| `make lint` | Run code linting (flake8) |
| `make format` | Format code (black, isort) |
| `make test` | Run tests (pytest) |
| `make dev-run` | Start Flask development server |
| `make clean` | Remove virtual environment and cache files |
| `make check` | Run all checks (lint + test) |

### Windows (PowerShell)

| Command | Description |
|---------|-------------|
| `.\scripts\dev-new.ps1 help` | Show all available commands |
| `.\scripts\dev-new.ps1 venv` | Create Python virtual environment |
| `.\scripts\dev-new.ps1 install` | Install all dependencies (prod + dev) |
| `.\scripts\dev-new.ps1 lint` | Run code linting (flake8) |
| `.\scripts\dev-new.ps1 format` | Format code (black, isort) |
| `.\scripts\dev-new.ps1 test` | Run tests (pytest) |
| `.\scripts\dev-new.ps1 run` | Start Flask development server |
| `.\scripts\dev-new.ps1 clean` | Remove virtual environment and cache files |
| `.\scripts\dev-new.ps1 check` | Run all checks (lint + test) |

## Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and test locally:
   ```bash
   make test        # Run tests
   make lint        # Check code quality
   make format      # Format code
   ```

3. **Commit and push**:
   ```bash
   git add .
   git commit -m "feat: your feature description"
   git push -u origin feature/your-feature-name
   ```

4. **Create a Pull Request** on GitHub

## Project Structure

```
brikk-infrastructure/
├── src/                    # Application source code
│   ├── main.py            # Flask application factory
│   ├── models/            # Database models
│   ├── routes/            # API route handlers
│   ├── services/          # Business logic services
│   └── schemas/           # Data validation schemas
├── tests/                 # Test files
│   ├── test_smoke.py      # Basic health tests
│   └── ...               # Feature-specific tests
├── docs/                  # Documentation
│   └── compliance/        # HIPAA/SOC 2 compliance docs
├── scripts/               # Development scripts
│   ├── dev.ps1           # Legacy Windows script
│   └── dev-new.ps1       # New command-based Windows script
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
└── Makefile              # Development commands (Linux/macOS)
```

## API Endpoints

The development server runs on `http://localhost:5000` with the following key endpoints:

- `GET /api/inbound/_ping` - Health check endpoint
- `POST /api/coordination/*` - Agent coordination endpoints
- `POST /api/billing/*` - Billing and subscription endpoints

## Environment Variables

For local development, the following environment variables are automatically set:

- `FLASK_APP=src.main:create_app`
- `FLASK_ENV=development`
- `FLASK_DEBUG=1`

## Testing

The project uses pytest for testing:

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_smoke.py -v

# Run tests with coverage
pytest --cov=src tests/
```

## Code Quality

We use several tools to maintain code quality:

- **flake8**: Linting for syntax errors and style issues
- **black**: Code formatting
- **isort**: Import sorting
- **pytest**: Testing framework

## Continuous Integration

GitHub Actions automatically runs tests and linting on every pull request. See `.github/workflows/ci.yaml` for details.

## Legacy Docker Workflow

For the legacy Docker-based development workflow, see:

- **Linux/macOS**: Use existing Makefile targets (`make up`, `make down`, etc.)
- **Windows**: Use `.\scripts\dev.ps1` (original script)

## Contributing

1. Read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines
2. Follow the development workflow above
3. Ensure all tests pass and code is properly formatted
4. Submit a pull request with a clear description

## Security

For security-related documentation and compliance information, see:

- [SECURITY.md](SECURITY.md) - Security policy and vulnerability reporting
- [docs/compliance/](docs/compliance/) - HIPAA/SOC 2 compliance documentation

## Support

For questions or issues:

1. Check existing [GitHub Issues](https://github.com/eritger1110/brikk-infrastructure/issues)
2. Create a new issue with detailed information
3. Follow the templates provided

## License

This project is proprietary software. All rights reserved.

## Beta Submit E2E

This section documents the end-to-end flow for submitting a beta application and how to test it.

### API Endpoint

- **URL:** `https://brikk-infrastructure.onrender.com/api/v1/beta/apply`
- **Method:** `POST`
- **Content-Type:** `application/json`

### cURL Examples

#### 1. Successful Submission (New Application)

```bash
curl -i -X POST https://brikk-infrastructure.onrender.com/api/v1/beta/apply \
-H 'Content-Type: application/json' \
-d '{"name":"Test User","email":"test@example.com","company":"TestCo","use_case":"Trying Brikk"}'
```

**Expected Response (201 Created):**

```json
{
  "code": "application_received",
  "message": "Thanks! Your application is in the queue.",
  "application_id": "<application-id>",
  "queue_position": <integer>
}
```

#### 2. Duplicate Submission (Idempotent)

Run the same command again with the same email address.

**Expected Response (200 OK):**

```json
{
  "code": "application_exists",
  "message": "We already have your application.",
  "application_id": "<existing-application-id>",
  "queue_position": <integer>
}
```

#### 3. Validation Error

```bash
curl -i -X POST https://brikk-infrastructure.onrender.com/api/v1/beta/apply \
-H 'Content-Type: application/json' \
-d '{"name":"","email":"invalid-email","use_case":""}'
```

**Expected Response (422 Unprocessable Entity):**

```json
{
  "code": "validation_error",
  "message": "Please correct the highlighted fields.",
  "errors": {
    "name": "Name is required",
    "email": "Invalid email address",
    "use_case": "Use case is required"
  }
}
```

### Troubleshooting

- **CORS Errors:** If you see CORS errors in the browser console, ensure that the origin you are testing from is included in the `CORS_ORIGINS` list in `src/factory.py`.
- **503 Service Unavailable (Email Health Check):** If the `/health/email` endpoint returns a 503 error, verify that the `SENDGRID_API_KEY` and `EMAIL_FROM` environment variables are correctly set in your production environment.
- **429 Too Many Requests:** The rate limit is set to 60 requests per minute per IP address for testing. If you exceed this, you will receive a 429 error. Wait a minute and try again.

