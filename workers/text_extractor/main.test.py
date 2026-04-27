"""
Unit tests for RabbitMQ consumer with exponential backoff and HITL lock checking.

Validates: Requirements 4.4, 4.5, 4.6, 7.2, 7.3, 7.4
"""
import pytest
from unittest.mock import patch, MagicMock, call
import pika
import sys
import json

from workers.text_extractor.main import connect_to_rabbitmq, process_message


class TestRabbitMQConnectionRetry:
    """Test RabbitMQ connection retry logic with exponential backoff."""
    
    def test_successful_connection_first_attempt(self):
        """Test successful connection on first attempt."""
        # Arrange
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        
        # Act
        with patch('workers.text_extractor.main.pika.BlockingConnection', return_value=mock_connection):
            connection, channel = connect_to_rabbitmq()
        
        # Assert
        assert connection == mock_connection
        assert channel == mock_channel
        mock_channel.queue_declare.assert_called_once_with(queue='fast_text_queue', durable=True)
    
    def test_connection_retry_with_exponential_backoff(self):
        """Test connection retries with exponential backoff delays."""
        # Arrange
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise pika.exceptions.AMQPConnectionError("Connection failed")
            return mock_connection
        
        # Act
        with patch('workers.text_extractor.main.pika.BlockingConnection', side_effect=side_effect):
            with patch('workers.text_extractor.main.time.sleep') as mock_sleep:
                connection, channel = connect_to_rabbitmq()
        
        # Assert
        assert call_count == 3
        assert connection == mock_connection
        # Verify exponential backoff: 5 * 2^0 = 5, 5 * 2^1 = 10
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(5)  # First retry delay
        mock_sleep.assert_any_call(10)  # Second retry delay
    
    def test_max_retries_exhausted_exits_gracefully(self):
        """Test that max retries exhausted logs critical error and exits."""
        # Arrange
        def side_effect(*args, **kwargs):
            raise pika.exceptions.AMQPConnectionError("Connection failed")
        
        # Act & Assert
        with patch('workers.text_extractor.main.pika.BlockingConnection', side_effect=side_effect):
            with patch('workers.text_extractor.main.time.sleep'):
                with pytest.raises(SystemExit) as exc_info:
                    connect_to_rabbitmq()
                
                # Verify exit code is 1
                assert exc_info.value.code == 1
    
    def test_retry_count_respects_config(self):
        """Test that retry count respects RABBITMQ_MAX_RETRIES config."""
        # Arrange
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise pika.exceptions.AMQPConnectionError("Connection failed")
        
        # Act & Assert
        with patch('workers.text_extractor.main.pika.BlockingConnection', side_effect=side_effect):
            with patch('workers.text_extractor.main.time.sleep'):
                with pytest.raises(SystemExit):
                    connect_to_rabbitmq()
                
                # Verify it tried exactly 3 times (default RABBITMQ_MAX_RETRIES)
                assert call_count == 3
    
    def test_initial_delay_respects_config(self):
        """Test that initial delay respects RABBITMQ_INITIAL_RETRY_DELAY config."""
        # Arrange
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise pika.exceptions.AMQPConnectionError("Connection failed")
            return mock_connection
        
        # Act
        with patch('workers.text_extractor.main.pika.BlockingConnection', side_effect=side_effect):
            with patch('workers.text_extractor.main.time.sleep') as mock_sleep:
                connect_to_rabbitmq()
        
        # Assert
        # First retry should use initial delay (5 seconds by default)
        mock_sleep.assert_called_once_with(5)


