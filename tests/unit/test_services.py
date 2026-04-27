"""
Unit tests for backend services (AIService, WhisperService).

Tests cover initialization, core functionality, error handling, and edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from backend.services.ai_service import AIService, AIServiceError
from backend.services.whisper_service import WhisperService, allowed_file
from backend.config import config


# ==================== AIService Tests ====================

class TestAIService:
    """Test suite for AIService class."""

    def test_init_success(self, monkeypatch):
        """Test successful initialization with valid API key."""
        monkeypatch.setenv('GROQ_API_KEY', 'test_key_123')
        
        service = AIService()
        
        assert service.model == config.ai_model
        assert service.temperature == config.ai_temperature
        assert service.max_tokens == config.ai_max_tokens

    def test_init_missing_api_key(self, monkeypatch):
        """Test initialization fails when GROQ_API_KEY is missing."""
        monkeypatch.delenv('GROQ_API_KEY', raising=False)
        
        with pytest.raises(AIServiceError, match="GROQ_API_KEY not found"):
            AIService()

    def test_generate_summary_success(self, monkeypatch):
        """Test successful summary generation."""
        monkeypatch.setenv('GROQ_API_KEY', 'test_key')
        
        # Mock the Groq client
        with patch('backend.services.ai_service.Groq') as mock_groq:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Test summary output"
            mock_client.chat.completions.create.return_value = mock_response
            mock_groq.return_value = mock_client
            
            service = AIService()
            result = service.generate_summary("Test transcript text")
            
            assert result == "Test summary output"
            mock_client.chat.completions.create.assert_called_once()

    def test_generate_summary_empty_text(self, monkeypatch):
        """Test summary generation with empty text."""
        monkeypatch.setenv('GROQ_API_KEY', 'test_key')
        
        service = AIService()
        
        with pytest.raises(ValueError, match="Empty text"):
            service.generate_summary("")

    def test_generate_summary_whitespace_only(self, monkeypatch):
        """Test summary generation with whitespace-only text."""
        monkeypatch.setenv('GROQ_API_KEY', 'test_key')
        
        service = AIService()
        
        with pytest.raises(ValueError, match="Empty text"):
            service.generate_summary("   \n\t  ")

    def test_generate_summary_api_error(self, monkeypatch):
        """Test summary generation handles Groq API errors."""
        monkeypatch.setenv('GROQ_API_KEY', 'test_key')
        
        with patch('backend.services.ai_service.Groq') as mock_groq:
            mock_client = MagicMock()
            from groq import GroqError
            mock_client.chat.completions.create.side_effect = GroqError("API error")
            mock_groq.return_value = mock_client
            
            service = AIService()
            
            with pytest.raises(AIServiceError, match="Groq API error"):
                service.generate_summary("Test text")

    def test_generate_summary_invalid_response_format(self, monkeypatch):
        """Test handling of malformed API response."""
        monkeypatch.setenv('GROQ_API_KEY', 'test_key')
        
        with patch('backend.services.ai_service.Groq') as mock_groq:
            mock_client = MagicMock()
            mock_response = MagicMock()
            # Simulate missing .choices attribute
            del mock_response.choices
            mock_client.chat.completions.create.return_value = mock_response
            mock_groq.return_value = mock_client
            
            service = AIService()
            
            with pytest.raises(AIServiceError, match="Unexpected response format"):
                service.generate_summary("Test text")

    def test_generate_summary_with_custom_prompt(self, monkeypatch):
        """Test summary generation with custom prompt."""
        monkeypatch.setenv('GROQ_API_KEY', 'test_key')
        
        with patch('backend.services.ai_service.Groq') as mock_groq:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Summary"
            mock_client.chat.completions.create.return_value = mock_response
            mock_groq.return_value = mock_client
            
            service = AIService()
            custom_prompt = "Summarize in 3 sentences:"
            result = service.generate_summary("Test text", prompt=custom_prompt)
            
            # Verify custom prompt was used
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args[1]['messages'][0]['content']
            assert custom_prompt in messages
            assert "Test text" in messages


# ==================== WhisperService Tests ====================

class TestWhisperService:
    """Test suite for WhisperService class."""

    @patch('backend.services.whisper_service.whisper.load_model')
    def test_init_success(self, mock_load_model):
        """Test successful model loading."""
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        
        service = WhisperService(model_size="base")
        
        assert service.model == mock_model
        assert service.model_size == "base"
        mock_load_model.assert_called_once_with("base")

    @patch('backend.services.whisper_service.whisper.load_model')
    def test_init_different_models(self, mock_load_model):
        """Test initialization with different model sizes."""
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        
        for model_size in ["tiny", "base", "small", "medium", "large"]:
            service = WhisperService(model_size=model_size)
            assert service.model_size == model_size

    @patch('backend.services.whisper_service.whisper.load_model')
    def test_transcribe_success(self, mock_load_model):
        """Test successful audio transcription."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Transcribed text content"}
        mock_load_model.return_value = mock_model
        
        service = WhisperService()
        result = service.transcribe("/fake/path/audio.mp3")
        
        assert result == "Transcribed text content"
        mock_model.transcribe.assert_called_once_with("/fake/path/audio.mp3")

    @patch('backend.services.whisper_service.whisper.load_model')
    def test_transcribe_empty_result(self, mock_load_model):
        """Test transcription with empty result returns empty string."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "   "}
        mock_load_model.return_value = mock_model
        
        service = WhisperService()
        result = service.transcribe("/fake/path/audio.mp3")
        
        # Service returns empty string, error handling is done at route level
        assert result == ""

    @patch('backend.services.whisper_service.whisper.load_model')
    def test_transcribe_file_not_found(self, mock_load_model):
        """Test transcription with missing file."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = FileNotFoundError("File not found")
        mock_load_model.return_value = mock_model
        
        service = WhisperService()
        
        with pytest.raises(Exception, match="Audio file not found"):
            service.transcribe("/nonexistent/file.mp3")

    @patch('backend.services.whisper_service.whisper.load_model')
    def test_transcribe_general_error(self, mock_load_model):
        """Test transcription handles unexpected errors."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = ValueError("Invalid audio format")
        mock_load_model.return_value = mock_model
        
        service = WhisperService()
        
        with pytest.raises(Exception, match="Transcription failed"):
            service.transcribe("/fake/path/audio.mp3")


# ==================== allowed_file Tests ====================

class TestAllowedFile:
    """Test suite for file extension validation."""

    def test_allowed_extensions(self):
        """Test all allowed file extensions are accepted."""
        allowed = ['mp3', 'mp4', 'wav', 'm4a']
        for ext in allowed:
            assert allowed_file(f"test.{ext}") is True

    def test_disallowed_extensions(self):
        """Test disallowed file extensions are rejected."""
        disallowed = ['txt', 'pdf', 'doc', 'jpg', 'png', 'avi', 'mov', 'mkv']
        for ext in disallowed:
            assert allowed_file(f"test.{ext}") is False

    def test_case_insensitive(self):
        """Test file extension checking is case-insensitive."""
        assert allowed_file("test.MP3") is True
        assert allowed_file("test.WAV") is True
        assert allowed_file("test.Mp4") is True
        assert allowed_file("test.M4A") is True

    def test_empty_filename(self):
        """Test empty filename returns False."""
        assert allowed_file("") is False
        assert allowed_file(None) is False

    def test_no_extension(self):
        """Test filename without extension returns False."""
        assert allowed_file("testfile") is False
        assert allowed_file("test.") is False

    def test_multiple_dots(self):
        """Test filename with multiple dots uses last extension."""
        assert allowed_file("my.meeting.recording.mp3") is True
        assert allowed_file("my.meeting.txt") is False


# ==================== Config Tests ====================

class TestConfig:
    """Test suite for Config class."""

    def test_singleton_pattern(self):
        """Test config is a singleton."""
        from backend.config import Config
        instance1 = Config()
        instance2 = Config()
        assert instance1 is instance2

    def test_default_values(self):
        """Test default configuration values are loaded."""
        assert config.app_name == 'MeetingAI'
        assert config.debug is False
        assert config.host == '0.0.0.0'
        assert config.port == 7860

    def test_upload_settings(self):
        """Test upload-related configuration."""
        assert config.upload_folder == 'storage/uploads'
        assert config.max_upload_size == 25 * 1024 * 1024  # 25MB in bytes
        assert isinstance(config.allowed_extensions, list)
        assert 'mp3' in config.allowed_extensions

    def test_transcription_settings(self):
        """Test transcription configuration."""
        assert config.max_transcript_length == 4000
        assert config.whisper_model in ['tiny', 'base', 'small', 'medium', 'large']

    def test_ai_settings(self):
        """Test AI service configuration."""
        assert config.ai_model is not None
        assert 0.0 <= config.ai_temperature <= 1.0
        assert config.ai_max_tokens > 0

    def test_get_method(self):
        """Test the config.get() method with dot notation."""
        assert config.get('app.name') == 'MeetingAI'
        assert config.get('app.port') == 7860
        assert config.get('upload.max_size_mb') == 25
        assert config.get('nonexistent.key', 'default') == 'default'

    def test_env_override(self, monkeypatch):
        """Test environment variables override defaults."""
        monkeypatch.setenv('PORT', '8080')
        monkeypatch.setenv('DEBUG', 'true')
        
        # Reload config to pick up env changes
        from backend.config import Config
        Config._instance = None
        new_config = Config()
        
        assert new_config.port == 8080
        assert new_config.debug is True
