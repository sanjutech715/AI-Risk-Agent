"""
tests/test_scoring.py
──────────────────────
Tests for the risk scoring engine (compute_risk, recommendations, confidence, flags).
"""

import pytest
import math

from agent_module.scoring import (
    compute_risk,
    compute_recommendation,
    compute_confidence,
    collect_flags,
    APPROVE_THRESHOLD,
    REVIEW_THRESHOLD,
    WEIGHTS,
)
from agent_module.models import StandardizedData, ValidationResult, RiskBreakdown


class TestComputeRisk:
    """Tests for compute_risk function."""

    def test_all_valid_no_issues(self):
        """Valid document with no issues should have low risk."""
        data = StandardizedData(
            document_type="invoice",
            issuer="Acme Corp",
            amount=10000.0,
            counterparty="Partner Ltd",
            jurisdiction="US",
        )
        val = ValidationResult(
            is_valid=True,
            missing_fields=[],
            anomalies=[],
            schema_errors=[],
            completeness_score=1.0,
        )
        risk_score, breakdown = compute_risk(data, val)
        assert risk_score == 0.0
        assert breakdown.overall_risk == 0.0
        assert isinstance(breakdown, RiskBreakdown)

    def test_invalid_document(self):
        """Invalid document should have baseline validation risk."""
        data = StandardizedData(document_type="invoice")
        val = ValidationResult(
            is_valid=False,
            missing_fields=[],
            anomalies=[],
            schema_errors=[],
            completeness_score=1.0,
        )
        risk_score, breakdown = compute_risk(data, val)
        # Base validation risk is 0.4 when invalid
        expected_risk = 0.4 * WEIGHTS["validation"]
        assert abs(risk_score - expected_risk) < 0.01

    def test_missing_fields_increase_risk(self):
        """Missing fields should increase validation risk."""
        data = StandardizedData(document_type="invoice")
        val = ValidationResult(
            is_valid=True,
            missing_fields=["issuer", "amount", "counterparty"],
            anomalies=[],
            schema_errors=[],
            completeness_score=1.0,
        )
        risk_score, breakdown = compute_risk(data, val)
        # 3 missing fields × 0.08 = 0.24 validation risk
        assert breakdown.validation_risk > 0.0
        assert risk_score > 0.0

    def test_low_completeness_score(self):
        """Low completeness should increase completeness risk."""
        data = StandardizedData(document_type="invoice")
        val = ValidationResult(
            is_valid=True,
            missing_fields=[],
            anomalies=[],
            schema_errors=[],
            completeness_score=0.5,
        )
        risk_score, breakdown = compute_risk(data, val)
        # Completeness risk = 1.0 - 0.5 = 0.5
        expected_completeness_risk = 0.5
        assert abs(breakdown.completeness_risk - expected_completeness_risk) < 0.01
        assert risk_score > 0.0

    def test_anomalies_increase_risk(self):
        """Anomalies should increase anomaly risk (sigmoid curve)."""
        data = StandardizedData(document_type="invoice")
        val_no_anomaly = ValidationResult(
            is_valid=True,
            missing_fields=[],
            anomalies=[],
            schema_errors=[],
            completeness_score=1.0,
        )
        val_one_anomaly = ValidationResult(
            is_valid=True,
            missing_fields=[],
            anomalies=["duplicate"],
            schema_errors=[],
            completeness_score=1.0,
        )
        val_multiple_anomalies = ValidationResult(
            is_valid=True,
            missing_fields=[],
            anomalies=["duplicate", "expired", "suspicious"],
            schema_errors=[],
            completeness_score=1.0,
        )

        risk_no, _ = compute_risk(data, val_no_anomaly)
        risk_one, _ = compute_risk(data, val_one_anomaly)
        risk_multi, _ = compute_risk(data, val_multiple_anomalies)

        assert risk_no == 0.0
        assert risk_one > 0.0
        assert risk_multi > risk_one

    def test_schema_errors_increase_risk(self):
        """Schema errors should increase schema risk linearly."""
        data = StandardizedData(document_type="invoice")
        val = ValidationResult(
            is_valid=True,
            missing_fields=[],
            anomalies=[],
            schema_errors=["invalid_amount", "invalid_date"],
            completeness_score=1.0,
        )
        risk_score, breakdown = compute_risk(data, val)
        # 2 schema errors × 0.15 = 0.30 schema risk
        expected_schema_risk = 0.30
        assert abs(breakdown.schema_risk - expected_schema_risk) < 0.01

    def test_composite_risk_formula(self):
        """Composite risk should follow the weighted formula."""
        data = StandardizedData(document_type="invoice")
        val = ValidationResult(
            is_valid=False,
            missing_fields=["issuer"],
            anomalies=["duplicate"],
            schema_errors=["invalid_date"],
            completeness_score=0.8,
        )
        risk_score, breakdown = compute_risk(data, val)

        # Verify weights sum to 1.0
        assert sum(WEIGHTS.values()) == 1.0

        # Verify composite matches formula
        expected_composite = (
            WEIGHTS["validation"] * breakdown.validation_risk
            + WEIGHTS["completeness"] * breakdown.completeness_risk
            + WEIGHTS["anomaly"] * breakdown.anomaly_risk
            + WEIGHTS["schema"] * breakdown.schema_risk
        )
        assert abs(risk_score - expected_composite) < 0.01

    def test_risk_capped_at_one(self):
        """Risk score should never exceed 1.0."""
        data = StandardizedData(document_type="invoice")
        val = ValidationResult(
            is_valid=False,
            missing_fields=["a", "b", "c", "d", "e"],
            anomalies=["x", "y", "z"],
            schema_errors=["s1", "s2", "s3"],
            completeness_score=0.0,
        )
        risk_score, breakdown = compute_risk(data, val)
        assert risk_score <= 1.0
        assert breakdown.overall_risk <= 1.0


