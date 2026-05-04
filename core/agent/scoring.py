"""
app/agent/scoring.py
─────────────────────
Deterministic risk scoring engine.
Computes a composite risk score (0.0 = no risk, 1.0 = max risk).

Formula:
    risk = 0.30 × validation_risk
         + 0.25 × completeness_risk
         + 0.25 × anomaly_risk
         + 0.20 × schema_risk

Thresholds:
    0.00 – 0.25  →  approve
    0.26 – 0.55  →  review
    0.56 – 1.00  →  reject
"""

from __future__ import annotations

import math
from typing import Tuple

from .models import RiskBreakdown, StandardizedData, ValidationResult

# ── Weight configuration ──────────────────────────────────────────────────────
WEIGHTS = {
    "validation":   0.30,
    "completeness": 0.25,
    "anomaly":      0.25,
    "schema":       0.20,
}

APPROVE_THRESHOLD = 0.25
REVIEW_THRESHOLD  = 0.55   # above this → reject


# ── Component scorers ─────────────────────────────────────────────────────────

def _validation_risk(val: ValidationResult) -> float:
    """Binary base + per-missing-field penalty."""
    base = 0.0 if val.is_valid else 0.4
    penalty = min(len(val.missing_fields) * 0.08, 0.6)
    return min(base + penalty, 1.0)


def _completeness_risk(val: ValidationResult) -> float:
    """Inverted completeness score."""
    return round(1.0 - val.completeness_score, 4)


def _anomaly_risk(val: ValidationResult) -> float:
    """Sigmoid-shaped penalty — a few anomalies raise risk quickly."""
    n = len(val.anomalies)
    if n == 0:
        return 0.0
    return round(1 - 1 / (1 + math.exp(n - 2)), 4)


def _schema_risk(val: ValidationResult) -> float:
    """Linear penalty per schema error, capped at 1.0."""
    return min(len(val.schema_errors) * 0.15, 1.0)


# ── Public API ────────────────────────────────────────────────────────────────

def compute_risk(
    data: StandardizedData,
    val: ValidationResult,
) -> Tuple[float, RiskBreakdown]:
    """Return (composite_risk_score, RiskBreakdown)."""
    v = _validation_risk(val)
    c = _completeness_risk(val)
    a = _anomaly_risk(val)
    s = _schema_risk(val)

    composite = round(
        min(
            WEIGHTS["validation"]   * v
            + WEIGHTS["completeness"] * c
            + WEIGHTS["anomaly"]      * a
            + WEIGHTS["schema"]       * s,
            1.0,
        ),
        4,
    )

    breakdown = RiskBreakdown(
        validation_risk=round(v, 4),
        completeness_risk=round(c, 4),
        anomaly_risk=round(a, 4),
        schema_risk=round(s, 4),
        overall_risk=composite,
    )
    return composite, breakdown


def compute_recommendation(risk_score: float) -> str:
    if risk_score <= APPROVE_THRESHOLD:
        return "approve"
    if risk_score <= REVIEW_THRESHOLD:
        return "review"
    return "reject"


def compute_confidence(risk_score: float, val: ValidationResult) -> float:
    """
    High confidence when risk is clearly low or clearly high.
    Dips near decision boundaries (0.25 / 0.55).
    """
    boundary_dip = min(
        abs(risk_score - APPROVE_THRESHOLD),
        abs(risk_score - REVIEW_THRESHOLD),
    )
    boundary_factor = min(boundary_dip / 0.275, 1.0)
    confidence = 0.55 * boundary_factor + 0.45 * val.completeness_score
    return round(min(max(confidence, 0.05), 0.99), 4)


def collect_flags(data: StandardizedData, val: ValidationResult) -> list[str]:
    """Human-readable flag list surfaced in the API response."""
    flags: list[str] = []
    if not val.is_valid:
        flags.append("Document failed validation")
    for field in val.missing_fields:
        flags.append(f"Missing required field: {field}")
    for anomaly in val.anomalies:
        flags.append(f"Anomaly detected: {anomaly}")
    for err in val.schema_errors:
        flags.append(f"Schema error: {err}")
    if data.amount and data.amount > 1_000_000:
        flags.append("💰 High-value transaction (>$1M) — enhanced review recommended")
    if not data.expiry_date:
        flags.append("No expiry date specified")
    return flags
