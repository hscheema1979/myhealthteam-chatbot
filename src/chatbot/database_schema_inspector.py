"""
Database Schema Inspector

Validates database schema and constraints before executing actions.
Ensures surgical precision by knowing exactly what can be changed.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import sqlite3

from src import database


@dataclass
class ColumnInfo:
    """Information about a database column"""
    name: str
    type: str
    nullable: bool
    default: Any
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_table: Optional[str] = None
    foreign_column: Optional[str] = None
    valid_values: Optional[List[str]] = None  # For ENUM-like columns


@dataclass
class TableInfo:
    """Information about a database table"""
    name: str
    columns: Dict[str, ColumnInfo]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, str]]
    constraints: List[str]


class DatabaseSchemaInspector:
    """
    Inspects database schema to enable safe, surgical changes.

    Validates:
    - Table existence
    - Column existence and types
    - Constraints (NOT NULL, CHECK, FOREIGN KEY)
    - Valid values for ENUM-like columns
    """

    def __init__(self):
        """Initialize inspector and cache schema"""
        self._schema_cache: Dict[str, TableInfo] = {}
        self._refresh_schema()

    def _refresh_schema(self):
        """Load and cache database schema"""
        conn = database.get_db_connection()

        # Get all tables
        tables = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """).fetchall()

        for table_row in tables:
            table_name = table_row["name"]
            if table_name.startswith("sqlite_"):
                continue  # Skip system tables

            self._schema_cache[table_name] = self._inspect_table(conn, table_name)

        conn.close()

    def _inspect_table(self, conn: sqlite3.Connection, table_name: str) -> TableInfo:
        """Inspect a single table's schema"""
        # Get column info
        columns_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()

        columns = {}
        primary_keys = []

        for col in columns_info:
            col_name = col["name"]
            columns[col_name] = ColumnInfo(
                name=col_name,
                type=col["type"],
                nullable=col["notnull"] == 0,
                default=col["dflt_value"],
                is_primary_key=col["pk"] > 0
            )

            if col["pk"] > 0:
                primary_keys.append(col_name)

        # Get foreign keys
        foreign_keys = []
        fk_info = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()

        for fk in fk_info:
            foreign_keys.append({
                "column": fk["from"],
                "foreign_table": fk["table"],
                "foreign_column": fk["to"]
            })

            if fk["from"] in columns:
                columns[fk["from"]].is_foreign_key = True
                columns[fk["from"]].foreign_table = fk["table"]
                columns[fk["from"]].foreign_column = fk["to"]

        # Get constraints
        constraints = []
        try:
            check_constraints = conn.execute(f"PRAGMA index_list({table_name})").fetchall()
            for constraint in check_constraints:
                if constraint["origin"] == "c":
                    constraints.append(constraint["name"])
        except:
            pass  # Some SQLite versions don't support this

        return TableInfo(
            name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            constraints=constraints
        )

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        return table_name in self._schema_cache

    def get_table(self, table_name: str) -> Optional[TableInfo]:
        """Get table information"""
        return self._schema_cache.get(table_name)

    def column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if column exists in table"""
        table = self.get_table(table_name)
        return table and column_name in table.columns

    def validate_value(
        self,
        table_name: str,
        column_name: str,
        value: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a value against column constraints

        Returns:
            (is_valid, error_message)
        """
        table = self.get_table(table_name)
        if not table:
            return False, f"Table {table_name} does not exist"

        column = table.columns.get(column_name)
        if not column:
            return False, f"Column {column_name} does not exist in {table_name}"

        # Type validation
        if value is None:
            if not column.nullable:
                return False, f"Column {column_name} cannot be NULL"
            return True, None

        # Integer validation
        if "INT" in column.type.upper():
            try:
                int(value)
            except (ValueError, TypeError):
                return False, f"Column {column_name} requires an integer"

        # Real/FLOAT validation
        elif "REAL" in column.type.upper() or "FLOA" in column.type.upper():
            try:
                float(value)
            except (ValueError, TypeError):
                return False, f"Column {column_name} requires a number"

        # TEXT length validation
        elif "TEXT" in column.type.upper():
            if len(str(value)) > 1000000:  # SQLite has no strict limit but be reasonable
                return False, f"Value too long for column {column_name}"

        # Specific column validations
        if table_name == "patients" or table_name.startswith("coordinator_tasks_"):
            return self._validate_patient_column(column_name, value)

        return True, None

    def _validate_patient_column(self, column_name: str, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate specific patient/task columns"""
        # Status validation
        if column_name == "status":
            valid_statuses = ["Active", "Inactive", "Discharged", "Pending"]
            if value not in valid_statuses:
                return False, f"Status must be one of: {', '.join(valid_statuses)}"

        # GOC validation
        elif column_name == "goc_status":
            valid_goc = ["Rev/Confirm", "Discuss", "Documentation"]
            if value not in valid_goc:
                return False, f"GOC must be one of: {', '.join(valid_goc)}"

        # Code status validation
        elif column_name == "code_status":
            valid_codes = ["Full Code", "DNR", "DNI", "Partial Code"]
            if value not in valid_codes:
                return False, f"Code status must be one of: {', '.join(valid_codes)}"

        return True, None

    def get_valid_values(self, table_name: str, column_name: str) -> Optional[List[str]]:
        """Get valid values for an ENUM-like column"""
        if column_name == "status":
            return ["Active", "Inactive", "Discharged", "Pending"]
        elif column_name == "goc_status":
            return ["Rev/Confirm", "Discuss", "Documentation"]
        elif column_name == "code_status":
            return ["Full Code", "DNR", "DNI", "Partial Code"]
        return None

    def refresh(self):
        """Refresh schema cache"""
        self._refresh_schema()
