#!/usr/bin/env python3
"""Database migration runner."""

import os
import sys
from pathlib import Path

import psycopg

from portfolio.config import settings
from portfolio.utils.logging import logger


def run_migrations() -> None:
    """Run all SQL migration files in order."""
    migrations_dir = Path(__file__).parent
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        logger.info("No migration files found")
        return

    logger.info(f"Found {len(migration_files)} migration file(s)")

    try:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                # Create migrations tracking table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL UNIQUE,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                conn.commit()

                # Get already applied migrations
                cur.execute("SELECT filename FROM schema_migrations")
                applied = {row[0] for row in cur.fetchall()}

                # Run pending migrations
                for migration_file in migration_files:
                    filename = migration_file.name

                    if filename in applied:
                        logger.info(f"Skipping {filename} (already applied)")
                        continue

                    logger.info(f"Applying {filename}...")
                    sql = migration_file.read_text()

                    try:
                        cur.execute(sql)
                        cur.execute(
                            "INSERT INTO schema_migrations (filename) VALUES (%s)", (filename,)
                        )
                        conn.commit()
                        logger.info(f"Successfully applied {filename}")
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"Failed to apply {filename}: {e}")
                        raise

        logger.info("All migrations completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
