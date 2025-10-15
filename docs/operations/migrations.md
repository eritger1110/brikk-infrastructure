# Database Migration Operations

## Overview

This document describes the database migration system for the Brikk infrastructure project, including the baseline
migration, stamping procedures, and deployment processes.

## Migration System

The project uses **Alembic** for database schema migrations, integrated with SQLAlchemy models.

### Baseline Migration

**Revision ID:** `b07a366647c3`

**Created:** October 15, 2025

**Purpose:** Establishes the complete baseline schema for fresh database installations.

This baseline migration creates all 23 core tables with the correct schema from the start, including:

- Organizations, users, and authentication
- Agents, services, and coordination
- Billing, subscriptions, and payments
- Monitoring, metrics, and health checks
- Rate limiting and idempotency

### Key Schema Details

- `agent_services.agent_id` is defined as `String(36)` from the baseline
- All foreign key relationships are properly established
- Indexes are created for performance optimization

## Fresh Installation

For new databases (including Render deployments), simply run:

```bash
python3.11 -m alembic upgrade head
```

This will apply the baseline migration and create all tables.

## Legacy Database Migration

For databases that were created before the migration system was implemented, see the detailed guide in
`docs/LEGACY_DB_MIGRATION.md`.

**Summary:** Use `alembic stamp b07a366647c3` to mark the database as being at the baseline revision.

## Production Deployment History

### Render Database Stamping (October 15, 2025)

The production Render database was successfully stamped with the baseline revision using a GitHub Actions workflow.

**Process:**

1. Created branch-triggered workflow (`.github/workflows/stamp-render-db.yml`)
2. Pushed to `ops/stamp-db` branch to trigger automatic stamping
3. Workflow verified: `alembic_version: b07a366647c3`
4. Subsequent deployments applied migrations successfully

**Result:** Production database is now properly tracked by Alembic and ready for future migrations.

## CI/CD Integration

### Migration Testing

The CI workflow (`.github/workflows/ci.yaml`) includes a `migrations` job that:

- Tests migrations on a clean SQLite database
- Verifies all tables are created correctly
- Validates schema correctness (e.g., `agent_services.agent_id` type)

This ensures migration issues are caught before deployment.

### Health Checks

The application includes health check endpoints for deployment verification:

- `/health` - Standard health check (used by Render)
- `/healthz` - Kubernetes-style health check
- `/readyz` - Readiness check with dependency validation

## Future Migrations

When creating new migrations:

1. Make model changes in `src/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review and test the generated migration
4. Commit and push to trigger CI
5. Deploy to production

All migrations will build on the baseline revision `b07a366647c3`.

## Troubleshooting

### DuplicateTable Errors

If you see `DuplicateTable` errors during migration, it means:

- The database has tables but no `alembic_version` tracking
- Solution: Stamp the database with the appropriate revision

### Migration Chain Issues

If migrations fail to apply:

1. Check `alembic_version` table for current revision
2. Verify migration files exist in `migrations/versions/`
3. Ensure database connection is working
4. Check logs for specific error messages

## References

- Alembic Documentation: https://alembic.sqlalchemy.org/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- Legacy Migration Guide: `docs/LEGACY_DB_MIGRATION.md`

