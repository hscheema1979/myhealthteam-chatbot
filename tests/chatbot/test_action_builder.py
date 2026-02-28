"""Tests for Action Builder and Transaction Executor"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.chatbot.action_builder import ActionBuilder, ValidatedAction
from src.chatbot.transaction_executor import TransactionExecutor


def test_validated_action_formatting():
    """Test ValidatedAction formats confirmation summaries"""
    action = ValidatedAction(
        action_type="INSERT",
        table_name="coordinator_tasks_2026_02",
        changes={
            "coordinator_id": 1,
            "patient_id": 123,
            "duration_minutes": 30,
            "service_type": "PCP",
            "task_description": "PCP visit"
        }
    )

    summary = action.get_confirmation_summary()

    assert "CONFIRMATION REQUIRED" in summary
    assert "30" in summary
    assert "PCP" in summary
    assert "123" in summary


def test_validated_action_with_warnings():
    """Test ValidatedAction includes warnings"""
    action = ValidatedAction(
        action_type="INSERT",
        table_name="coordinator_tasks_2026_02",
        changes={"coordinator_id": 1, "patient_id": 999},
        warnings=["Patient ID 999 not verified"]
    )

    assert action.warnings == ["Patient ID 999 not verified"]
    assert action.is_valid  # No validation errors


def test_validated_action_validation_errors():
    """Test ValidatedAction with validation errors"""
    action = ValidatedAction(
        action_type="UNKNOWN",
        table_name="nonexistent_table",
        changes={},
        validation_errors=["Table does not exist"]
    )

    assert not action.is_valid
    assert len(action.validation_errors) > 0


@patch('src.chatbot.action_builder.DatabaseSchemaInspector')
def test_action_builder_builds_insert_action(mock_schema):
    """Test ActionBuilder builds INSERT action"""
    # Mock schema
    mock_inspector = Mock()
    mock_schema.return_value = mock_inspector
    mock_inspector.table_exists.return_value = True
    mock_inspector.validate_value.return_value = (True, None)

    builder = ActionBuilder()

    # Mock fallback parse to return structured action
    with patch.object(builder, '_fallback_parse') as mock_parse:
        mock_parse.return_value = {
            "action": "INSERT",
            "table": "coordinator_tasks_2026_02",
            "data": {
                "duration_minutes": 30,
                "service_type": "PCP",
                "patient_id": 123
            },
            "warnings": []
        }

        action = builder.build_action("Add 30min PCP", user_id=1)

        assert action.action_type == "INSERT"
        assert action.table_name == "coordinator_tasks_2026_02"
        assert action.changes["duration_minutes"] == 30


@patch('src.chatbot.transaction_executor.database.get_db_connection')
def test_transaction_executor_executes_insert(mock_db):
    """Test TransactionExecutor executes INSERT successfully"""
    # Mock database
    mock_conn = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.execute.return_value.lastrowid = 12345
    mock_conn.execute.return_value.rowcount = 1

    executor = TransactionExecutor()
    action = ValidatedAction(
        action_type="INSERT",
        table_name="test_table",
        changes={"col1": "value1"},
        sql_params=("value1",)
    )

    result = executor.execute(action, user_id=1)

    assert result["success"] == True
    assert "successfully" in result["message"].lower()


@patch('src.chatbot.transaction_executor.database.get_db_connection')
def test_transaction_executor_rolls_back_on_error(mock_db):
    """Test TransactionExecutor rolls back on error"""
    # Mock database to raise error
    mock_conn = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.execute.side_effect = Exception("Database error")

    executor = TransactionExecutor()
    action = ValidatedAction(
        action_type="INSERT",
        table_name="test_table",
        changes={"col1": "value1"}
    )

    result = executor.execute(action, user_id=1)

    assert result["success"] == False
    assert "Error" in result["message"]
