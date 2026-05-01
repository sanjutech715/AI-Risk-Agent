"""
tests/conftest.py
──────────────────
Shared fixtures and configuration for the Risk Agent test suite.
"""

import pytest
from fastapi.testclient import TestClient
from app_module.main import app as fastapi_app


@pytest.fixture(scope="session")
def client():
    """Shared TestClient — no live server needed."""
    with TestClient(fastapi_app) as c:
        yield c


# ── Reusable document payloads ─────────────────────────────────────────────────

@pytest.fixture
def valid_doc_payload():
    return {
        "document_id": "FIXTURE_VALID",
        "standardized_data": {
            "document_type": "invoice",
            "issuer": "Fixture Corp",
            "amount": 5000.0,
            "currency": "USD",
            "issue_date": "2024-01-01",
            "expiry_date": "2024-12-31",
            "counterparty": "Fixture Partner",
            "jurisdiction": "US",
            "metadata": {},
        },
        "validation_result": {
            "is_valid": True,
            "missing_fields": [],
            "anomalies": [],
            "schema_errors": [],
            "completeness_score": 1.0,
        },
    }


@pytest.fixture
def high_risk_doc_payload():
    return {
        "document_id": "FIXTURE_HIGH_RISK",
        "standardized_data": {
            "document_type": "contract",
            "issuer": None,
            "amount": 2_500_000.0,
            "currency": "USD",
            "issue_date": None,
            "expiry_date": None,
            "counterparty": None,
            "jurisdiction": None,
            "metadata": {},
        },
        "validation_result": {
            "is_valid": False,
            "missing_fields": ["issuer", "counterparty", "issue_date"],
            "anomalies": ["suspicious activity", "duplicate entry", "amount mismatch"],
            "schema_errors": ["invalid format", "missing required field"],
            "completeness_score": 0.1,
        },
    }


# ── Additional fixtures for tests/test_api.py ───────────────────────────────────

@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "document_id": "TEST001",
        "standardized_data": {
            "document_type": "invoice",
            "issuer": "Test Corp",
            "amount": 10000.0,
            "currency": "USD",
            "issue_date": "2024-01-15",
            "expiry_date": "2024-04-15",
            "counterparty": "Partner Ltd",
            "jurisdiction": "US",
            "metadata": {},
        },
        "validation_result": {
            "is_valid": True,
            "missing_fields": [],
            "anomalies": [],
            "schema_errors": [],
            "completeness_score": 0.95,
        },
    }


@pytest.fixture
def high_risk_document():
    """High risk document for testing."""
    return {
        "document_id": "TEST002",
        "standardized_data": {
            "document_type": "contract",
            "issuer": None,
            "amount": 500000.0,
            "currency": "EUR",
            "issue_date": None,
            "counterparty": None,
            "jurisdiction": "Unknown",
            "metadata": {},
        },
        "validation_result": {
            "is_valid": False,
            "missing_fields": ["issuer", "counterparty", "issue_date"],
            "anomalies": ["amount exceeds threshold"],
            "schema_errors": ["missing required field: issuer"],
            "completeness_score": 0.30,
        },
    }
