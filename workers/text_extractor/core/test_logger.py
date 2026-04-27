"""
Unit tests for structured JSON logging infrastructure.
"""

import json
import logging
from io import StringIO
import sys
import pytest

from workers.text_extractor.core.logger import (
    JSONFormatter,
    setup_logging,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
    log_with_fields,
    log_node_start,
    log_node_complete,
    log_node_error,
)


def test_json_formatter_basic():
    """Test JSONFormatter produces valid JSON output."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    output = formatter.format(record)
    log_data = json.loads(output)
    
    assert log_data['level'] == 'INFO'
    assert log_data['logger'] == 'test_logger'
    assert log_data['message'] == 'Test message'
    assert 'timestamp' in log_data
    assert log_data['timestamp'].endswith('Z')


def test_json_formatter_with_correlation_id():
    """Test JSONFormatter includes correlation ID when set."""
    formatter = JSONFormatter()
    set_correlation_id("test-correlation-123")
    
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    output = formatter.format(record)
    log_data = json.loads(output)
    
    assert log_data['correlation_id'] == 'test-correlation-123'
    
    clear_correlation_id()


def test_json_formatter_with_extra_fields():
    """Test JSONFormatter includes extra fields."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.extra_fields = {'user_id': 123, 'action': 'test'}
    
    output = formatter.format(record)
    log_data = json.loads(output)
    
    assert log_data['user_id'] == 123
    assert log_data['action'] == 'test'


def test_setup_logging():
    """Test setup_logging configures logging correctly."""
    setup_logging("DEBUG")
    
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) > 0
    assert isinstance(root_logger.handlers[0].formatter, JSONFormatter)


def test_correlation_id_context():
    """Test correlation ID context management."""
    assert get_correlation_id() is None
    
    set_correlation_id("test-123")
    assert get_correlation_id() == "test-123"
    
    clear_correlation_id()
    assert get_correlation_id() is None


def test_log_with_fields(caplog):
    """Test log_with_fields adds structured fields."""
    logger = logging.getLogger("test")
    setup_logging("INFO")
    
    # Capture log output
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    
    log_with_fields(logger, logging.INFO, "Test message", user_id=123, action="test")
    
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data['message'] == 'Test message'
    assert log_data['user_id'] == 123
    assert log_data['action'] == 'test'


def test_log_node_start():
    """Test log_node_start logs node execution start."""
    logger = logging.getLogger("test")
    setup_logging("INFO")
    
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    
    state = {'message': 'Hello', 'user_id': 123}
    log_node_start(logger, "intent_node", state)
    
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert 'Node started: intent_node' in log_data['message']
    assert log_data['node'] == 'intent_node'
    assert log_data['event'] == 'node_start'
    assert 'state' in log_data


def test_log_node_complete():
    """Test log_node_complete logs node execution completion."""
    logger = logging.getLogger("test")
    setup_logging("INFO")
    
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    
    state_changes = {'intent': 'NEW'}
    log_node_complete(logger, "intent_node", state_changes)
    
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert 'Node completed: intent_node' in log_data['message']
    assert log_data['node'] == 'intent_node'
    assert log_data['event'] == 'node_complete'
    assert 'state_changes' in log_data


def test_log_node_error():
    """Test log_node_error logs node execution errors."""
    logger = logging.getLogger("test")
    setup_logging("INFO")
    
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    
    error = ValueError("Test error")
    log_node_error(logger, "intent_node", error)
    
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert 'Node error: intent_node' in log_data['message']
    assert log_data['node'] == 'intent_node'
    assert log_data['event'] == 'node_error'
    assert log_data['error_type'] == 'ValueError'
    assert log_data['error_message'] == 'Test error'


def test_sanitize_state_redacts_sensitive_data():
    """Test that sensitive data is redacted from state logs."""
    logger = logging.getLogger("test")
    setup_logging("INFO")
    
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    
    state = {
        'message': 'Hello',
        'api_key': 'secret-key-123',
        'user_token': 'token-456'
    }
    log_node_start(logger, "test_node", state)
    
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert log_data['state']['api_key'] == '[REDACTED]'
    assert log_data['state']['user_token'] == '[REDACTED]'
    assert log_data['state']['message'] == 'Hello'


def test_sanitize_state_truncates_long_strings():
    """Test that long strings are truncated in state logs."""
    logger = logging.getLogger("test")
    setup_logging("INFO")
    
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    
    long_string = 'a' * 600
    state = {'long_field': long_string}
    log_node_start(logger, "test_node", state)
    
    output = stream.getvalue()
    log_data = json.loads(output)
    
    assert len(log_data['state']['long_field']) < 600
    assert '[truncated]' in log_data['state']['long_field']
