"""
Unit tests for backend.routes.summarize helper functions.

Tests validation, sanitization, truncation, and response helpers.
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.routes.summarize import (
    validate_file,
    validate_request_size,
    save_uploaded_file,
    sanitize_text,
    truncate_text_content,
    json_success,
    json_error
)
from backend.exceptions import ValidationError
from werkzeug.datastructures import FileStorage


# ==================== validate_file Tests ====================

class TestValidateFile:
    """Tests for file validation function."""

    def test_validate_file_success(self):
        """Valid file with allowed extension passes."""
        mock_file = MagicMock(spec=FileStorage)
        mock_file.filename = 'meeting.mp3'
        
        # Should not raise
        validate_file(mock_file)

    def test_validate_file_no_file(self):
        """Missing file raises ValidationError."""
        with pytest.raises(ValidationError, match="No file provided"):
            validate_file(None)

    def test_validate_file_empty_filename(self):
        """Empty filename raises ValidationError."""
        mock_file = MagicMock(spec=FileStorage)
        mock_file.filename = ''
        
        with pytest.raises(ValidationError, match="Empty filename"):
            validate_file(mock_file)

    def test_validate_file_invalid_extension(self):
        """Disallowed file extension raises ValidationError."""
        mock_file = MagicMock(spec=FileStorage)
        mock_file.filename = 'document.pdf'
        
        with pytest.raises(ValidationError, match="Invalid file type"):
            validate_file(mock_file)

    def test_validate_file_case_insensitive(self):
        """File extension check is case-insensitive."""
        mock_file = MagicMock(spec=FileStorage)
        mock_file.filename = 'meeting.MP3'
        validate_file(mock_file)  # Should not raise

        mock_file.filename = 'meeting.Mp4'
        validate_file(mock_file)  # Should not raise


# ==================== validate_request_size Tests ====================

class TestValidateRequestSize:
    """Tests for request size validation."""

    def test_validate_request_size_within_limit(self, app):
        """Request within limit passes validation."""
        size = 100  # 100 bytes
        with app.test_request_context('/', data=b'x' * size, content_length=size):
            # Should not raise
            validate_request_size()

    def test_validate_request_size_no_content_length(self, app):
        """When content_length is None, validation passes."""
        with app.test_request_context('/'):
            # request.content_length will be None
            validate_request_size()  # Should not raise


# ==================== save_uploaded_file Tests ====================

class TestSaveUploadedFile:
    """Tests for file saving utility."""

    def test_save_uploaded_file_creates_directory(self, tmp_path):
        """Upload directory is created if missing."""
        upload_dir = tmp_path / "new_uploads"
        mock_file = MagicMock()
        mock_file.filename = 'test.mp3'
        
        filepath = save_uploaded_file(str(upload_dir), mock_file)
        
        assert upload_dir.exists()
        assert filepath == str(upload_dir / 'test.mp3')

    def test_save_uploaded_file_calls_save(self, tmp_path):
        """File.save is called with correct path."""
        upload_dir = tmp_path / "uploads"
        mock_file = MagicMock()
        mock_file.filename = 'audio.mp3'
        
        filepath = save_uploaded_file(str(upload_dir), mock_file)
        
        expected_path = str(upload_dir / 'audio.mp3')
        assert filepath == expected_path
        mock_file.save.assert_called_once_with(expected_path)

    def test_save_uploaded_file_with_secure_filename(self, tmp_path):
        """Filename is sanitized (assumes safe filename passed from route)."""
        upload_dir = tmp_path / "uploads"
        mock_file = MagicMock()
        mock_file.filename = 'normal_name.wav'
        
        filepath = save_uploaded_file(str(upload_dir), mock_file)
        filename = Path(filepath).name
        assert filename == 'normal_name.wav'


# ==================== sanitize_text Tests ====================

class TestSanitizeText:
    """Tests for text sanitization."""

    def test_removes_null_bytes(self):
        """Null bytes are removed."""
        dirty = "Hello\x00World"
        clean = sanitize_text(dirty)
        assert '\x00' not in clean
        assert clean == "HelloWorld"

    def test_removes_control_characters(self):
        """Various control characters are stripped."""
        dirty = "Text\x01\x02\x03more\x1Fend"
        clean = sanitize_text(dirty)
        assert clean == "Textmoreend"

    def test_preserves_whitespace(self):
        """Spaces, newlines, tabs are preserved."""
        text = "Hello\nWorld\t!"
        clean = sanitize_text(text)
        assert clean == "Hello\nWorld\t!"

    def test_strips_leading_trailing(self):
        """Leading/trailing whitespace is stripped."""
        text = "   Hello World   "
        clean = sanitize_text(text)
        assert clean == "Hello World"

    def test_empty_string_remains_empty(self):
        """Empty string returns empty."""
        assert sanitize_text("") == ""


# ==================== truncate_text_content Tests ====================

class TestTruncateTextContent:
    """Tests for text truncation."""

    def test_text_shorter_than_limit_unchanged(self):
        """Text within limit is not modified."""
        text = "Short text"
        result = truncate_text_content(text, 100)
        assert result == text

    def test_text_longer_than_limit_truncated(self):
        """Text exceeding limit is truncated."""
        text = "x" * 200
        result = truncate_text_content(text, 100)
        assert len(result) == 100
        assert result == "x" * 100

    def test_exact_limit(self):
        """Text exactly at limit remains unchanged."""
        text = "y" * 50
        result = truncate_text_content(text, 50)
        assert result == text


# ==================== JSON Response Helpers Tests ====================

class TestJsonResponseHelpers:
    """Tests for json_success and json_error helpers."""

    def test_json_success_structure(self, app):
        """json_success returns correct structure."""
        with app.app_context():
            response, status = json_success({'key': 'value'}, 201)
            
            assert status == 201
            assert response.json == {'success': True, 'data': {'key': 'value'}}

    def test_json_error_structure(self, app):
        """json_error returns correct structure."""
        with app.app_context():
            response, status = json_error('Something broke', 'ERROR_CODE', 400)
            
            assert status == 400
            assert response.json == {
                'success': False,
                'error': 'ERROR_CODE',
                'message': 'Something broke'
            }

    def test_json_success_default_status(self, app):
        """json_success uses 200 by default."""
        with app.app_context():
            response, status = json_success({})
            assert status == 200