class TestComputeRecommendation:
    """Tests for compute_recommendation function."""

    def test_low_risk_approve(self):
        """Risk ≤ 0.25 should recommend approve."""
        assert compute_recommendation(0.0) == "approve"
        assert compute_recommendation(0.15) == "approve"
        assert compute_recommendation(APPROVE_THRESHOLD) == "approve"

    def test_medium_risk_review(self):
        """Risk between 0.25 and 0.55 should recommend review."""
        assert compute_recommendation(0.30) == "review"
        assert compute_recommendation(0.40) == "review"
        assert compute_recommendation(REVIEW_THRESHOLD) == "review"

    def test_high_risk_reject(self):
        """Risk > 0.55 should recommend reject."""
        assert compute_recommendation(0.56) == "reject"
        assert compute_recommendation(0.75) == "reject"
        assert compute_recommendation(1.0) == "reject"

    def test_boundary_conditions(self):
        """Test exact threshold boundaries."""
        # Just above approve boundary
        assert compute_recommendation(APPROVE_THRESHOLD + 0.001) == "review"
        # Just above review boundary
        assert compute_recommendation(REVIEW_THRESHOLD + 0.001) == "reject"


class TestComputeConfidence:
    """Tests for compute_confidence function."""

    def test_high_confidence_when_risk_is_clear(self):
        """Confidence should be highest when risk is clear and completeness is high."""
        # Very low risk + high completeness = high confidence
        confidence_low = compute_confidence(0.0, ValidationResult(
            is_valid=True,
            completeness_score=1.0,
        ))
        # Very high risk + high completeness = moderate confidence
        # (because confidence is driven by boundary_factor and completeness_score)
        confidence_high = compute_confidence(1.0, ValidationResult(
            is_valid=True,
            completeness_score=1.0,
        ))
        assert confidence_low > 0.70
        assert confidence_high > 0.50

    def test_lower_confidence_near_boundaries(self):
        """Confidence should dip near decision boundaries."""
        # Near approve boundary (0.25)
        confidence_near_approve = compute_confidence(0.25, ValidationResult(
            is_valid=True,
            completeness_score=0.9,
        ))
        # Near review boundary (0.55)
        confidence_near_review = compute_confidence(0.55, ValidationResult(
            is_valid=True,
            completeness_score=0.9,
        ))
        # Far from boundaries
        confidence_far = compute_confidence(0.40, ValidationResult(
            is_valid=True,
            completeness_score=0.9,
        ))
        
        # Confidence near boundaries should be lower
        assert confidence_near_approve < confidence_far
        assert confidence_near_review < confidence_far

    def test_completeness_affects_confidence(self):
        """Higher completeness should increase confidence."""
        val_complete = ValidationResult(
            is_valid=True,
            completeness_score=1.0,
        )
        val_incomplete = ValidationResult(
            is_valid=True,
            completeness_score=0.3,
        )
        confidence_complete = compute_confidence(0.40, val_complete)
        confidence_incomplete = compute_confidence(0.40, val_incomplete)
        assert confidence_complete > confidence_incomplete

    def test_confidence_bounds(self):
        """Confidence should always be between 0.05 and 0.99."""
        for risk_score in [0.0, 0.25, 0.40, 0.55, 1.0]:
            confidence = compute_confidence(risk_score, ValidationResult(
                is_valid=True,
                completeness_score=0.5,
            ))
            assert 0.05 <= confidence <= 0.99


