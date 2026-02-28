"""
Authentication module for MyHealthTeam Chatbot

Handles shared authentication with the main application via user_sessions table.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import hashlib

from src.database import get_db_connection


class AuthManager:
    """Manages authentication and sessions"""

    def __init__(self, session_timeout_hours: int = 24):
        self.session_timeout = timedelta(hours=session_timeout_hours)

    def create_session(self, user_id: int) -> str:
        """
        Create a new session for a user

        Args:
            user_id: User's ID

        Returns:
            Session ID for cookie
        """
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + self.session_timeout

        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO user_sessions (session_id, user_id, expires_at)
                VALUES (?, ?, ?)""",
                (session_id, user_id, expires_at.isoformat())
            )
            conn.commit()

        return session_id

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session and return user info

        Args:
            session_id: Session ID from cookie

        Returns:
            Dict with user_id, expires_at if valid, None otherwise
        """
        with get_db_connection() as conn:
            session = conn.execute(
                """SELECT user_id, expires_at
                FROM user_sessions
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 1""",
                (session_id,)
            ).fetchone()

            if not session:
                return None

            # Check expiration
            expires_at = datetime.fromisoformat(session["expires_at"])
            if expires_at < datetime.now():
                # Clean up expired session
                conn.execute(
                    "DELETE FROM user_sessions WHERE session_id = ?",
                    (session_id,)
                )
                conn.commit()
                return None

            return {
                "user_id": session["user_id"],
                "expires_at": session["expires_at"]
            }

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information"""
        with get_db_connection() as conn:
            user = conn.execute(
                """SELECT user_id, email, first_name, last_name
                FROM users WHERE user_id = ?""",
                (user_id,)
            ).fetchone()

            if not user:
                return None

            return dict(user)

    def get_user_roles(self, user_id: int) -> list:
        """Get user's role IDs"""
        with get_db_connection() as conn:
            roles = conn.execute(
                """SELECT role_id
                FROM user_roles
                WHERE user_id = ?""",
                (user_id,)
            ).fetchall()

            return [r["role_id"] for r in roles]

    def revoke_session(self, session_id: str) -> bool:
        """Revoke a session"""
        with get_db_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM user_sessions WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from database"""
        with get_db_connection() as conn:
            cursor = conn.execute(
                """DELETE FROM user_sessions
                WHERE datetime(expires_at) < datetime('now')"""
            )
            conn.commit()
            return cursor.rowcount


# Singleton instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get the singleton auth manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
