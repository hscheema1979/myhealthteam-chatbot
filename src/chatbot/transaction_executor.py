"""
Transaction Executor - Safe, Surgical Database Operations

Executes database actions with transaction safety:
- All-or-nothing changes (atomicity)
- Rollback on any error
- Complete audit logging
- Clear error messages
"""

from typing import Dict, Any, Optional
from datetime import datetime
import sqlite3

from src import database
from src.chatbot.action_builder import ValidatedAction
from src.chatbot.database_schema_inspector import DatabaseSchemaInspector


class TransactionExecutor:
    """
    Executes database actions with transaction safety.

    Every action is:
    1. Executed within a transaction
    2. Validated before COMMIT
    3. Rolled back on any error
    4. Logged to audit trail
    """

    def __init__(self):
        """Initialize executor"""
        self.schema = DatabaseSchemaInspector()

    def execute(self, action: ValidatedAction, user_id: int) -> Dict[str, Any]:
        """
        Execute a validated database action within a transaction

        Args:
            action: ValidatedAction to execute
            user_id: User performing the action

        Returns:
            Dict with success status, message, and details
        """
        if not action.is_valid:
            return {
                "success": False,
                "message": "Cannot execute invalid action",
                "errors": action.validation_errors
            }

        conn = database.get_db_connection()

        try:
            # Start transaction
            conn.execute("BEGIN IMMEDIATE TRANSACTION")

            # Execute the action based on type
            if action.action_type == "INSERT":
                result = self._execute_insert(conn, action, user_id)
            elif action.action_type == "UPDATE":
                result = self._execute_update(conn, action, user_id)
            elif action.action_type == "DELETE":
                result = self._execute_delete(conn, action, user_id)
            else:
                raise ValueError(f"Unknown action type: {action.action_type}")

            # If we got here, everything worked - commit
            conn.commit()

            # Log to audit trail
            self._log_action(conn, action, user_id, success=True)

            conn.close()

            return {
                "success": True,
                "message": result.get("message", "Action completed successfully"),
                "details": result
            }

        except Exception as e:
            # Rollback on any error
            try:
                conn.rollback()
            except:
                pass

            # Log failed attempt
            self._log_action(conn, action, user_id, success=False, error=str(e))

            conn.close()

            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "error": str(e)
            }

    def _execute_insert(
        self,
        conn: sqlite3.Connection,
        action: ValidatedAction,
        user_id: int
    ) -> Dict[str, Any]:
        """Execute INSERT action"""
        table = action.table_name
        data = action.changes

        # Build INSERT statement
        columns = list(data.keys())
        placeholders = ", ".join(["?"] * len(columns))

        sql = f"""
            INSERT INTO {table} ({", ".join(columns)})
            VALUES ({placeholders})
        """

        # Execute
        cursor = conn.execute(sql, list(data.values()))

        return {
            "message": f"Added new record to {table}",
            "row_id": cursor.lastrowid,
            "rows_affected": cursor.rowcount
        }

    def _execute_update(
        self,
        conn: sqlite3.Connection,
        action: ValidatedAction,
        user_id: int
    ) -> Dict[str, Any]:
        """Execute UPDATE action"""
        table = action.table_name
        target_id = action.target_id
        data = action.changes

        # Build UPDATE statement
        set_clause = ", ".join([f"{col} = ?" for col in data.keys()])

        sql = f"""
            UPDATE {table}
            SET {set_clause}
            WHERE patient_id = ?
        """

        params = list(data.values()) + [target_id]

        # Execute
        cursor = conn.execute(sql, params)

        if cursor.rowcount == 0:
            raise ValueError(f"No record found with patient_id = {target_id}")

        return {
            "message": f"Updated {table} (ID: {target_id})",
            "rows_affected": cursor.rowcount
        }

    def _execute_delete(
        self,
        conn: sqlite3.Connection,
        action: ValidatedAction,
        user_id: int
    ) -> Dict[str, Any]:
        """Execute DELETE action"""
        table = action.table_name
        target_id = action.target_id

        # Build DELETE statement
        sql = f"DELETE FROM {table} WHERE patient_id = ?"

        # Execute
        cursor = conn.execute(sql, [target_id])

        if cursor.rowcount == 0:
            raise ValueError(f"No record found with patient_id = {target_id}")

        return {
            "message": f"Deleted record from {table} (ID: {target_id})",
            "rows_affected": cursor.rowcount
        }

    def _log_action(
        self,
        conn: sqlite3.Connection,
        action: ValidatedAction,
        user_id: int,
        success: bool,
        error: Optional[str] = None
    ):
        """Log action to audit trail"""
        try:
            # Ensure audit_log table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    action_data TEXT,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT
                )
            """)

            # Insert log entry
            conn.execute("""
                INSERT INTO audit_log (
                    user_id, action_type, table_name, action_data,
                    success, error_message, timestamp, ip_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                action.action_type,
                action.table_name,
                str(action.changes),
                success,
                error,
                datetime.now().isoformat(),
                None  # IP address could be added from request context
            ))

        except Exception as e:
            # Don't fail the transaction if logging fails
            print(f"Warning: Failed to log action: {e}")

    def execute_with_confirmation(
        self,
        action: ValidatedAction,
        user_id: int,
        confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Execute action with confirmation flow

        Args:
            action: ValidatedAction to execute
            user_id: User performing the action
            confirmed: Whether user confirmed the action

        Returns:
            Dict with success status and message
        """
        if not confirmed:
            return {
                "success": False,
                "message": "Action cancelled - not confirmed",
                "confirmation_required": True,
                "confirmation_summary": action.get_confirmation_summary()
            }

        return self.execute(action, user_id)
