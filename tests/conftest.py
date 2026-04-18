import os
import pytest

os.environ['GROQ_API_KEY'] = 'test_key_for_testing'

from backend.app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_transcript():
    return "John: We need to launch the new feature by next week. Sarah: I'll handle the backend. Mike: I'll do frontend. Decision: We will use microservices. Topics: deployment, testing, release"