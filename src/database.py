"""
Database module for MyHealthTeam Chatbot

Configured to use TEST DATABASE ONLY in isolated workspace /opt/test_myhealthteam/
"""
import sqlite3
import os
from typing import Optional
from contextlib import contextmanager


# Workspace isolation - chatbot only operates within this directory
WORKSPACE = "/opt/test_myhealthteam"

# Test database path within workspace
DEFAULT_DB_PATH = os.path.join(WORKSPACE, "chatbot", "production_backup_for_testing.db")


def get_db_path() -> str:
    """Get database path from environment or use default test database in workspace"""
    db_path = os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)

    # Enforce workspace isolation
    if not db_path.startswith(WORKSPACE):
        raise ValueError(
            f"SECURITY ERROR: Chatbot must use database within workspace {WORKSPACE}!\n"
            f"Current path: {db_path}\n"
            f"Expected: {DEFAULT_DB_PATH}"
        )

    # Verify it's a test database
    if "production_backup_for_testing" not in db_path and "test" not in db_path.lower():
        raise ValueError(
            f"SECURITY ERROR: Chatbot must use test database only!\n"
            f"Current path: {db_path}"
        )

    return db_path


@contextmanager
def get_db_connection():
    """
    Get a database connection to the TEST database in workspace

    Yields:
        sqlite3.Connection: Database connection

    Raises:
        sqlite3.Error: If database connection fails
        ValueError: If database is not in workspace or not a test database
    """
    db_path = get_db_path()

    # Verify workspace isolation
    if not db_path.startswith(WORKSPACE):
        raise ValueError(
            f"SECURITY ERROR: Database must be in workspace {WORKSPACE}"
        )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()


def execute_query(query: str, params: tuple = (), fetch_one: bool = False):
    """
    Execute a SQL query on the test database in workspace

    Args:
        query: SQL query with placeholders
        params: Query parameters
        fetch_one: If True, fetch single row; otherwise fetch all

    Returns:
        Row or list of rows
    """
    with get_db_connection() as conn:
        cursor = conn.execute(query, params)
        if fetch_one:
            return cursor.fetchone()
        return cursor.fetchall()


def get_table_schema(table_name: str) -> list:
    """Get schema information for a table"""
    with get_db_connection() as conn:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the test database"""
    with get_db_connection() as conn:
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()
        return result is not None


# Verify workspace on import
if __name__ != "__main__":
    current_db = get_db_path()
    if not current_db.startswith(WORKSPACE):
        import warnings
        warnings.warn(
            f"WARNING: Database path is not in workspace {WORKSPACE}: {current_db}",
            RuntimeWarning
        )
