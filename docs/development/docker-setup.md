# Docker Setup Guide

## Overview

This project uses Docker Compose to provide a consistent development environment
with all required services (PostgreSQL, Redis, Flask API).

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

Install Docker Desktop (includes both):

- **macOS**: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Windows**: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- **Linux**: [Docker Engine](https://docs.docker.com/engine/install/)

## Quick Start

### 1. Start all services

```bash
docker-compose up
```

This will start:

- PostgreSQL database on port 5432
- Redis cache on port 6379
- Flask API on port 5000

### 2. Access the API

```bash
curl http://localhost:5000/health
```

### 3. View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
```

### 4. Stop services

```bash
# Stop and keep containers
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (clean slate)
docker-compose down -v
```

## Docker Compose Files

### docker-compose.yml

Main configuration file with all services. This is the base configuration
used for development.

### docker-compose.override.yml

Local development overrides (gitignored). Copy the example to customize:

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

This file is automatically loaded by docker-compose and allows you to:

- Change environment variables
- Mount additional volumes
- Override service configurations
- Add custom services

### docker-compose.test.yml

Test environment configuration. Use this to run tests in Docker:

```bash
docker-compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit
```

### docker-compose.local.yml (Legacy)

Original Redis-only configuration. Kept for backward compatibility.

## Common Tasks

### Database Migrations

Run migrations in the API container:

```bash
docker-compose exec api alembic upgrade head
```

Create a new migration:

```bash
docker-compose exec api alembic revision --autogenerate -m "Description"
```

### Access Database

Connect to PostgreSQL:

```bash
docker-compose exec postgres psql -U brikk -d brikk_dev
```

### Access Redis

Connect to Redis CLI:

```bash
docker-compose exec redis redis-cli
```

### Run Tests

```bash
# Run all tests
docker-compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit

# Run specific test file
docker-compose exec api pytest tests/test_specific.py
```

### Rebuild Containers

After changing requirements.txt or Dockerfile:

```bash
docker-compose build
docker-compose up
```

Force rebuild without cache:

```bash
docker-compose build --no-cache
```

### Shell Access

Get a shell in the API container:

```bash
docker-compose exec api bash
```

Run Python shell with app context:

```bash
docker-compose exec api flask shell
```

### View Container Status

```bash
docker-compose ps
```

### Clean Up

Remove all containers, volumes, and images:

```bash
docker-compose down -v --rmi all
```

## Environment Variables

The API service uses these environment variables (defined in docker-compose.yml):

### Flask Configuration

- `FLASK_APP`: Application entry point
- `FLASK_ENV`: Environment (development/production)
- `FLASK_DEBUG`: Enable debug mode

### Database Configuration

- `DATABASE_URL`: PostgreSQL connection string

### Redis Configuration

- `REDIS_URL`: Redis connection string

### Security

- `SECRET_KEY`: Flask secret key (change in production!)
- `JWT_SECRET_KEY`: JWT signing key (change in production!)

### API Configuration

- `API_TITLE`: API title for documentation
- `API_VERSION`: API version

### Logging

- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `JSON_LOGS`: Enable JSON-formatted logs

## Troubleshooting

### Port Already in Use

If ports 5000, 5432, or 6379 are already in use, you can change them in
docker-compose.override.yml:

```yaml
services:
  api:
    ports:
      - "8000:5000"  # Map to different host port
```

### Database Connection Errors

Ensure the database is healthy:

```bash
docker-compose ps postgres
```

Check database logs:

```bash
docker-compose logs postgres
```

### Permission Errors

The API container runs as a non-root user (UID 1000). If you encounter
permission errors with mounted volumes, ensure your local files are readable:

```bash
chmod -R 755 src/
```

### Container Won't Start

Check logs for the failing service:

```bash
docker-compose logs api
```

Rebuild the container:

```bash
docker-compose build api
docker-compose up api
```

### Database Migrations Fail

Reset the database and run migrations again:

```bash
docker-compose down -v
docker-compose up -d postgres redis
sleep 5
docker-compose up api
```

## Development Workflow

### 1. Start Services

```bash
docker-compose up -d
```

### 2. Watch Logs

```bash
docker-compose logs -f api
```

### 3. Make Code Changes

Code changes in `src/` are automatically detected and the server reloads
(hot reload enabled in development mode).

### 4. Run Tests

```bash
docker-compose exec api pytest
```

### 5. Commit Changes

```bash
git add .
git commit -m "Your changes"
```

### 6. Stop Services

```bash
docker-compose down
```

## Production Considerations

**Important**: The docker-compose.yml file is configured for development.
For production deployment:

1. Use proper secret management (not hardcoded secrets)
1. Disable debug mode
1. Use production-grade database with backups
1. Configure proper logging and monitoring
1. Use reverse proxy (nginx) in front of Flask
1. Enable HTTPS/TLS
1. Configure resource limits
1. Use Docker secrets or environment variable injection
1. Implement health checks and restart policies
1. Use multi-stage builds to reduce image size

## CI/CD Integration

The Docker setup can be used in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          docker-compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit
```

## Related Documentation

- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Flask Deployment Guide](https://flask.palletsprojects.com/en/latest/deploying/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Redis Docker Image](https://hub.docker.com/_/redis)

## Support

For issues or questions:

1. Check the troubleshooting section above
1. Review Docker logs: `docker-compose logs`
1. Check service health: `docker-compose ps`
1. Create an issue in the repository