class TestHITLLockChecking:
    """Test HITL lock checking in message processing."""
    
    def test_process_message_without_hitl_lock(self):
        """Test processing a new message without existing HITL lock."""
        # Arrange
        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 123
        mock_properties = MagicMock()
        mock_properties.correlation_id = "test-correlation-id"
        
        message_data = {
            "user_id": 456,
            "group_id": 789,
            "message_text": "Remind me to buy milk tomorrow"
        }
        body = json.dumps(message_data).encode('utf-8')
        
        mock_workflow_result = {
            "user_id": 456,
            "group_id": 789,
            "message_text": "Remind me to buy milk tomorrow",
            "intent": "NEW",
            "db_context": None,
            "extracted_data": {"title": "buy milk", "deadline": "tomorrow"},
            "validation_error": None,
            "needs_human": False,
            "hitl_prompt": None
        }
        
        # Act
        with patch('workers.text_extractor.main.check_hitl_lock', return_value=None) as mock_check_lock:
            with patch('workers.text_extractor.main.app.invoke', return_value=mock_workflow_result) as mock_invoke:
                process_message(mock_channel, mock_method, mock_properties, body)
        
        # Assert
        mock_check_lock.assert_called_once_with(456)
        mock_invoke.assert_called_once()
        
        # Verify state passed to workflow
        call_args = mock_invoke.call_args[0][0]
        assert call_args["user_id"] == 456
        assert call_args["group_id"] == 789
        assert call_args["message_text"] == "Remind me to buy milk tomorrow"
        assert call_args["intent"] is None
        assert call_args["db_context"] is None
        assert call_args["needs_human"] is False
        
        # Verify message acknowledged
        mock_channel.basic_ack.assert_called_once_with(delivery_tag=123)
    
    def test_process_message_with_hitl_lock(self):
        """Test processing a user reply when HITL lock exists."""
        # Arrange
        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 123
        mock_properties = MagicMock()
        mock_properties.correlation_id = "test-correlation-id"
        
        # User's reply message
        message_data = {
            "user_id": 456,
            "message_text": "The deadline is next Friday"
        }
        body = json.dumps(message_data).encode('utf-8')
        
        # Saved state from Redis
        saved_state = {
            "user_id": 456,
            "group_id": 789,
            "message_text": "Remind me to buy milk",
            "intent": "NEW",
            "db_context": "Recent tasks: ...",
            "extracted_data": {"title": "buy milk", "deadline": None},
            "validation_error": "Missing deadline",
            "needs_human": True,
            "hitl_prompt": "When should I remind you?"
        }
        
        mock_workflow_result = {
            "user_id": 456,
            "group_id": 789,
            "message_text": "The deadline is next Friday",
            "intent": "NEW",
            "db_context": "Recent tasks: ...",
            "extracted_data": {"title": "buy milk", "deadline": "next Friday"},
            "validation_error": None,
            "needs_human": False,
            "hitl_prompt": "When should I remind you?"
        }
        
        # Act
        with patch('workers.text_extractor.main.check_hitl_lock', return_value=saved_state) as mock_check_lock:
            with patch('workers.text_extractor.main.app.invoke', return_value=mock_workflow_result) as mock_invoke:
                process_message(mock_channel, mock_method, mock_properties, body)
        
        # Assert
        mock_check_lock.assert_called_once_with(456)
        mock_invoke.assert_called_once()
        
        # Verify state passed to workflow merges saved state with user reply
        call_args = mock_invoke.call_args[0][0]
        assert call_args["user_id"] == 456
        assert call_args["group_id"] == 789
        assert call_args["message_text"] == "The deadline is next Friday"  # User's reply
        assert call_args["intent"] == "NEW"  # From saved state
        assert call_args["db_context"] == "Recent tasks: ..."  # From saved state
        assert call_args["extracted_data"] == {"title": "buy milk", "deadline": None}  # From saved state
        assert call_args["validation_error"] is None  # Cleared for retry
        assert call_args["needs_human"] is False  # Reset for retry
        assert call_args["hitl_prompt"] == "When should I remind you?"  # From saved state
        
        # Verify message acknowledged
        mock_channel.basic_ack.assert_called_once_with(delivery_tag=123)
    
    def test_process_message_hitl_lock_with_missing_fields(self):
        """Test processing when saved state has missing fields."""
        # Arrange
        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 123
        mock_properties = MagicMock()
        mock_properties.correlation_id = "test-correlation-id"
        
        message_data = {
            "user_id": 456,
            "message_text": "Yes, next Friday"
        }
        body = json.dumps(message_data).encode('utf-8')
        
        # Saved state with minimal fields
        saved_state = {
            "user_id": 456,
            "intent": "NEW"
        }
        
        mock_workflow_result = {
            "user_id": 456,
            "intent": "NEW",
            "needs_human": False
        }
        
        # Act
        with patch('workers.text_extractor.main.check_hitl_lock', return_value=saved_state):
            with patch('workers.text_extractor.main.app.invoke', return_value=mock_workflow_result) as mock_invoke:
                process_message(mock_channel, mock_method, mock_properties, body)
        
        # Assert
        call_args = mock_invoke.call_args[0][0]
        assert call_args["user_id"] == 456
        assert call_args["message_text"] == "Yes, next Friday"
        assert call_args["intent"] == "NEW"
        assert call_args["group_id"] is None  # Default when missing
        assert call_args["db_context"] is None  # Default when missing
        assert call_args["validation_error"] is None
        assert call_args["needs_human"] is False
        
        mock_channel.basic_ack.assert_called_once_with(delivery_tag=123)
