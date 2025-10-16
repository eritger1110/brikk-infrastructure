# Docker Quick Start

## TL;DR

```bash
# Build and start everything
make docker-build
make docker-up

# View logs
make docker-logs

# Run migrations
make docker-migrate

# Access services
curl http://localhost:5000/health  # API
make docker-db-shell              # PostgreSQL
make docker-redis-shell           # Redis

# Stop everything
make docker-down
```

## What Gets Started

When you run `make docker-up`, three services start:

1. **PostgreSQL** (port 5432) - Database
1. **Redis** (port 6379) - Cache
1. **Flask API** (port 5000) - Web application

## Common Commands

| Command | Description |
|---------|-------------|
| `make docker-up` | Start all services |
| `make docker-down` | Stop all services |
| `make docker-logs` | View all logs |
| `make docker-logs-api` | View API logs only |
| `make docker-build` | Rebuild images |
| `make docker-test` | Run tests |
| `make docker-migrate` | Run DB migrations |
| `make docker-shell` | Open shell in API container |
| `make docker-clean` | Remove everything |
| `make docker-status` | Show service status |

## Files

- `docker-compose.yml` - Main configuration
- `docker-compose.override.yml` - Local customizations (gitignored)
- `docker-compose.test.yml` - Test environment
- `Dockerfile` - API container definition
- `.dockerignore` - Files to exclude from builds

## Full Documentation

See [docker-setup.md](./docker-setup.md) for complete documentation.

## Troubleshooting

**Port conflicts?** Change ports in `docker-compose.override.yml`

**Permission errors?** Ensure files are readable: `chmod -R 755 src/`

**Database issues?** Reset: `make docker-clean && make docker-up`

**Still stuck?** Check logs: `make docker-logs`

