"""
tests/conftest.py
──────────────────
Shared fixtures and configuration for the Risk Agent test suite.
"""

import sys
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add project root to path so imports work when running pytest from tests/ subdirectory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app_module.main import app as fastapi_app


@pytest.fixture(scope="session")
def app():
    """Create a single FastAPI app instance for the whole test session."""
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    """Shared TestClient — no live server needed."""
    return TestClient(app)