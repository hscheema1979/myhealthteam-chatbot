"""Tests for query handlers"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from src.chatbot.handlers.query_handlers import QueryHandlers


@patch('src.chatbot.handlers.query_handlers.database.get_db_connection')
def test_get_my_stats_returns_structure(mock_conn):
    """Test get_my_stats returns proper structure"""
    # Mock database response
    mock_connection = MagicMock()
    mock_conn.return_value = mock_connection

    mock_connection.execute.return_value.fetchone.return_value = {
        "patient_count": 55,
        "task_count": 23,
        "total_minutes": 690
    }
    mock_connection.execute.return_value.fetchone.return_value = (
        "coordinator_tasks_2026_02",
    )

    handlers = QueryHandlers()
    result = handlers.get_my_stats(user_id=1, time_range="month")

    # Verify structure
    assert "patient_count" in result
    assert "task_count" in result
    assert "total_minutes" in result
    assert isinstance(result["patient_count"], int)


def test_format_stats_response():
    """Test formatting stats response for chat"""
    handlers = QueryHandlers()

    stats_data = {
        "patient_count": 55,
        "task_count": 23,
        "total_minutes": 690,
    }

    response = handlers.format_stats_response(stats_data, time_range="week")

    assert "55" in response
    assert "23" in response
    assert "690" in response
    assert "week" in response.lower()


def test_format_patients_response():
    """Test formatting patient list for chat"""
    handlers = QueryHandlers()

    patients = [
        {
            "first_name": "Ada",
            "last_name": "Lopez",
            "status": "Active",
            "facility": "Autumn Ridge",
            "last_visit_date": "2026-02-20"
        },
        {
            "first_name": "Ben",
            "last_name": "Kim",
            "status": "Active",
            "facility": "Summit Care",
            "last_visit_date": None
        },
    ]

    response = handlers.format_patients_response(patients)

    assert "2 Patient(s)" in response
    assert "Ada Lopez" in response
    assert "Ben Kim" in response


def test_format_tasks_response():
    """Test formatting task list for chat"""
    handlers = QueryHandlers()

    tasks = [
        {
            "task_description": "PCP Visit",
            "service_type": "PCP",
            "duration_minutes": 30
        },
        {
            "task_description": "Follow Up",
            "service_type": "Follow Up",
            "duration_minutes": 15
        },
    ]

    response = handlers.format_tasks_response(tasks)

    assert "2 Recent Task(s)" in response
    assert "PCP Visit" in response
    assert "30 min" in response
