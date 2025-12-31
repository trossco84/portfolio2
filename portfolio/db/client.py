"""Database client and connection management."""

from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg.rows import dict_row

from portfolio.config import settings
from portfolio.utils.logging import logger


class DatabaseClient:
    """Postgres database client."""

    def __init__(self, connection_string: str):
        """Initialize database client."""
        self.connection_string = connection_string

    @contextmanager
    def get_connection(self) -> Generator[psycopg.Connection, None, None]:
        """Get a database connection context manager."""
        conn = None
        try:
            conn = psycopg.connect(self.connection_string, row_factory=dict_row)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_cursor(self) -> Generator[psycopg.Cursor, None, None]:
        """Get a database cursor context manager."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                yield cur
                conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> list[dict]:
        """Execute a SELECT query and return results."""
        with self.get_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def execute_one(self, query: str, params: tuple = ()) -> dict | None:
        """Execute a SELECT query and return one result."""
        with self.get_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT query and return the inserted ID."""
        with self.get_cursor() as cur:
            cur.execute(query + " RETURNING id", params)
            result = cur.fetchone()
            return result["id"] if result else None

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an UPDATE/DELETE query and return affected rows."""
        with self.get_cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount


# Global database client instance
db_client = DatabaseClient(settings.database_url)
