"""
Unit tests for configuration management and validation.

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
"""
import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError
from workers.text_extractor.core.config import Settings, load_settings


class TestSettingsValidation:
    """Test configuration validation and defaults."""
    
    def test_required_fields_present(self):
        """Test that all required fields are validated."""
        # Arrange: Set all required environment variables
        env_vars = {
            "GOOGLE_API_KEY": "test_key",
            "RABBITMQ_URL": "amqp://test",
            "REDIS_URL": "redis://test",
            "DATABASE_URL": "postgresql://test",
            "TELEGRAM_BOT_TOKEN": "test_token"
        }
        
        # Act & Assert: Should create settings without error
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.GOOGLE_API_KEY == "test_key"
            assert settings.TELEGRAM_BOT_TOKEN == "test_token"
    
    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise validation error."""
        # Arrange: Missing TELEGRAM_BOT_TOKEN
        env_vars = {
            "GOOGLE_API_KEY": "test_key",
            "RABBITMQ_URL": "amqp://test",
            "REDIS_URL": "redis://test",
            "DATABASE_URL": "postgresql://test"
        }
        
        # Act & Assert: Should raise ValidationError
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "TELEGRAM_BOT_TOKEN" in str(exc_info.value)
    
    def test_optional_fields_have_defaults(self):
        """Test that optional fields use default values."""
        # Arrange: Only required fields
        env_vars = {
            "GOOGLE_API_KEY": "test_key",
            "RABBITMQ_URL": "amqp://test",
            "REDIS_URL": "redis://test",
            "DATABASE_URL": "postgresql://test",
            "TELEGRAM_BOT_TOKEN": "test_token"
        }
        
        # Act
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
        
        # Assert: Check defaults
        assert settings.PROMETHEUS_PORT == 8001
        assert settings.LOG_LEVEL == "INFO"
        assert settings.DB_POOL_MIN_SIZE == 5
        assert settings.DB_POOL_MAX_SIZE == 20
        assert settings.RABBITMQ_PREFETCH_COUNT == 10
        assert settings.RABBITMQ_POOL_SIZE == 10
        assert settings.RABBITMQ_MAX_RETRIES == 3
        assert settings.RABBITMQ_INITIAL_RETRY_DELAY == 5
        assert settings.TELEGRAM_MAX_RETRIES == 2
        assert settings.TELEGRAM_RETRY_DELAY == 1
        assert settings.HITL_LOCK_TTL == 3600
    
    def test_log_level_validation_valid(self):
        """Test LOG_LEVEL validation accepts valid levels."""
        # Arrange
        env_vars = {
            "GOOGLE_API_KEY": "test_key",
            "RABBITMQ_URL": "amqp://test",
            "REDIS_URL": "redis://test",
            "DATABASE_URL": "postgresql://test",
            "TELEGRAM_BOT_TOKEN": "test_token",
            "LOG_LEVEL": "debug"  # lowercase should be converted to uppercase
        }
        
        # Act
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
        
        # Assert
        assert settings.LOG_LEVEL == "DEBUG"
    
    def test_log_level_validation_invalid(self):
        """Test LOG_LEVEL validation rejects invalid levels."""
        # Arrange
        env_vars = {
            "GOOGLE_API_KEY": "test_key",
            "RABBITMQ_URL": "amqp://test",
            "REDIS_URL": "redis://test",
            "DATABASE_URL": "postgresql://test",
            "TELEGRAM_BOT_TOKEN": "test_token",
            "LOG_LEVEL": "INVALID"
        }
        
        # Act & Assert
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "LOG_LEVEL must be one of" in str(exc_info.value)
    
    def test_prometheus_port_validation_valid(self):
        """Test PROMETHEUS_PORT validation accepts valid port range."""
        # Arrange
        env_vars = {
            "GOOGLE_API_KEY": "test_key",
            "RABBITMQ_URL": "amqp://test",
            "REDIS_URL": "redis://test",
            "DATABASE_URL": "postgresql://test",
            "TELEGRAM_BOT_TOKEN": "test_token",
            "PROMETHEUS_PORT": "9090"
        }
        
        # Act
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
        
        # Assert
        assert settings.PROMETHEUS_PORT == 9090
    
    def test_prometheus_port_validation_invalid_low(self):
        """Test PROMETHEUS_PORT validation rejects ports below 1024."""
        # Arrange
        env_vars = {
            "GOOGLE_API_KEY": "test_key",
            "RABBITMQ_URL": "amqp://test",
            "REDIS_URL": "redis://test",
            "DATABASE_URL": "postgresql://test",
            "TELEGRAM_BOT_TOKEN": "test_token",
            "PROMETHEUS_PORT": "80"
        }
        
        # Act & Assert
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must be between 1024 and 65535" in str(exc_info.value)
    
    def test_prometheus_port_validation_invalid_high(self):
        """Test PROMETHEUS_PORT validation rejects ports above 65535."""
        # Arrange
        env_vars = {
            "GOOGLE_API_KEY": "test_key",
            "RABBITMQ_URL": "amqp://test",
            "REDIS_URL": "redis://test",
            "DATABASE_URL": "postgresql://test",
            "TELEGRAM_BOT_TOKEN": "test_token",
            "PROMETHEUS_PORT": "70000"
        }
        
        # Act & Assert
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must be between 1024 and 65535" in str(exc_info.value)
    
    def test_connection_pool_defaults(self):
        """Test connection pool configuration has correct defaults."""
        # Arrange
        env_vars = {
            "GOOGLE_API_KEY": "test_key",
            "RABBITMQ_URL": "amqp://test",
            "REDIS_URL": "redis://test",
            "DATABASE_URL": "postgresql://test",
            "TELEGRAM_BOT_TOKEN": "test_token"
        }
        
        # Act
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
        
        # Assert: Validates requirement 10.6
        assert settings.RABBITMQ_PREFETCH_COUNT == 10
        assert settings.RABBITMQ_POOL_SIZE == 10
    
    def test_load_settings_exits_on_validation_error(self):
        """Test load_settings exits with non-zero status on validation error."""
        # Arrange: Missing required field
        env_vars = {
            "GOOGLE_API_KEY": "test_key"
        }
        
        # Act & Assert: Should exit with non-zero status
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                load_settings()
            assert exc_info.value.code == 1
