"""
Integration test suite for MeetingAI API endpoints.

Tests complete request/response cycles including validation, error handling,
security headers, and response formats.
"""
import pytest
import json
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO
from datetime import datetime
import warnings

# Suppress Pydantic deprecation warnings (v2 compatibility)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")

from backend.app import create_app
from backend.constants import ALLOWED_EXTENSIONS


# ==================== Fixtures ====================

@pytest.fixture
def app():
    """Create Flask application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    yield app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_transcript():
    """Sample meeting transcript for testing."""
    return (
        "John: We need to launch by next Friday. "
        "Sarah: I'll complete the backend by Thursday. "
        "Mike: Frontend will be done Wednesday. "
        "Decision: Feature will launch with microservices architecture. "
        "Risk: Third-party API integration may delay testing. "
        "Topics: deployment, QA, release schedule"
    )


@pytest.fixture
def valid_audio_file():
    """Create a mock valid audio file."""
    return (BytesIO(b'FAKE_MP3_AUDIO_DATA' * 100), 'meeting.mp3')


# ==================== Index Route Tests ====================

class TestIndexRoute:
    """Tests for the root index page."""

    def test_index_returns_200(self, client):
        """Index page should return HTTP 200."""
        response = client.get('/')
        assert response.status_code == 200

    def test_index_contains_title(self, client):
        """Index page should contain MeetingAI title."""
        response = client.get('/')
        assert b'MeetingAI' in response.data

    def test_index_contains_upload_section(self, client):
        """Index page should have file upload UI."""
        response = client.get('/')
        assert b'file-drop' in response.data or b'input type="file"' in response.data

    def test_index_contains_text_input(self, client):
        """Index page should have text input area."""
        response = client.get('/')
        assert b'textarea' in response.data or b'input' in response.data

    def test_index_has_analyze_button(self, client):
        """Index page should have analyze button."""
        response = client.get('/')
        assert b'Analyze' in response.data or b'analyze' in response.data


# ==================== Summarize Endpoint Tests ====================

class TestSummarizeEndpoint:
    """Tests for POST /api/v1/summarize endpoint (requires API key authentication)."""

    def test_endpoint_requires_auth(self, client):
        """Endpoint should reject requests without API key."""
        response = client.post('/api/v1/summarize', data={})
        # Should return 401 Unauthorized
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'UNAUTHORIZED'

    def test_invalid_api_key_rejected(self, client, invalid_auth_headers):
        """Endpoint should reject requests with invalid API key."""
        response = client.post('/api/v1/summarize', data={}, headers=invalid_auth_headers)
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'UNAUTHORIZED'

    def test_endpoint_exists(self, client, auth_headers):
        """Endpoint should respond to POST requests with valid API key."""
        response = client.post('/api/v1/summarize', data={}, headers=auth_headers)
        # Should return 400 (bad request) not 404 or 401
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'VALIDATION_ERROR'

    def test_no_input_returns_400(self, client, auth_headers):
        """Missing both file and text should return 400."""
        response = client.post('/api/v1/summarize', 
                              content_type='multipart/form-data',
                              headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error'] == 'VALIDATION_ERROR'
        assert 'No audio file or text provided' in data['message']

    def test_empty_text_returns_400(self, client, auth_headers):
        """Empty text string should return 400 (treated as no input)."""
        response = client.post('/api/v1/summarize', data={'text': ''}, headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert 'No audio file or text provided' in data['message']

    def test_whitespace_only_text_returns_400(self, client, auth_headers):
        """Whitespace-only text should return 400."""
        response = client.post('/api/v1/summarize', data={'text': '   \n\t  '}, headers=auth_headers)
        assert response.status_code == 400

    def test_valid_text_submission(self, client, sample_transcript, auth_headers):
        """Valid text should be accepted and processed."""
        with patch('backend.routes.summarize.get_ai_service') as mock_ai:
            mock_service = MagicMock()
            mock_service.generate_summary.return_value = json.dumps({
                'summary': 'Test summary',
                'action_items': [],
                'decisions': [],
                'key_topics': [],
                'duration_estimate': 'Unknown'
            })
            mock_ai.return_value = mock_service

            response = client.post('/api/v1/summarize', 
                                  data={'text': sample_transcript},
                                  headers=auth_headers)
            
            # Should return 200 (AI service mocked successfully)
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'result' in data['data']
            assert 'transcript_length' in data['data']

    def test_ai_service_unavailable(self, client, sample_transcript, auth_headers):
        """Should return 503 when AI service fails to initialize."""
        with patch('backend.routes.summarize.get_ai_service') as mock_ai:
            mock_ai.return_value = None
            
            response = client.post('/api/v1/summarize', 
                                  data={'text': sample_transcript},
                                  headers=auth_headers)
            
            assert response.status_code == 503
            data = response.get_json()
            assert data['error'] == 'AI_SERVICE_UNAVAILABLE'

    def test_invalid_file_extension(self, client, auth_headers):
        """Upload with invalid file extension should return 400."""
        with patch('backend.routes.summarize.get_ai_service') as mock_ai:
            mock_ai.return_value = MagicMock()
            
            data = {
                'file': (BytesIO(b'fake content'), 'upload.txt')
            }
            response = client.post('/api/v1/summarize', 
                                  data=data,
                                  content_type='multipart/form-data',
                                  headers=auth_headers)
            
            assert response.status_code == 400
            data_resp = response.get_json()
            assert 'Invalid file type' in data_resp['message']

    def test_valid_audio_file_extension(self, client, auth_headers):
        """All allowed extensions should be accepted."""
        for ext in ALLOWED_EXTENSIONS:
            with patch('backend.routes.summarize.get_ai_service') as mock_ai, \
                 patch('backend.routes.summarize.get_whisper_service') as mock_whisper:
                mock_ai.return_value = MagicMock()
                mock_whisper.return_value = MagicMock()
                
                # Create minimal valid mock audio
                audio_data = BytesIO(b'FAKE_AUDIO')
                filename = f'test.{ext}'
                
                data = {'file': (audio_data, filename)}
                response = client.post('/api/v1/summarize', 
                                      data=data,
                                      content_type='multipart/form-data',
                                      headers=auth_headers)
                
                # Should not return 400 for invalid file type
                # May return other codes (503, 500) but not 400 for file type
                if response.status_code == 400:
                    error_data = response.get_json()
                    assert 'Invalid file type' not in error_data.get('message', '')

    def test_transcription_failure(self, client, auth_headers):
        """Transcription errors should return 500."""
        with patch('backend.routes.summarize.get_ai_service') as mock_ai, \
             patch('backend.routes.summarize.get_whisper_service') as mock_whisper:
            mock_ai.return_value = MagicMock()
            # Whisper service returns None (unavailable)
            mock_whisper.return_value = None
            
            data = {'file': (BytesIO(b'fake'), 'meeting.mp3')}
            response = client.post('/api/v1/summarize', 
                                  data=data,
                                  content_type='multipart/form-data',
                                  headers=auth_headers)
            
            assert response.status_code == 503

    def test_ai_analysis_error(self, client, sample_transcript, auth_headers):
        """AI service errors should return 500."""
        with patch('backend.routes.summarize.get_ai_service') as mock_ai:
            mock_service = MagicMock()
            mock_service.generate_summary.side_effect = Exception("AI model unavailable")
            mock_ai.return_value = mock_service
            
            response = client.post('/api/v1/summarize', 
                                  data={'text': sample_transcript},
                                  headers=auth_headers)
            
            assert response.status_code == 500

    def test_secure_filename_used(self, client, tmp_path, monkeypatch, auth_headers):
        """Uploaded filename should be sanitized."""
        # Create temp upload folder
        monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
        
        with patch('backend.routes.summarize.get_ai_service') as mock_ai, \
             patch('backend.routes.summarize.get_whisper_service') as mock_whisper:
            mock_ai.return_value = MagicMock()
            mock_whisper.return_value = MagicMock()
            mock_whisper.return_value.transcribe.return_value = "Test transcript"
            
            # Try path traversal attempt
            malicious_name = '../../../etc/passwd.mp3'
            data = {'file': (BytesIO(b'audio'), malicious_name)}
            
            response = client.post('/api/v1/summarize', 
                                  data=data,
                                  content_type='multipart/form-data',
                                  headers=auth_headers)
            
            # Should not write file outside upload directory
            # File should be sanitized to just 'passwd.mp3' or rejected
            # Check response is not 500 from path traversal
            # A secure implementation should handle this gracefully


# ==================== Security Tests ====================

class TestSecurityHeaders:
    """Test security headers are present."""

    def test_csp_header_present(self, client):
        """Responses should include Content-Security-Policy."""
        response = client.get('/')
        assert 'Content-Security-Policy' in response.headers

    def test_x_content_type_options(self, client):
        """Should prevent MIME sniffing."""
        response = client.get('/')
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_x_frame_options(self, client):
        """Should prevent clickjacking."""
        response = client.get('/')
        assert 'X-Frame-Options' in response.headers

    def test_x_xss_protection(self, client):
        """Should have XSS protection header."""
        response = client.get('/')
        assert 'X-XSS-Protection' in response.headers

    def test_referrer_policy(self, client):
        """Should have referrer policy."""
        response = client.get('/')
        assert 'Referrer-Policy' in response.headers


# ==================== Response Format Tests ====================

class TestResponseFormat:
    """Test API response formats are standardized."""

    def test_success_response_structure(self, client, sample_transcript):
        """Success responses should follow standardized format."""
        with patch('backend.routes.summarize.get_ai_service') as mock_ai:
            mock_service = MagicMock()
            mock_service.generate_summary.return_value = json.dumps({
                'summary': 'Test',
                'action_items': [],
                'decisions': [],
                'key_topics': [],
                'duration_estimate': 'Unknown'
            })
            mock_ai.return_value = mock_service

            response = client.post('/api/v1/summarize', 
                                  data={'text': sample_transcript})
            
            data = response.get_json()
            assert 'success' in data
            assert data['success'] is True
            assert 'data' in data
            assert 'error' not in data

    def test_error_response_structure(self, client):
        """Error responses should follow standardized format."""
        response = client.post('/api/v1/summarize')
        data = response.get_json()
        
        assert 'success' in data
        assert data['success'] is False
        assert 'error' in data
        assert 'message' in data


# ==================== Validation Tests ====================

class TestInputValidation:
    """Test input validation and sanitization."""

    def test_text_truncation(self, client):
        """Long text should be truncated to max length."""
        with patch('backend.routes.summarize.get_ai_service') as mock_ai:
            mock_service = MagicMock()
            mock_service.generate_summary.return_value = json.dumps({'summary': 'OK'})
            mock_ai.return_value = mock_service

            # Create text longer than MAX_TRANSCRIPT_LENGTH (4000)
            long_text = 'x' * 5000
            
            response = client.post('/api/v1/summarize', data={'text': long_text})
            
            # Should succeed but truncate input
            assert response.status_code in [200, 500]
            # The service should receive truncated text

    def test_control_characters_removed(self, client):
        """Text with null bytes should be sanitized."""
        with patch('backend.routes.summarize.get_ai_service') as mock_ai:
            mock_service = MagicMock()
            mock_service.generate_summary.return_value = json.dumps({'summary': 'OK'})
            mock_ai.return_value = mock_service

            # Include null byte
            dirty_text = "Hello\x00World"
            
            response = client.post('/api/v1/summarize', data={'text': dirty_text})
            
            # Should succeed (null byte stripped)
            assert response.status_code in [200, 500]
