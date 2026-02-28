"""Tests for Gemini CLI client"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.chatbot.gemini_client import GeminiClient, GeminiResponseBuffer


def test_response_buffer_basic():
    """Test basic response buffering"""
    buffer = GeminiResponseBuffer(min_buffer_size=5)  # Lower threshold for testing

    # Add content and verify no errors
    chunks = buffer.add_data("Hello world. This is a test.")
    # Just verify it doesn't crash
    assert isinstance(chunks, list)

    # Manual flush should always work
    flushed = buffer.flush()
    assert isinstance(flushed, str)


def test_response_buffer_code_block_detection():
    """Test code block detection prevents splitting"""
    buffer = GeminiResponseBuffer()

    # Start code block
    chunks = buffer.add_data("```python")
    assert len(chunks) == 0  # Not complete
    assert buffer.in_code_block == True

    # Add content
    chunks = buffer.add_data("def test():\n    pass")
    assert len(chunks) == 0  # Still in code block

    # Close code block
    chunks = buffer.add_data("```")
    assert len(chunks) >= 1  # Should flush now
    assert buffer.in_code_block == False


def test_response_buffer_flush():
    """Test manual flush"""
    buffer = GeminiResponseBuffer()

    buffer.add_data("Partial message")
    chunks = buffer.flush()

    assert chunks == "Partial message"
    assert buffer.buffer == ""


def test_gemini_client_initialization():
    """Test Gemini client can be initialized"""
    client = GeminiClient()

    assert client.cli_command == "gemini"
    assert client.timeout_ms == 30000
    assert client.active_processes == {}


def test_fallback_parse():
    """Test fallback to pattern matching when Gemini unavailable"""
    client = GeminiClient()

    # Mock the fallback to use pattern parser
    with patch.object(client, '_fallback_parse') as mock_fallback:
        mock_fallback.return_value = {
            "intent": "QUERY_STATS",
            "entities": {},
            "confidence": 0.95,
            "fallback": True
        }

        # Mock subprocess to raise error
        with patch('subprocess.Popen', side_effect=FileNotFoundError("gemini not found")):
            result = client.parse_message(
                message="/stats",
                context={"user_id": 1, "roles": ["coordinator"]}
            )

            # Should fall back to pattern matching
            assert result["intent"] == "QUERY_STATS"
            assert result.get("fallback") == True


def test_filter_debug_messages():
    """Test filtering of debug messages"""
    client = GeminiClient()

    # Debug message should be filtered out
    assert client._filter_debug_messages("[DEBUG] Loading config...") == ""
    assert client._filter_debug_messages("Loaded cached credentials") == ""

    # Normal message should pass through
    assert client._filter_debug_messages("You have 55 patients") == "You have 55 patients"
