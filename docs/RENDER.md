# Render Deployment Notes

This document provides recommended settings for deploying the Brikk infrastructure application on Render.

## Pre-deploy Command

To ensure database migrations are run before the application starts, set the following pre-deploy command
in your Render service settings:

```bash
alembic upgrade head
```

This command will run the Alembic migrations to the latest version, ensuring the database schema is
up-to-date before the application boots.

## Environment Variables

Set the following environment variable to ensure Alembic can find the application modules:

```ini
PYTHONPATH=/opt/render/project/src
```

This ensures that the `src` directory is on the Python path, allowing Alembic to import the necessary
models and configurations.

## Runtime Migrations

As a fallback, the application is also configured to run migrations at startup if the
`BRIKK_DB_MIGRATE_ON_START` environment variable is set to `true`. However, using the pre-deploy command
is the recommended approach for a cleaner and more reliable deployment process.
