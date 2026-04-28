"""
app/agent/models.py
────────────────────
All Pydantic input / output schemas for the Risk Agent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


# ── Input Models ──────────────────────────────────────────────────────────────

class ValidationResult(BaseModel):
    is_valid: bool
    missing_fields: list[str] = []
    anomalies: list[str] = []
    schema_errors: list[str] = []
    completeness_score: float = Field(..., ge=0.0, le=1.0)


class StandardizedData(BaseModel):
    document_type: str
    issuer: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "USD"
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    counterparty: Optional[str] = None
    jurisdiction: Optional[str] = None
    metadata: Dict[str, Any] = {}


class AgentRequest(BaseModel):
    document_id: str
    standardized_data: StandardizedData
    validation_result: ValidationResult


# ── Output Models ─────────────────────────────────────────────────────────────

class RiskBreakdown(BaseModel):
    validation_risk: float
    completeness_risk: float
    anomaly_risk: float
    schema_risk: float
    overall_risk: float


class AgentResponse(BaseModel):
    document_id: str
    summary: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_breakdown: RiskBreakdown
    recommendation: Literal["approve", "review", "reject"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    flags: list[str] = []
    processed_at: str = Field(
        default_factory=lambda: (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
    )


class HealthResponse(BaseModel):
    status: str
    agent: str
    version: str
    timestamp: str
