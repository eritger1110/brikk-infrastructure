# Brikk Platform - Stage 2 Deployment Guide

This guide provides instructions for deploying Stage 2 of the Brikk platform.

## 1. Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Redis
- PostgreSQL

## 2. Configuration

Update the `.env` file with your database credentials, Redis URL, and other configuration settings.

## 3. Running the Platform

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade

# Start the application
flask run
```

## 4. Running the Celery Worker

```bash
celery -A src.services.task_queue.celery_app worker --loglevel=info
```

