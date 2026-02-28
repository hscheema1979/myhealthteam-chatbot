"""
Core utilities for MyHealthTeam Chatbot

Provides user role management and common utilities.
"""
from typing import List

from src.database import get_db_connection


def get_user_role_ids(user_id: int) -> List[int]:
    """
    Get all role IDs for a user

    Args:
        user_id: User's ID

    Returns:
        List of role IDs
    """
    with get_db_connection() as conn:
        roles = conn.execute(
            """SELECT role_id
            FROM user_roles
            WHERE user_id = ?""",
            (user_id,)
        ).fetchall()

        return [r["role_id"] for r in roles]


def get_user_role_names(user_id: int) -> List[str]:
    """
    Get all role names for a user

    Args:
        user_id: User's ID

    Returns:
        List of role names
    """
    with get_db_connection() as conn:
        roles = conn.execute(
            """SELECT r.role_name
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.role_id
            WHERE ur.user_id = ?""",
            (user_id,)
        ).fetchall()

        return [r["role_name"] for r in roles]


def has_role(user_id: int, role_id: int) -> bool:
    """Check if user has a specific role"""
    return role_id in get_user_role_ids(user_id)


def is_admin(user_id: int) -> bool:
    """Check if user is an admin (role_id = 34)"""
    return has_role(user_id, 34)


def is_coordinator(user_id: int) -> bool:
    """Check if user is a care coordinator (role_id = 36)"""
    return has_role(user_id, 36)


def is_provider(user_id: int) -> bool:
    """Check if user is a care provider (role_id = 33)"""
    return has_role(user_id, 33)


def is_manager(user_id: int) -> bool:
    """Check if user is a coordinator manager (role_id = 40)"""
    return has_role(user_id, 40)
