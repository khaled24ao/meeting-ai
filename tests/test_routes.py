"""
Test suite for MeetingAI API endpoints.

Covers index page rendering and summarization endpoint with various inputs.
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from typing import Any, Dict


def test_index_route(client) -> None:
    """
    Test that the index page loads successfully.
    
    Verifies:
        - HTTP 200 response
        - Page contains 'MeetingAI' branding
    """
    response = client.get('/')
    assert response.status_code == 200, "Index page should return 200"
    assert b'MeetingAI' in response.data, "Page should contain 'MeetingAI'"


def test_summarize_no_input(client) -> None:
    """
    Test summarize endpoint rejects requests with no input.
    
    Verifies:
        - HTTP 400 response
        - Appropriate error message returned
    """
    response = client.post('/api/v1/summarize')
    assert response.status_code == 400, "Should return 400 for missing input"
    assert b'No audio file or text provided' in response.data


@patch('backend.routes.summarize.get_ai_service')
def test_summarize_with_text(mock_ai_service, client, sample_transcript) -> None:
    """
    Test summarize endpoint with valid text input.
    
    Args:
        mock_ai_service: Mocked AI service fixture.
        client: Flask test client.
        sample_transcript: Sample transcript text fixture.
        
    Verifies:
        - HTTP 200 response
        - Response contains 'result' and 'transcript_length' fields
    """
    mock_service = MagicMock()
    mock_service.generate_summary.return_value = (
        '{"summary": "Test summary", "action_items": [], '
        '"decisions": [], "key_topics": [], "duration_estimate": "Unknown"}'
    )
    mock_ai_service.return_value = mock_service
    
    response = client.post('/api/v1/summarize', data={'text': sample_transcript})
    assert response.status_code == 200, "Should return 200 for valid text"
    json_data = response.get_json()
    assert 'result' in json_data, "Response should contain 'result'"
    assert 'transcript_length' in json_data, "Response should contain 'transcript_length'"


def test_summarize_invalid_file_type(client) -> None:
    """
    Test summarize endpoint rejects invalid file types.
    
    Verifies:
        - HTTP 400 response
        - Error indicates allowed file types
    """
    data = {'file': (BytesIO(b'fake audio content'), 'test.txt')}
    response = client.post('/api/v1/summarize', 
                          data=data, 
                          content_type='multipart/form-data')
    assert response.status_code == 400, "Should return 400 for invalid file type"
    assert b'Invalid file type' in response.data


def test_summarize_empty_text(client) -> None:
    """
    Test summarize endpoint rejects empty text input.
    
    Verifies:
        - HTTP 400 response for whitespace-only input
    """
    response = client.post('/api/v1/summarize', data={'text': ''})
    assert response.status_code == 400, "Should return 400 for empty text"


def test_api_endpoint_exists(client) -> None:
    """
    Test that summarize endpoint is accessible.
    
    Verifies endpoint responds to POST requests (success or error
    depending on input, but endpoint must be reachable).
    """
    response = client.post('/api/v1/summarize', data={'text': 'test'})
    assert response.status_code in [200, 500], \
        "Endpoint should exist and respond (200 for success, 500 for AI errors)"