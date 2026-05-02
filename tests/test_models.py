"""
tests/test_models.py
─────────────────────
Tests for Pydantic data models (ValidationResult, StandardizedData, AgentRequest, etc.)
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from agent_module.models import (
    ValidationResult,
    StandardizedData,
    AgentRequest,
    RiskBreakdown,
    AgentResponse,
    HealthResponse,
)


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_validation_result(self):
        """Should create a valid ValidationResult."""
        result = ValidationResult(
            is_valid=True,
            missing_fields=[],
            anomalies=[],
            schema_errors=[],
            completeness_score=0.95,
        )
        assert result.is_valid is True
        assert result.completeness_score == 0.95
        assert len(result.missing_fields) == 0

    def test_completeness_score_bounds(self):
        """Completeness score must be between 0.0 and 1.0."""
        # Valid edge cases
        ValidationResult(
            is_valid=True,
            completeness_score=0.0,
        )
        ValidationResult(
            is_valid=True,
            completeness_score=1.0,
        )

        # Invalid - below 0
        with pytest.raises(ValueError):
            ValidationResult(
                is_valid=True,
                completeness_score=-0.1,
            )

        # Invalid - above 1.0
        with pytest.raises(ValueError):
            ValidationResult(
                is_valid=True,
                completeness_score=1.1,
            )

    def test_with_missing_fields_and_anomalies(self):
        """Should store missing fields and anomalies."""
        result = ValidationResult(
            is_valid=False,
            missing_fields=["issuer", "amount"],
            anomalies=["duplicate_entry", "expired_date"],
            completeness_score=0.60,
        )
        assert result.is_valid is False
        assert len(result.missing_fields) == 2
        assert len(result.anomalies) == 2


class TestStandardizedData:
    """Tests for StandardizedData model."""

    def test_minimal_standardized_data(self):
        """Should create StandardizedData with minimal fields."""
        data = StandardizedData(document_type="invoice")
        assert data.document_type == "invoice"
        assert data.currency == "USD"  # default
        assert data.metadata == {}  # default

    def test_complete_standardized_data(self):
        """Should create StandardizedData with all fields."""
        data = StandardizedData(
            document_type="contract",
            issuer="Acme Corp",
            amount=50000.0,
            currency="EUR",
            issue_date="2024-01-15",
            expiry_date="2024-12-31",
            counterparty="Partner Ltd",
            jurisdiction="DE",
            metadata={"key": "value"},
        )
        assert data.document_type == "contract"
        assert data.issuer == "Acme Corp"
        assert data.amount == 50000.0
        assert data.currency == "EUR"
        assert data.metadata["key"] == "value"

    def test_optional_fields_are_none(self):
        """Optional fields should be None when not provided."""
        data = StandardizedData(document_type="invoice")
        assert data.issuer is None
        assert data.amount is None
        assert data.counterparty is None


class TestAgentRequest:
    """Tests for AgentRequest model."""

    def test_valid_agent_request(self):
        """Should create a valid AgentRequest."""
        request = AgentRequest(
            document_id="DOC001",
            standardized_data=StandardizedData(document_type="invoice"),
            validation_result=ValidationResult(
                is_valid=True,
                completeness_score=0.90,
            ),
        )
        assert request.document_id == "DOC001"
        assert request.standardized_data.document_type == "invoice"
        assert request.validation_result.is_valid is True

    def test_agent_request_requires_fields(self):
        """AgentRequest should require standardized_data and validation_result."""
        # Missing standardized_data should fail
        with pytest.raises(ValidationError):
            AgentRequest(
                document_id="DOC001",
                validation_result=ValidationResult(
                    is_valid=True,
                    completeness_score=0.90,
                ),
            )


class TestRiskBreakdown:
    """Tests for RiskBreakdown model."""

    def test_valid_risk_breakdown(self):
        """Should create a valid RiskBreakdown."""
        breakdown = RiskBreakdown(
            validation_risk=0.2,
            completeness_risk=0.15,
            anomaly_risk=0.1,
            schema_risk=0.05,
            overall_risk=0.5,
        )
        assert breakdown.validation_risk == 0.2
        assert breakdown.overall_risk == 0.5

    def test_risk_values_are_bounded(self):
        """Risk values should be between 0.0 and 1.0."""
        # Valid edge cases
        RiskBreakdown(
            validation_risk=0.0,
            completeness_risk=0.0,
            anomaly_risk=0.0,
            schema_risk=0.0,
            overall_risk=0.0,
        )
        RiskBreakdown(
            validation_risk=1.0,
            completeness_risk=1.0,
            anomaly_risk=1.0,
            schema_risk=1.0,
            overall_risk=1.0,
        )


class TestAgentResponse:
    """Tests for AgentResponse model."""

    def test_valid_agent_response(self):
        """Should create a valid AgentResponse."""
        response = AgentResponse(
            document_id="DOC001",
            summary="This is a test document",
            risk_score=0.3,
            risk_breakdown=RiskBreakdown(
                validation_risk=0.2,
                completeness_risk=0.15,
                anomaly_risk=0.1,
                schema_risk=0.05,
                overall_risk=0.3,
            ),
            recommendation="approve",
            confidence=0.85,
            reasoning="Document passed all validations",
            flags=[],
        )
        assert response.document_id == "DOC001"
        assert response.risk_score == 0.3
        assert response.recommendation == "approve"
        assert response.confidence == 0.85

    def test_processed_at_defaults_to_now(self):
        """processed_at should default to current UTC time."""
        response = AgentResponse(
            document_id="DOC001",
            summary="Test",
            risk_score=0.2,
            risk_breakdown=RiskBreakdown(
                validation_risk=0.0,
                completeness_risk=0.0,
                anomaly_risk=0.0,
                schema_risk=0.0,
                overall_risk=0.2,
            ),
            recommendation="approve",
            confidence=0.9,
            reasoning="OK",
        )
        assert response.processed_at is not None
        assert "Z" in response.processed_at  # UTC marker

    def test_recommendation_enum_validation(self):
        """Recommendation must be one of: approve, review, reject."""
        # Valid
        AgentResponse(
            document_id="DOC001",
            summary="Test",
            risk_score=0.2,
            risk_breakdown=RiskBreakdown(
                validation_risk=0.0,
                completeness_risk=0.0,
                anomaly_risk=0.0,
                schema_risk=0.0,
                overall_risk=0.2,
            ),
            recommendation="approve",
            confidence=0.9,
            reasoning="OK",
        )

        # Invalid recommendation
        with pytest.raises(ValueError):
            AgentResponse(
                document_id="DOC001",
                summary="Test",
                risk_score=0.2,
                risk_breakdown=RiskBreakdown(
                    validation_risk=0.0,
                    completeness_risk=0.0,
                    anomaly_risk=0.0,
                    schema_risk=0.0,
                    overall_risk=0.2,
                ),
                recommendation="invalid_recommendation",
                confidence=0.9,
                reasoning="OK",
            )

    def test_confidence_bounds(self):
        """Confidence must be between 0.0 and 1.0."""
        # Valid
        AgentResponse(
            document_id="DOC001",
            summary="Test",
            risk_score=0.2,
            risk_breakdown=RiskBreakdown(
                validation_risk=0.0,
                completeness_risk=0.0,
                anomaly_risk=0.0,
                schema_risk=0.0,
                overall_risk=0.2,
            ),
            recommendation="approve",
            confidence=0.0,
            reasoning="OK",
        )

        # Invalid - above 1.0
        with pytest.raises(ValueError):
            AgentResponse(
                document_id="DOC001",
                summary="Test",
                risk_score=0.2,
                risk_breakdown=RiskBreakdown(
                    validation_risk=0.0,
                    completeness_risk=0.0,
                    anomaly_risk=0.0,
                    schema_risk=0.0,
                    overall_risk=0.2,
                ),
                recommendation="approve",
                confidence=1.1,
                reasoning="OK",
            )


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_valid_health_response(self):
        """Should create a valid HealthResponse."""
        response = HealthResponse(
            status="ok",
            agent="risk-agent",
            version="1.0.0",
            timestamp="2024-01-15T10:30:00Z",
        )
        assert response.status == "ok"
        assert response.agent == "risk-agent"
        assert response.version == "1.0.0"
