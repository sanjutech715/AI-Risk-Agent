"""
tests/conftest.py
──────────────────
Shared fixtures and configuration for the Risk Agent test suite.
"""

import pytest
from fastapi.testclient import TestClient
from app_module.main import app as fastapi_app


@pytest.fixture(scope="session")
def app():
    """Create a single FastAPI app instance for the whole test session."""
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    """Shared TestClient — no live server needed."""
    return TestClient(app)