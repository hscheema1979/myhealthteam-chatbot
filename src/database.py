"""
Database module for MyHealthTeam Chatbot

Uses TEST DATABASE ONLY in isolated workspace /opt/test_myhealthteam/
"""
import sqlite3
import os
from typing import Optional
from contextlib import contextmanager


# Test database path in workspace
TEST_DB = "/opt/test_myhealthteam/production_backup_for_testing.db"
DEFAULT_DB_PATH = TEST_DB


def get_db_path() -> str:
    """Get database path from environment or use default test database"""
    db_path = os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)

    # Enforce test database only
    if db_path != TEST_DB:
        raise ValueError(
            f"SECURITY ERROR: Chatbot must use test database only!\n"
            f"Current path: {db_path}\n"
            f"Required: {TEST_DB}"
        )

    return db_path


@contextmanager
def get_db_connection():
    """
    Get a database connection

    Yields:
        sqlite3.Connection: Database connection

    Raises:
        sqlite3.Error: If database connection fails
        ValueError: If database path is not allowed
    """
    db_path = get_db_path()

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
    """Check if a table exists in the database"""
    with get_db_connection() as conn:
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ).fetchone()
        return result is not None
