"""
tests/test_scoring.py
--------------------
Unit tests for the deterministic risk scoring engine.
No server or API key needed - pure logic tests.

Run:
    pytest tests/test_scoring.py -v
"""

import math
import pytest

from agent_module.models import StandardizedData, ValidationResult
from agent_module.scoring import (
    APPROVE_THRESHOLD,
    REVIEW_THRESHOLD,
    _anomaly_risk,
    _completeness_risk,
    _schema_risk,
    _validation_risk,
    collect_flags,
    compute_confidence,
    compute_recommendation,
    compute_risk,
)


# Helpers

def make_validation(
    is_valid=True,
    missing_fields=None,
    anomalies=None,
    schema_errors=None,
    completeness_score=1.0,
) -> ValidationResult:
    return ValidationResult(
        is_valid=is_valid,
        missing_fields=missing_fields or [],
        anomalies=anomalies or [],
        schema_errors=schema_errors or [],
        completeness_score=completeness_score,
    )


def make_data(**kwargs) -> StandardizedData:
    defaults = dict(
        document_type="invoice",
        issuer="Test Corp",
        amount=10000.0,
        currency="USD",
        issue_date="2024-01-01",
        expiry_date="2024-12-31",
        counterparty="Partner Ltd",
        jurisdiction="US",
        metadata={},
    )
    defaults.update(kwargs)
    return StandardizedData(**defaults)


# _validation_risk

class TestValidationRisk:
    def test_valid_no_missing_fields_is_zero(self):
        val = make_validation(is_valid=True, missing_fields=[])
        assert _validation_risk(val) == 0.0

    def test_invalid_no_missing_fields_has_base_penalty(self):
        val = make_validation(is_valid=False, missing_fields=[])
        score = _validation_risk(val)
        assert score == 0.4

    def test_valid_with_missing_fields_adds_penalty(self):
        val = make_validation(is_valid=True, missing_fields=["issuer", "counterparty"])
        score = _validation_risk(val)
        # 0.0 base + 2 * 0.08 = 0.16
        assert score == pytest.approx(0.16, abs=1e-4)

    def test_invalid_with_many_missing_fields_capped_at_one(self):
        val = make_validation(is_valid=False, missing_fields=["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"])
        score = _validation_risk(val)
        assert score == 1.0

    def test_penalty_capped_even_without_base(self):
        # 8 missing fields → 0.64 penalty → capped? No: 0.6 is cap for penalty, base=0 → 0.6
        val = make_validation(is_valid=True, missing_fields=["a"] * 8)
        score = _validation_risk(val)
        assert score == pytest.approx(0.6, abs=1e-4)


# _completeness_risk

class TestCompletenessRisk:
    def test_perfect_completeness_is_zero(self):
        val = make_validation(completeness_score=1.0)
        assert _completeness_risk(val) == 0.0

    def test_zero_completeness_is_one(self):
        val = make_validation(completeness_score=0.0)
        assert _completeness_risk(val) == 1.0

    def test_half_completeness_is_half(self):
        val = make_validation(completeness_score=0.5)
        assert _completeness_risk(val) == pytest.approx(0.5, abs=1e-4)

    def test_completeness_0_97(self):
        val = make_validation(completeness_score=0.97)
        assert _completeness_risk(val) == pytest.approx(0.03, abs=1e-4)


# _anomaly_risk

class TestAnomalyRisk:
    def test_no_anomalies_is_zero(self):
        val = make_validation(anomalies=[])
        assert _anomaly_risk(val) == 0.0

    def test_one_anomaly_low_risk(self):
        val = make_validation(anomalies=["suspicious amount"])
        score = _anomaly_risk(val)
        # sigmoid: 1 - 1/(1 + e^(1-2)) = 1 - 1/(1+e^-1) ≈ 0.2689
        expected = 1 - 1 / (1 + math.exp(1 - 2))
        assert score == pytest.approx(expected, abs=1e-4)

    def test_two_anomalies_is_0_5(self):
        val = make_validation(anomalies=["a", "b"])
        score = _anomaly_risk(val)
        # 1 - 1/(1 + e^(2-2)) = 1 - 0.5 = 0.5
        assert score == pytest.approx(0.5, abs=1e-4)

    def test_many_anomalies_approaches_one(self):
        val = make_validation(anomalies=["a"] * 10)
        score = _anomaly_risk(val)
        assert score > 0.99


# _schema_risk

class TestSchemaRisk:
    def test_no_schema_errors_is_zero(self):
        val = make_validation(schema_errors=[])
        assert _schema_risk(val) == 0.0

    def test_one_schema_error(self):
        val = make_validation(schema_errors=["missing field"])
        assert _schema_risk(val) == pytest.approx(0.15, abs=1e-4)

    def test_schema_errors_capped_at_one(self):
        val = make_validation(schema_errors=["e"] * 10)
        assert _schema_risk(val) == 1.0

    def test_seven_errors_capped(self):
        # 7 * 0.15 = 1.05 → capped at 1.0
        val = make_validation(schema_errors=["e"] * 7)
        assert _schema_risk(val) == 1.0


