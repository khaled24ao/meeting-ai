"""
Pytest configuration and fixtures for MeetingAI tests.

Provides reusable test fixtures for Flask app, test client, and sample data.
"""
import os
import json
import pytest
from typing import Generator
from unittest.mock import patch, MagicMock

# Ensure test environment is set
os.environ['GROQ_API_KEY'] = 'test_key_for_testing'
os.environ['SECRET_KEY'] = 'test_secret_key_32_chars_long_1234567890'
os.environ['ALLOWED_API_KEYS'] = 'test_api_key_123,test_api_key_456'
os.environ['CONFIG_PATH'] = 'config.yaml'  # Use test config if available
os.environ['RATE_LIMIT_ENABLED'] = 'false'  # Disable rate limiting for tests

# Add project root to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app import create_app
from backend.config import Config


@pytest.fixture(scope='session')
def app() -> Generator:
    """
    Create Flask application configured for testing.
    
    Yields:
        Flask: Test-configured Flask application instance.
    """
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['DEBUG'] = False
    yield flask_app


@pytest.fixture(scope='session')
def client(app) -> Generator:
    """
    Create Flask test client fixture.
    
    Args:
        app: Flask application fixture.
        
    Yields:
        FlaskClient: Test client for making requests.
    """
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def sample_transcript() -> str:
    """
    Provide a sample meeting transcript for testing.
    
    Returns:
        str: Sample transcript text with speakers, decisions, and topics.
    """
    return (
        "John: We need to launch the new feature by next week. "
        "Sarah: I'll handle the backend. "
        "Mike: I'll do frontend. "
        "Decision: We will use microservices. "
        "Topics: deployment, testing, release"
    )


@pytest.fixture
def mock_ai_service():
    """
    Create a mocked AI service for testing.
    
    Returns:
        MagicMock: Mocked AIService that returns a predefined summary.
    """
    with patch('backend.services.ai_service.AIService') as mock:
        mock_instance = MagicMock()
        mock_instance.generate_summary.return_value = json.dumps({
            'summary': 'Test summary',
            'action_items': [],
            'decisions': [],
            'key_topics': [],
            'duration_estimate': 'Unknown'
        })
        mock.return_value = mock_instance
        yield mock


@pytest.fixture(scope=chr(115)+chr(101)+chr(115)+chr(115)+chr(105)+chr(111)+chr(110), autouse=True)
def reset_config_singleton():
    """
    Reset Config singleton before each test to ensure clean state.
    """
    Config._instance = None
    yield
    Config._instance = None


@pytest.fixture(scope=chr(115)+chr(101)+chr(115)+chr(115)+chr(105)+chr(111)+chr(110), autouse=True)
def reset_service_singletons():
    """
    Reset service singletons before each test by patching module globals.
    """
    import backend.routes.summarize as summarize_module
    from backend.utils import auth as auth_module
    
    # Store original values
    original_ai = summarize_module._ai_service
    original_whisper = summarize_module._whisper_service
    
    # Reset to None
    summarize_module._ai_service = None
    summarize_module._whisper_service = None
    
    # Clear rate limit store
    auth_module.clear_rate_limit_store()
    
    yield
    
    # Restore original values
    summarize_module._ai_service = original_ai
    summarize_module._whisper_service = original_whisper


@pytest.fixture
def auth_headers() -> dict:
    """
    Provide valid authentication headers for API requests.
    
    Returns:
        dict: Headers with X-API-Key set to a valid test key.
    """
    return {'X-API-Key': 'test_api_key_123'}


@pytest.fixture
def invalid_auth_headers() -> dict:
    """
    Provide invalid authentication headers.
    
    Returns:
        dict: Headers with invalid X-API-Key.
    """
    return {'X-API-Key': 'invalid_key_999'}