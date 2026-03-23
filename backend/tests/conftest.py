import pytest
from fastapi.testclient import TestClient

# Mock settings before importing app
import os
os.environ["OPENAI_API_KEY"] = "test-key"

from app.main import app

@pytest.fixture
def client():
    return TestClient(app)
