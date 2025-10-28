#!/bin/bash
# Pre-start script to run database migrations
# This runs automatically before the app starts on Render

set -e  # Exit on error

echo "========================================="
echo "Running database migrations..."
echo "========================================="

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set"
    exit 1
fi

# Run Alembic migrations
echo "Applying Alembic migrations..."
alembic upgrade head

echo "========================================="
echo "Migrations completed successfully!"
echo "========================================="

exit 0

