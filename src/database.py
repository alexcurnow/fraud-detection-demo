"""Database connection and initialization."""

import sqlite3
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "fraud_detection.db"
SCHEMA_PATH = Path(__file__).parent.parent / "schema.sql"


class Database:
    """SQLite database connection manager."""

    _connection: Optional[sqlite3.Connection] = None

    @classmethod
    def get_connection(cls) -> sqlite3.Connection:
        """Get or create database connection."""
        if cls._connection is None:
            cls._connection = sqlite3.connect(
                DB_PATH,
                check_same_thread=False,
                isolation_level=None  # Autocommit mode for event sourcing
            )
            cls._connection.row_factory = sqlite3.Row  # Access columns by name
            logger.info(f"Database connection established: {DB_PATH}")
        return cls._connection

    @classmethod
    def initialize_schema(cls, force: bool = False) -> None:
        """Initialize database schema from schema.sql file."""
        if force and DB_PATH.exists():
            DB_PATH.unlink()
            logger.warning("Existing database deleted (force=True)")

        if not SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

        conn = cls.get_connection()
        schema_sql = SCHEMA_PATH.read_text()

        # Execute schema (executescript handles its own transaction)
        try:
            conn.executescript(schema_sql)
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise

    @classmethod
    def execute(cls, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor."""
        conn = cls.get_connection()
        return conn.execute(query, params)

    @classmethod
    def execute_many(cls, query: str, params_list: list[tuple]) -> None:
        """Execute many queries with parameter list."""
        conn = cls.get_connection()
        conn.executemany(query, params_list)

    @classmethod
    def fetch_one(cls, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute query and fetch one result."""
        cursor = cls.execute(query, params)
        return cursor.fetchone()

    @classmethod
    def fetch_all(cls, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute query and fetch all results."""
        cursor = cls.execute(query, params)
        return cursor.fetchall()

    @classmethod
    def close(cls) -> None:
        """Close database connection."""
        if cls._connection:
            cls._connection.close()
            cls._connection = None
            logger.info("Database connection closed")
