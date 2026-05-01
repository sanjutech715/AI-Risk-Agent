"""
tests/test_models.py
─────────────────────
Unit tests for Pydantic models (AgentRequest, AgentResponse, etc.)
and the decision_agent pipeline with a mocked LLM service.

Run:
    pytest tests/test_models.py -v
"""

import pytest
from unittest.mock import AsyncMock, patch
from pydantic import ValidationError

from agent_module.models import (
    AgentRequest,
    AgentResponse,
    RiskBreakdown,
    StandardizedData,
    ValidationResult,
)


# ── ValidationResult ──────────────────────────────────────────────────────────

class TestValidationResultModel:
    def test_valid_minimal(self):
        vr = ValidationResult(is_valid=True, completeness_score=0.8)
        assert vr.is_valid is True
        assert vr.completeness_score == 0.8
        assert vr.missing_fields == []
        assert vr.anomalies == []
        assert vr.schema_errors == []

    def test_completeness_score_below_0_raises(self):
        with pytest.raises(ValidationError):
            ValidationResult(is_valid=True, completeness_score=-0.1)

    def test_completeness_score_above_1_raises(self):
        with pytest.raises(ValidationError):
            ValidationResult(is_valid=True, completeness_score=1.1)

    def test_completeness_score_boundary_0_valid(self):
        vr = ValidationResult(is_valid=True, completeness_score=0.0)
        assert vr.completeness_score == 0.0

    def test_completeness_score_boundary_1_valid(self):
        vr = ValidationResult(is_valid=True, completeness_score=1.0)
        assert vr.completeness_score == 1.0


# ── StandardizedData ──────────────────────────────────────────────────────────

class TestStandardizedDataModel:
    def test_only_document_type_required(self):
        sd = StandardizedData(document_type="invoice")
        assert sd.document_type == "invoice"
        assert sd.issuer is None
        assert sd.currency == "USD"

    def test_all_optional_fields_none(self):
        sd = StandardizedData(document_type="contract")
        for field in ("issuer", "amount", "issue_date", "expiry_date", "counterparty", "jurisdiction"):
            assert getattr(sd, field) is None

    def test_metadata_defaults_to_empty_dict(self):
        sd = StandardizedData(document_type="invoice")
        assert sd.metadata == {}

    def test_currency_defaults_to_usd(self):
        sd = StandardizedData(document_type="invoice")
        assert sd.currency == "USD"


# ── AgentRequest ──────────────────────────────────────────────────────────────

class TestAgentRequestModel:
    def test_valid_request(self):
        req = AgentRequest(
            document_id="DOC001",
            standardized_data=StandardizedData(document_type="invoice"),
            validation_result=ValidationResult(is_valid=True, completeness_score=1.0),
        )
        assert req.document_id == "DOC001"

    def test_missing_document_id_raises(self):
        with pytest.raises(ValidationError):
            AgentRequest(
                standardized_data=StandardizedData(document_type="invoice"),
                validation_result=ValidationResult(is_valid=True, completeness_score=1.0),
            )

    def test_missing_standardized_data_raises(self):
        with pytest.raises(ValidationError):
            AgentRequest(
                document_id="X",
                validation_result=ValidationResult(is_valid=True, completeness_score=1.0),
            )


# ── AgentResponse ─────────────────────────────────────────────────────────────

class TestAgentResponseModel:
    def _make_response(self, **kwargs):
        defaults = dict(
            document_id="DOC001",
            summary="Test summary.",
            risk_score=0.1,
            risk_breakdown=RiskBreakdown(
                validation_risk=0.0,
                completeness_risk=0.0,
                anomaly_risk=0.0,
                schema_risk=0.0,
                overall_risk=0.1,
            ),
            recommendation="approve",
            confidence=0.9,
            reasoning="Low risk document.",
            flags=[],
        )
        defaults.update(kwargs)
        return AgentResponse(**defaults)

    def test_valid_response_created(self):
        resp = self._make_response()
        assert resp.document_id == "DOC001"
        assert resp.recommendation == "approve"

    def test_risk_score_above_1_raises(self):
        with pytest.raises(ValidationError):
            self._make_response(risk_score=1.5)

    def test_risk_score_below_0_raises(self):
        with pytest.raises(ValidationError):
            self._make_response(risk_score=-0.1)

    def test_confidence_above_1_raises(self):
        with pytest.raises(ValidationError):
            self._make_response(confidence=1.1)

    def test_recommendation_must_be_valid(self):
        with pytest.raises(ValidationError):
            self._make_response(recommendation="maybe")

    def test_processed_at_auto_populated(self):
        resp = self._make_response()
        assert resp.processed_at.endswith("Z")

    def test_flags_default_is_empty_list(self):
        resp = self._make_response()
        assert resp.flags == []