# ── compute_risk ───────────────────────────────────────────────────────────────

class TestComputeRisk:
    def test_perfect_document_low_risk(self):
        data = make_data()
        val = make_validation(is_valid=True, completeness_score=1.0)
        score, breakdown = compute_risk(data, val)
        assert score == pytest.approx(0.0, abs=1e-4)
        assert breakdown.overall_risk == score

    def test_risk_score_between_0_and_1(self):
        data = make_data()
        val = make_validation(
            is_valid=False,
            missing_fields=["issuer"],
            anomalies=["suspicious"],
            schema_errors=["bad field"],
            completeness_score=0.5,
        )
        score, _ = compute_risk(data, val)
        assert 0.0 <= score <= 1.0

    def test_breakdown_components_are_set(self):
        data = make_data()
        val = make_validation(is_valid=False, completeness_score=0.6, anomalies=["a"])
        _, breakdown = compute_risk(data, val)
        assert breakdown.validation_risk >= 0.0
        assert breakdown.completeness_risk >= 0.0
        assert breakdown.anomaly_risk >= 0.0
        assert breakdown.schema_risk >= 0.0

    def test_high_risk_document(self):
        data = make_data(issuer=None, counterparty=None)
        val = make_validation(
            is_valid=False,
            missing_fields=["issuer", "counterparty", "issue_date"],
            anomalies=["dup signature", "amount mismatch", "unusual party"],
            schema_errors=["invalid format", "missing required"],
            completeness_score=0.1,
        )
        score, _ = compute_risk(data, val)
        assert score > REVIEW_THRESHOLD  # should be "reject"


# ── compute_recommendation ─────────────────────────────────────────────────────

class TestComputeRecommendation:
    def test_zero_is_approve(self):
        assert compute_recommendation(0.0) == "approve"

    def test_at_approve_threshold_is_approve(self):
        assert compute_recommendation(APPROVE_THRESHOLD) == "approve"

    def test_just_above_approve_is_review(self):
        assert compute_recommendation(APPROVE_THRESHOLD + 0.01) == "review"

    def test_at_review_threshold_is_review(self):
        assert compute_recommendation(REVIEW_THRESHOLD) == "review"

    def test_just_above_review_is_reject(self):
        assert compute_recommendation(REVIEW_THRESHOLD + 0.01) == "reject"

    def test_one_is_reject(self):
        assert compute_recommendation(1.0) == "reject"


# ── compute_confidence ─────────────────────────────────────────────────────────

class TestComputeConfidence:
    def test_confidence_between_0_and_1(self):
        val = make_validation(completeness_score=0.8)
        conf = compute_confidence(0.1, val)
        assert 0.0 <= conf <= 1.0

    def test_high_completeness_boosts_confidence(self):
        val_high = make_validation(completeness_score=1.0)
        val_low = make_validation(completeness_score=0.1)
        conf_high = compute_confidence(0.0, val_high)
        conf_low = compute_confidence(0.0, val_low)
        assert conf_high > conf_low

    def test_near_boundary_has_lower_confidence(self):
        val = make_validation(completeness_score=0.8)
        conf_near = compute_confidence(APPROVE_THRESHOLD, val)      # at boundary
        conf_far = compute_confidence(0.0, val)                     # far from boundary
        assert conf_far > conf_near


# ── collect_flags ──────────────────────────────────────────────────────────────

class TestCollectFlags:
    def test_no_issues_no_flags_for_valid_complete(self):
        data = make_data()
        val = make_validation(is_valid=True)
        flags = collect_flags(data, val)
        # expiry_date is set, so no expiry flag; no other issues
        assert "Document failed validation" not in flags

    def test_invalid_document_flag(self):
        data = make_data()
        val = make_validation(is_valid=False)
        flags = collect_flags(data, val)
        assert "Document failed validation" in flags

    def test_missing_fields_each_get_a_flag(self):
        data = make_data()
        val = make_validation(is_valid=True, missing_fields=["issuer", "counterparty"])
        flags = collect_flags(data, val)
        assert any("issuer" in f for f in flags)
        assert any("counterparty" in f for f in flags)

    def test_anomalies_get_flags(self):
        data = make_data()
        val = make_validation(anomalies=["suspicious activity"])
        flags = collect_flags(data, val)
        assert any("suspicious activity" in f for f in flags)

    def test_schema_errors_get_flags(self):
        data = make_data()
        val = make_validation(schema_errors=["invalid format"])
        flags = collect_flags(data, val)
        assert any("invalid format" in f for f in flags)

    def test_high_value_transaction_flag(self):
        data = make_data(amount=2_000_000.0)
        val = make_validation()
        flags = collect_flags(data, val)
        assert any("High-value" in f for f in flags)

    def test_no_expiry_date_flag(self):
        data = make_data(expiry_date=None)
        val = make_validation()
        flags = collect_flags(data, val)
        assert any("expiry" in f.lower() for f in flags)

    def test_normal_amount_no_high_value_flag(self):
        data = make_data(amount=5000.0)
        val = make_validation()
        flags = collect_flags(data, val)
        assert not any("High-value" in f for f in flags)
