"""
tests/test_api.py
----------------
Pytest tests for the Risk Agent API.

Usage:
    pytest tests/test_api.py -v
    python -m pytest tests/test_api.py -v
"""

import pytest

# Use fixtures from pytesting/conftest.py - no live server needed


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
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


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client):
        """Health endpoint should return status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_version(self, client):
        """Health endpoint should return version."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] == "1.0.0"


class TestAnalyzeEndpoint:
    """Tests for /api/v1/analyze endpoint."""

    def test_analyze_valid_document(self, client, sample_document):
        """Should successfully analyze a valid document."""
        response = client.post("/api/v1/analyze", json=sample_document)
        assert response.status_code == 200
        data = response.json()

        # Check response fields
        assert data["document_id"] == "TEST001"
        assert "summary" in data
        assert "risk_score" in data
        assert 0.0 <= data["risk_score"] <= 1.0
        assert data["recommendation"] in ["approve", "review", "reject"]
        assert 0.0 <= data["confidence"] <= 1.0
        assert "risk_breakdown" in data

    def test_analyze_high_risk_document(self, client, high_risk_document):
        """Should correctly identify high risk document."""
        response = client.post("/api/v1/analyze", json=high_risk_document)
        assert response.status_code == 200
        data = response.json()

        # High risk document should have higher risk score
        assert data["risk_score"] > 0.3
        # Should have flags for missing fields
        assert len(data["flags"]) > 0

    def test_analyze_invalid_document_id(self, client):
        """Should handle missing document_id."""
        invalid_doc = {
            "standardized_data": {"document_type": "invoice"},
            "validation_result": {
                "is_valid": True,
                "missing_fields": [],
                "anomalies": [],
                "schema_errors": [],
                "completeness_score": 1.0,
            },
        }
        response = client.post("/api/v1/analyze", json=invalid_doc)
        # Should return 422 validation error
        assert response.status_code == 422


class TestBatchEndpoint:
    """Tests for /api/v1/batch endpoint."""

    def test_batch_single_document(self, client, sample_document):
        """Should successfully process single document in batch."""
        response = client.post("/api/v1/batch", json=[sample_document])
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_batch_multiple_documents(self, client, sample_document, high_risk_document):
        """Should successfully process multiple documents."""
        docs = [sample_document, high_risk_document]
        response = client.post("/api/v1/batch", json=docs)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_batch_exceeds_limit(self, client, sample_document):
        """Should reject batch exceeding 20 documents."""
        # Create 21 documents
        docs = [{"document_id": f"DOC{i}", **sample_document} for i in range(21)]
        response = client.post("/api/v1/batch", json=docs)
        assert response.status_code == 400


class TestRiskScoring:
    """Tests for risk scoring logic."""

    def test_low_risk_approve(self, client):
        """Low risk document should get approve recommendation."""
        doc = {
            "document_id": "LOW001",
            "standardized_data": {
                "document_type": "invoice",
                "issuer": "Valid Corp",
                "amount": 1000.0,
                "currency": "USD",
                "issue_date": "2024-01-01",
                "expiry_date": "2024-12-31",
                "counterparty": "Valid Partner",
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
        response = client.post("/api/v1/analyze", json=doc)
        data = response.json()
        assert data["recommendation"] == "approve"
        assert data["risk_score"] <= 0.25

    def test_high_risk_reject(self, client):
        """High risk document should get reject recommendation."""
        doc = {
            "document_id": "HIGH001",
            "standardized_data": {
                "document_type": "contract",
                "issuer": None,
                "amount": 1000000.0,
                "currency": "USD",
                "issue_date": None,
                "expiry_date": None,
                "counterparty": None,
                "jurisdiction": None,
                "metadata": {},
            },
            "validation_result": {
                "is_valid": False,
                "missing_fields": ["issuer", "counterparty", "issue_date", "expiry_date"],
                "anomalies": ["suspicious activity", "duplicate signature", "amount mismatch"],
                "schema_errors": ["invalid format", "missing required field"],
                "completeness_score": 0.1,
            },
        }
        response = client.post("/api/v1/analyze", json=doc)
        data = response.json()
        assert data["recommendation"] == "reject"
        assert data["risk_score"] >= 0.55  # REVIEW_THRESHOLD = 0.55
