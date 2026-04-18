import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'MeetingAI' in response.data


def test_summarize_no_input(client):
    response = client.post('/api/v1/summarize')
    assert response.status_code == 400
    assert b'No audio file or text provided' in response.data


@patch('backend.routes.summarize.get_ai_service')
def test_summarize_with_text(mock_ai_service, client, sample_transcript):
    mock_service = MagicMock()
    mock_service.generate_summary.return_value = '{"summary": "Test summary", "action_items": [], "decisions": [], "key_topics": [], "duration_estimate": "Unknown"}'
    mock_ai_service.return_value = mock_service
    
    response = client.post('/api/v1/summarize', data={'text': sample_transcript})
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'result' in json_data
    assert 'transcript_length' in json_data


def test_summarize_invalid_file_type(client):
    data = {'file': (BytesIO(b'fake audio'), 'test.txt')}
    response = client.post('/api/v1/summarize', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b'Invalid file type' in response.data


def test_summarize_empty_text(client):
    response = client.post('/api/v1/summarize', data={'text': ''})
    assert response.status_code == 400


def test_api_endpoint_exists(client):
    response = client.post('/api/v1/summarize', data={'text': 'test'})
    assert response.status_code in [200, 500]