class TestCollectFlags:
    """Tests for collect_flags function."""

    def test_no_flags_for_valid_complete_document(self):
        """Valid, complete document should have no flags."""
        data = StandardizedData(
            document_type="invoice",
            issuer="Acme",
            amount=10000.0,
            expiry_date="2025-12-31",
            counterparty="Partner",
        )
        val = ValidationResult(
            is_valid=True,
            missing_fields=[],
            anomalies=[],
            schema_errors=[],
            completeness_score=1.0,
        )
        flags = collect_flags(data, val)
        assert len(flags) == 0

    def test_invalid_document_flag(self):
        """Invalid document should have corresponding flag."""
        data = StandardizedData(document_type="invoice")
        val = ValidationResult(
            is_valid=False,
            missing_fields=[],
            anomalies=[],
            schema_errors=[],
            completeness_score=1.0,
        )
        flags = collect_flags(data, val)
        assert "Document failed validation" in flags

    def test_missing_fields_flags(self):
        """Missing fields should generate flags."""
        data = StandardizedData(document_type="invoice")
        val = ValidationResult(
            is_valid=True,
            missing_fields=["issuer", "amount"],
            anomalies=[],
            schema_errors=[],
            completeness_score=1.0,
        )
        flags = collect_flags(data, val)
        assert "Missing required field: issuer" in flags
        assert "Missing required field: amount" in flags

    def test_anomaly_flags(self):
        """Anomalies should generate flags."""
        data = StandardizedData(document_type="invoice")
        val = ValidationResult(
            is_valid=True,
            missing_fields=[],
            anomalies=["duplicate_entry", "expired_date"],
            schema_errors=[],
            completeness_score=1.0,
        )
        flags = collect_flags(data, val)
        assert "Anomaly detected: duplicate_entry" in flags
        assert "Anomaly detected: expired_date" in flags

    def test_schema_error_flags(self):
        """Schema errors should generate flags."""
        data = StandardizedData(document_type="invoice")
        val = ValidationResult(
            is_valid=True,
            missing_fields=[],
            anomalies=[],
            schema_errors=["invalid_amount", "invalid_date"],
            completeness_score=1.0,
        )
        flags = collect_flags(data, val)
        assert "Schema error: invalid_amount" in flags
        assert "Schema error: invalid_date" in flags

    def test_high_value_transaction_flag(self):
        """Transactions > 1M should get high-value flag."""
        data = StandardizedData(
            document_type="invoice",
            amount=1_500_000.0,
        )
        val = ValidationResult(
            is_valid=True,
            completeness_score=1.0,
        )
        flags = collect_flags(data, val)
        assert any("High-value transaction" in flag for flag in flags)

    def test_no_expiry_date_flag(self):
        """Document without expiry date should get flag."""
        data = StandardizedData(
            document_type="invoice",
            expiry_date=None,
        )
        val = ValidationResult(
            is_valid=True,
            completeness_score=1.0,
        )
        flags = collect_flags(data, val)
        assert "No expiry date specified" in flags

    def test_multiple_flags(self):
        """Document can have multiple flags."""
        data = StandardizedData(
            document_type="invoice",
            amount=2_000_000.0,
        )
        val = ValidationResult(
            is_valid=False,
            missing_fields=["issuer"],
            anomalies=["suspicious"],
            schema_errors=["invalid_date"],
            completeness_score=0.5,
        )
        flags = collect_flags(data, val)
        assert len(flags) >= 4
        assert "Document failed validation" in flags
        assert any("High-value transaction" in flag for flag in flags)
        assert "Anomaly detected: suspicious" in flags
