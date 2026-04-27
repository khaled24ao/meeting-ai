"""
Unit tests for backend configuration.

Tests Config singleton, environment variable overrides, and property accessors.
"""
import pytest
import os
from unittest.mock import patch

from backend.config import Config, config
from backend.constants import ALLOWED_EXTENSIONS


class TestConfigSingleton:
    """Test Config singleton pattern."""

    def test_config_is_singleton(self):
        """Multiple instantiations return same object."""
        config1 = Config()
        config2 = Config()
        assert config1 is config2

    def test_config_instance_caching(self):
        """Instance is cached across module imports."""
        from backend.config import config
        assert config is not None
        assert isinstance(config, Config)


class TestDefaultConfiguration:
    """Test default configuration values."""

    def test_app_defaults(self):
        """Application defaults are set correctly."""
        assert config.app_name == 'MeetingAI'
        assert config.debug is False
        assert config.host == '0.0.0.0'
        assert config.port == 7860

    def test_upload_defaults(self):
        """Upload configuration defaults."""
        assert config.upload_folder == 'storage/uploads'
        assert config.max_upload_size == 25 * 1024 * 1024  # 25 MB in bytes
        assert isinstance(config.allowed_extensions, list)
        assert len(config.allowed_extensions) > 0

    def test_transcription_defaults(self):
        """Transcription configuration defaults."""
        assert config.max_transcript_length == 4000
        assert config.whisper_model in ['tiny', 'base', 'small', 'medium', 'large']

    def test_ai_defaults(self):
        """AI configuration defaults."""
        assert config.ai_model is not None
        assert isinstance(config.ai_model, str)
        assert 0.0 <= config.ai_temperature <= 1.0
        assert config.ai_max_tokens > 0


class TestEnvironmentOverrides:
    """Test environment variable overrides."""

    def test_port_override(self, monkeypatch):
        """PORT environment variable overrides default."""
        monkeypatch.setenv('PORT', '8080')
        Config._instance = None
        new_config = Config()
        assert new_config.port == 8080

    def test_debug_override(self, monkeypatch):
        """DEBUG environment variable overrides default."""
        monkeypatch.setenv('DEBUG', 'true')
        Config._instance = None
        new_config = Config()
        assert new_config.debug is True

    def test_host_override(self, monkeypatch):
        """HOST environment variable overrides default."""
        monkeypatch.setenv('HOST', '127.0.0.1')
        Config._instance = None
        new_config = Config()
        assert new_config.host == '127.0.0.1'

    def test_app_name_override(self, monkeypatch):
        """APP_NAME environment variable overrides default."""
        monkeypatch.setenv('APP_NAME', 'MyMeetingAI')
        Config._instance = None
        new_config = Config()
        assert new_config.app_name == 'MyMeetingAI'

    def test_upload_folder_override(self, monkeypatch, tmp_path):
        """UPLOAD_FOLDER environment variable overrides default."""
        test_path = str(tmp_path / "uploads")
        monkeypatch.setenv('UPLOAD_FOLDER', test_path)
        Config._instance = None
        new_config = Config()
        assert new_config.upload_folder == test_path

    def test_max_upload_size_override(self, monkeypatch):
        """MAX_UPLOAD_SIZE_MB environment variable overrides default."""
        monkeypatch.setenv('MAX_UPLOAD_SIZE_MB', '50')
        Config._instance = None
        new_config = Config()
        assert new_config.max_upload_size == 50 * 1024 * 1024

    def test_allowed_extensions_override(self, monkeypatch):
        """ALLOWED_EXTENSIONS environment variable overrides default."""
        monkeypatch.setenv('ALLOWED_EXTENSIONS', 'mp3,wav,flac')
        Config._instance = None
        new_config = Config()
        assert new_config.allowed_extensions == ['mp3', 'wav', 'flac']

    def test_whisper_model_override(self, monkeypatch):
        """WHISPER_MODEL environment variable overrides default."""
        monkeypatch.setenv('WHISPER_MODEL', 'base')
        Config._instance = None
        new_config = Config()
        assert new_config.whisper_model == 'base'

    def test_ai_model_override(self, monkeypatch):
        """AI_MODEL environment variable overrides default."""
        monkeypatch.setenv('AI_MODEL', 'llama-3.2-70b')
        Config._instance = None
        new_config = Config()
        assert new_config.ai_model == 'llama-3.2-70b'

    def test_ai_temperature_override(self, monkeypatch):
        """AI_TEMPERATURE environment variable overrides default."""
        monkeypatch.setenv('AI_TEMPERATURE', '0.8')
        Config._instance = None
        new_config = Config()
        assert new_config.ai_temperature == 0.8

    def test_ai_max_tokens_override(self, monkeypatch):
        """AI_MAX_TOKENS environment variable overrides default."""
        monkeypatch.setenv('AI_MAX_TOKENS', '2048')
        Config._instance = None
        new_config = Config()
        assert new_config.ai_max_tokens == 2048

    def test_log_level_override(self, monkeypatch):
        """LOG_LEVEL environment variable overrides default."""
        monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
        Config._instance = None
        new_config = Config()
        assert new_config.get('logging.level') == 'DEBUG'


class TestGetMethod:
    """Test Config.get() method with dot notation."""

    def test_get_existing_keys(self):
        """get() returns values for existing keys."""
        assert config.get('app.name') == 'MeetingAI'
        assert config.get('app.port') == 7860
        assert config.get('upload.max_size_mb') == 25
        assert config.get('transcription.whisper_model') == config.whisper_model
        assert config.get('ai.temperature') == config.ai_temperature

    def test_get_nonexistent_key_returns_default(self):
        """get() returns default for non-existent keys."""
        assert config.get('nonexistent.key') is None
        assert config.get('nonexistent.key', 'fallback') == 'fallback'

    def test_get_with_invalid_key_type(self):
        """get() handles invalid key gracefully."""
        # Empty key should return None
        assert config.get('', 'default') == 'default'


class TestConfigValidation:
    """Test configuration values are valid."""

    def test_port_in_valid_range(self):
        """Port number is in valid range."""
        assert 1 <= config.port <= 65535

    def test_max_upload_size_positive(self):
        """Max upload size is positive."""
        assert config.max_upload_size > 0

    def test_allowed_extensions_nonempty(self):
        """Allowed extensions list is not empty."""
        assert len(config.allowed_extensions) > 0

    def test_all_extensions_lowercase(self):
        """All extensions are lowercase."""
        for ext in config.allowed_extensions:
            assert ext == ext.lower()
            assert '.' not in ext  # Extensions without dot

    def test_transcription_max_length_positive(self):
        """Max transcript length is positive."""
        assert config.max_transcript_length > 0

    def test_temperature_in_range(self):
        """AI temperature is between 0 and 1."""
        assert 0.0 <= config.ai_temperature <= 1.0

    def test_ai_model_is_known(self):
        """AI model is one of the known models."""
        known_models = ['llama3-8b-8192', 'llama-3.1-8b-instant']
        assert config.ai_model in known_models


class TestProperties:
    """Test config property accessors."""

    def test_max_upload_size_returns_bytes(self):
        """max_upload_size returns bytes, not MB."""
        size_bytes = config.max_upload_size
        size_mb = config.get('upload.max_size_mb')
        assert size_bytes == size_mb * 1024 * 1024

    def test_upload_folder_exists_in_defaults(self):
        """upload_folder is set to a reasonable default."""
        assert config.upload_folder == 'storage/uploads'

    def test_configuration_immutability(self):
        """Properties return consistent values."""
        port1 = config.port
        port2 = config.port
        assert port1 == port2