# ── Decision Agent (mocked LLM) ───────────────────────────────────────────────

class TestDecisionAgent:
    """
    Tests for the run_agent() orchestration function.
    The LLM service is mocked so no API key is required.
    """

    @pytest.fixture
    def sample_request(self):
        return AgentRequest(
            document_id="AGENT001",
            standardized_data=StandardizedData(
                document_type="invoice",
                issuer="Test Corp",
                amount=10000.0,
                currency="USD",
                issue_date="2024-01-01",
                expiry_date="2024-12-31",
                counterparty="Partner Ltd",
                jurisdiction="US",
            ),
            validation_result=ValidationResult(
                is_valid=True,
                missing_fields=[],
                anomalies=[],
                schema_errors=[],
                completeness_score=1.0,
            ),
        )

    @pytest.fixture
    def high_risk_request(self):
        return AgentRequest(
            document_id="AGENT002",
            standardized_data=StandardizedData(
                document_type="contract",
                issuer=None,
                amount=3_000_000.0,
            ),
            validation_result=ValidationResult(
                is_valid=False,
                missing_fields=["issuer", "counterparty", "issue_date"],
                anomalies=["duplicate", "mismatch", "suspicious"],
                schema_errors=["bad format", "missing field"],
                completeness_score=0.1,
            ),
        )

    @pytest.mark.asyncio
    async def test_agent_returns_response_object(self, sample_request):
        from agent_module.decision_agent import run_agent

        with patch("agent_module.decision_agent.generate_summary", new=AsyncMock(return_value="Mock summary.")):
            result = await run_agent(sample_request)

        assert isinstance(result, AgentResponse)

    @pytest.mark.asyncio
    async def test_agent_document_id_matches(self, sample_request):
        from agent_module.decision_agent import run_agent

        with patch("agent_module.decision_agent.generate_summary", new=AsyncMock(return_value="Mock summary.")):
            result = await run_agent(sample_request)

        assert result.document_id == "AGENT001"

    @pytest.mark.asyncio
    async def test_agent_uses_llm_summary(self, sample_request):
        from agent_module.decision_agent import run_agent

        mock_text = "This is an AI-generated summary."
        with patch("agent_module.decision_agent.generate_summary", new=AsyncMock(return_value=mock_text)):
            result = await run_agent(sample_request)

        assert result.summary == mock_text

    @pytest.mark.asyncio
    async def test_perfect_doc_gets_approve(self, sample_request):
        from agent_module.decision_agent import run_agent

        with patch("agent_module.decision_agent.generate_summary", new=AsyncMock(return_value=".")):
            result = await run_agent(sample_request)

        assert result.recommendation == "approve"
        assert result.risk_score == pytest.approx(0.0, abs=1e-4)

    @pytest.mark.asyncio
    async def test_high_risk_doc_gets_reject(self, high_risk_request):
        from agent_module.decision_agent import run_agent

        with patch("agent_module.decision_agent.generate_summary", new=AsyncMock(return_value=".")):
            result = await run_agent(high_risk_request)

        assert result.recommendation == "reject"
        assert result.risk_score > 0.55

    @pytest.mark.asyncio
    async def test_agent_populates_flags(self, high_risk_request):
        from agent_module.decision_agent import run_agent

        with patch("agent_module.decision_agent.generate_summary", new=AsyncMock(return_value=".")):
            result = await run_agent(high_risk_request)

        assert len(result.flags) > 0

    @pytest.mark.asyncio
    async def test_agent_reasoning_contains_score(self, sample_request):
        from agent_module.decision_agent import run_agent

        with patch("agent_module.decision_agent.generate_summary", new=AsyncMock(return_value=".")):
            result = await run_agent(sample_request)

        assert str(result.risk_score) in result.reasoning or "0.0" in result.reasoning

    @pytest.mark.asyncio
    async def test_agent_confidence_within_range(self, sample_request):
        from agent_module.decision_agent import run_agent

        with patch("agent_module.decision_agent.generate_summary", new=AsyncMock(return_value=".")):
            result = await run_agent(sample_request)

        assert 0.0 <= result.confidence <= 1.0
