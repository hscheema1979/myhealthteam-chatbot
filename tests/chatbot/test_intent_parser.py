"""Tests for intent parser"""

import pytest
from src.chatbot.intent_parser import IntentParser, Intent


def test_parse_stats_slash_command():
    """Test parsing /stats slash command"""
    parser = IntentParser()
    result = parser.parse("/stats")

    assert result.intent == Intent.QUERY_STATS
    assert result.entities == {}
    assert result.confidence > 0.95


def test_parse_stats_natural_language():
    """Test parsing natural language stats query"""
    parser = IntentParser()
    result = parser.parse("How many patients do I have?")

    assert result.intent == Intent.QUERY_STATS
    assert result.entities.get("scope") == "self"
    assert result.confidence > 0.7


def test_parse_patients_slash_command():
    """Test parsing /patients slash command"""
    parser = IntentParser()
    result = parser.parse("/patients active")

    assert result.intent == Intent.QUERY_PATIENTS
    assert result.entities.get("status") == "Active"
    assert result.confidence > 0.95


def test_parse_add_task_intent():
    """Test parsing add task intent"""
    parser = IntentParser()
    result = parser.parse("Add 30min PCP visit for John Smith")

    assert result.intent == Intent.ACTION_ADD_TASK
    assert result.entities.get("duration") == 30
    assert result.entities.get("service_type") == "PCP"
    assert "patient_name" in result.entities


def test_parse_unknown_message():
    """Test parsing unknown/ambiguous message"""
    parser = IntentParser()
    result = parser.parse("hello there")

    assert result.intent == Intent.UNKNOWN
    assert result.confidence < 0.5


def test_extract_duration_with_hours():
    """Test extracting duration with hours"""
    parser = IntentParser()
    result = parser.parse("Add 1 hour 30min visit")

    assert result.entities.get("duration") == 90  # 1 hour + 30 minutes


def test_extract_confirmation():
    """Test extracting confirmation intent"""
    parser = IntentParser()
    result = parser.parse("yes, go ahead")

    assert result.entities.get("confirmation") == True


def test_extract_cancellation():
    """Test extracting cancellation intent"""
    parser = IntentParser()
    result = parser.parse("no, cancel that")

    assert result.entities.get("cancellation") == False


def test_get_help_text():
    """Test help text generation"""
    parser = IntentParser()
    help_text = parser.get_help_text()

    assert "Stats" in help_text
    assert "Patients" in help_text
    assert "Tasks" in help_text
    assert "/help" in help_text
