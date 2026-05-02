"""
tests/test_api.py
------------------
Integration tests for the Risk Agent FastAPI endpoints.
Uses FastAPI's TestClient - NO live server or API key needed.
The LLM service is automatically mocked (no ANTHROPIC_API_KEY set).

Run:
    pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient

from app_module.main import app

# Client fixture

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# Shared payloads

VALID_DOC = {
    "document_id": "TEST001",
    "standardized_data": {
        "document_type": "invoice",
        "issuer": "Acme Corp",
        "amount": 15000.0,
        "currency": "USD",
        "issue_date": "2024-01-15",
        "expiry_date": "2024-04-15",
        "counterparty": "Globex Ltd",
        "jurisdiction": "US",
        "metadata": {},
    },
    "validation_result": {
        "is_valid": True,
        "missing_fields": [],
        "anomalies": [],
        "schema_errors": [],
        "completeness_score": 0.97,
    },
}

HIGH_RISK_DOC = {
    "document_id": "TEST002",
    "standardized_data": {
        "document_type": "contract",
        "issuer": None,
        "amount": 500000.0,
        "currency": "EUR",
        "issue_date": None,
        "expiry_date": None,
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


# /health endpoint

class TestHealthEndpoint:
    def test_status_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_status_is_ok(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_version_present(self, client):
        data = client.get("/health").json()
        assert "version" in data

    def test_agent_name_present(self, client):
        data = client.get("/health").json()
        assert data["agent"] == "Decision-Summary-Risk-Agent"

    def test_timestamp_present(self, client):
        data = client.get("/health").json()
        assert "timestamp" in data


# /api/v1/analyze endpoint

class TestAnalyzeEndpoint:

    # Response shape

    def test_status_200_for_valid_doc(self, client):
        r = client.post("/api/v1/analyze", json=VALID_DOC)
        assert r.status_code == 200

    def test_response_has_document_id(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        assert data["document_id"] == "TEST001"

    def test_response_has_risk_score(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        assert "risk_score" in data
        assert 0.0 <= data["risk_score"] <= 1.0

    def test_response_has_valid_recommendation(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        assert data["recommendation"] in ("approve", "review", "reject")

    def test_response_has_confidence(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        assert 0.0 <= data["confidence"] <= 1.0

    def test_response_has_summary(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        assert isinstance(data["summary"], str)
        assert len(data["summary"]) > 0

    def test_response_has_reasoning(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        assert isinstance(data["reasoning"], str)

    def test_response_has_flags_list(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        assert isinstance(data["flags"], list)

    def test_response_has_risk_breakdown(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        bd = data["risk_breakdown"]
        for key in ("validation_risk", "completeness_risk", "anomaly_risk", "schema_risk", "overall_risk"):
            assert key in bd

    def test_response_has_processed_at(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        assert "processed_at" in data

    # Risk scoring correctness

    def test_valid_doc_has_low_risk_score(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        assert data["risk_score"] <= 0.25

    def test_valid_doc_is_approved(self, client):
        data = client.post("/api/v1/analyze", json=VALID_DOC).json()
        assert data["recommendation"] == "approve"

    def test_high_risk_doc_has_higher_score(self, client):
        data = client.post("/api/v1/analyze", json=HIGH_RISK_DOC).json()
        assert data["risk_score"] > 0.25

    def test_high_risk_doc_not_approved(self, client):
        data = client.post("/api/v1/analyze", json=HIGH_RISK_DOC).json()
        assert data["recommendation"] in ("review", "reject")

    def test_high_risk_doc_has_flags(self, client):
        data = client.post("/api/v1/analyze", json=HIGH_RISK_DOC).json()
        assert len(data["flags"]) > 0

    # --- Approve case ---

    def test_perfect_document_gets_approve(self, client):
        doc = {
            "document_id": "PERFECT001",
            "standardized_data": {
                "document_type": "invoice",
                "issuer": "Good Corp",
                "amount": 1000.0,
                "currency": "USD",
                "issue_date": "2024-01-01",
                "expiry_date": "2024-12-31",
                "counterparty": "Good Partner",
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
        data = client.post("/api/v1/analyze", json=doc).json()
        assert data["recommendation"] == "approve"
        assert data["risk_score"] == pytest.approx(0.0, abs=1e-4)

    # --- Reject case ---

    def test_worst_case_document_gets_reject(self, client):
        doc = {
            "document_id": "BAD001",
            "standardized_data": {
                "document_type": "contract",
                "issuer": None,
                "amount": 2_000_000.0,
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
        data = client.post("/api/v1/analyze", json=doc).json()
        assert data["recommendation"] == "reject"
        assert data["risk_score"] > 0.55

    # --- Validation errors ---

    def test_missing_document_id_returns_422(self, client):
        bad_doc = {
            "standardized_data": {"document_type": "invoice"},
            "validation_result": {
                "is_valid": True,
                "missing_fields": [],
                "anomalies": [],
                "schema_errors": [],
                "completeness_score": 1.0,
            },
        }
        r = client.post("/api/v1/analyze", json=bad_doc)
        assert r.status_code == 422

    def test_missing_validation_result_returns_422(self, client):
        bad_doc = {
            "document_id": "X",
            "standardized_data": {"document_type": "invoice"},
        }
        r = client.post("/api/v1/analyze", json=bad_doc)
        assert r.status_code == 422

    def test_completeness_score_out_of_range_returns_422(self, client):
        doc = {
            "document_id": "X",
            "standardized_data": {"document_type": "invoice"},
            "validation_result": {
                "is_valid": True,
                "missing_fields": [],
                "anomalies": [],
                "schema_errors": [],
                "completeness_score": 1.5,  # invalid
            },
        }
        r = client.post("/api/v1/analyze", json=doc)
        assert r.status_code == 422

    def test_empty_body_returns_422(self, client):
        r = client.post("/api/v1/analyze", json={})
        assert r.status_code == 422


# ── /api/v1/batch ──────────────────────────────────────────────────────────────

class TestBatchEndpoint:

    def test_batch_single_document_returns_list(self, client):
        r = client.post("/api/v1/batch", json=[VALID_DOC])
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_batch_preserves_order(self, client):
        docs = [
            {**VALID_DOC, "document_id": "BATCH_A"},
            {**VALID_DOC, "document_id": "BATCH_B"},
        ]
        data = client.post("/api/v1/batch", json=docs).json()
        assert data[0]["document_id"] == "BATCH_A"
        assert data[1]["document_id"] == "BATCH_B"

    def test_batch_mixed_risk_documents(self, client):
        docs = [VALID_DOC, HIGH_RISK_DOC]
        data = client.post("/api/v1/batch", json=docs).json()
        assert len(data) == 2
        scores = [d["risk_score"] for d in data]
        # low-risk first, high-risk second
        assert scores[0] < scores[1]

    def test_batch_each_result_has_required_fields(self, client):
        docs = [VALID_DOC]
        data = client.post("/api/v1/batch", json=docs).json()
        result = data[0]
        for field in ("document_id", "risk_score", "recommendation", "confidence", "flags"):
            assert field in result

    def test_batch_exceeds_20_returns_400(self, client):
        # build 21 unique docs
        docs = [
            {
                **VALID_DOC,
                "document_id": f"DOC{i:03d}",
            }
            for i in range(21)
        ]
        r = client.post("/api/v1/batch", json=docs)
        assert r.status_code == 400

    def test_batch_empty_list_returns_empty(self, client):
        r = client.post("/api/v1/batch", json=[])
        # either 200 with empty list or 422 — both are acceptable
        assert r.status_code in (200, 422)

    def test_batch_exactly_20_is_accepted(self, client):
        docs = [
            {
                **VALID_DOC,
                "document_id": f"LIMIT{i:02d}",
            }
            for i in range(20)
        ]
        r = client.post("/api/v1/batch", json=docs)
        assert r.status_code == 200
        assert len(r.json()) == 20


# ── Routing / 404 ──────────────────────────────────────────────────────────────

class TestRouting:
    def test_unknown_route_returns_404(self, client):
        r = client.get("/nonexistent")
        assert r.status_code == 404

    def test_get_on_analyze_returns_405(self, client):
        r = client.get("/api/v1/analyze")
        assert r.status_code == 405
