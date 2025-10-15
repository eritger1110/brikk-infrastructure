# Legacy Database Migration: Stamping to Baseline

## Introduction

This document provides instructions for migrating legacy Brikk databases that were created **before** the
implementation of our standardized Alembic migration workflow. If you are working with a fresh database installation,
you do not need to follow these steps; migrations will be applied automatically.

## The Problem: Missing Migration History

Legacy databases were created directly from SQLAlchemy models, which means they have all the necessary tables but lack
any Alembic migration history. As a result, attempting to run `alembic upgrade head` on these databases will fail
because Alembic will try to create tables that already exist.

To resolve this, we need to "stamp" the database, which tells Alembic that the database is already at a specific
revision without actually running the migration scripts.

## Solution: Stamping the Database to the Baseline

We will stamp the database with the `b07a366647c3` revision, which is our baseline schema. This will mark the database
as being up-to-date with the initial schema, allowing future migrations to be applied correctly.

### Step-by-Step Guide

1. **Ensure your environment is configured:**

   Make sure your `DATABASE_URL` environment variable is set to the correct connection string for your legacy database.

   ```bash
   export DATABASE_URL="your_database_connection_string"
   ```

2. **Run the `alembic stamp` command:**

   Execute the following command to stamp the database with the baseline revision ID:

   ```bash
   python3.11 -m alembic stamp b07a366647c3
   ```

### Verification

To verify that the stamping was successful, you can check the `alembic_version` table in your database. It should
contain a single entry with the revision ID `b07a366647c3`.

For a SQLite database, you can use the following command:

```bash
sqlite3 your_database.db "SELECT * FROM alembic_version;"
```

For other database systems, use your preferred database client to run the equivalent query.

## Future Migrations

After successfully stamping the database, you can apply all future migrations using the standard
`alembic upgrade head` command:

```bash
python3.11 -m alembic upgrade head
```

This will bring your legacy database schema up-to-date and ensure that it stays in sync with future changes.

