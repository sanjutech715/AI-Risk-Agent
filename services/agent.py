"""
app/agent/decision_agent.py
────────────────────────────
Orchestrates the full agent pipeline:
  1. Risk scoring          (scoring.py)
  2. AI-powered summary    (services/llm_service.py)
  3. Final response packaging
"""

from __future__ import annotations

from core.agent.models import AgentRequest, AgentResponse
from core.agent.scoring import (
    collect_flags,
    compute_confidence,
    compute_recommendation,
    compute_risk,
)
from core.llm_service import generate_summary


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(
    req: AgentRequest,
    risk_score: float,
    recommendation: str,
    flags: list[str],
) -> str:
    doc = req.standardized_data
    val = req.validation_result

    return f"""You are a document risk analyst. Generate a concise, professional summary \
(2-3 sentences) for the following document review.

Document ID     : {req.document_id}
Document Type   : {doc.document_type}
Issuer          : {doc.issuer or 'Unknown'}
Counterparty    : {doc.counterparty or 'Unknown'}
Amount          : {f"{doc.currency} {doc.amount:,.2f}" if doc.amount else 'Not specified'}
Jurisdiction    : {doc.jurisdiction or 'Not specified'}
Issue Date      : {doc.issue_date or 'Not specified'}
Expiry Date     : {doc.expiry_date or 'Not specified'}

Validation Status : {'VALID' if val.is_valid else 'INVALID'}
Completeness      : {val.completeness_score * 100:.0f}%
Anomalies Found   : {len(val.anomalies)}
Schema Errors     : {len(val.schema_errors)}

Risk Score       : {risk_score:.4f} / 1.00
Recommendation   : {recommendation.upper()}
Flags            : {', '.join(flags) if flags else 'None'}

Write only the summary paragraph. Be factual, professional, and highlight the most \
important risk factors."""


def _build_reasoning(
    risk_score: float,
    recommendation: str,
    flags: list[str],
    val,
) -> str:
    parts = [
        f"Risk score of {risk_score:.4f} places this document in the '{recommendation}' category."
    ]
    if flags:
        shown = flags[:3]
        suffix = "..." if len(flags) > 3 else ""
        parts.append(f"Key concerns: {'; '.join(shown)}{suffix}.")
    parts.append(f"Document completeness is {val.completeness_score * 100:.0f}%.")
    return " ".join(parts)


# ── Main entry-point ──────────────────────────────────────────────────────────

async def run_agent(req: AgentRequest) -> AgentResponse:
    """Full pipeline: score → summarise → package."""

    # 1. Deterministic scoring
    risk_score, breakdown = compute_risk(req.standardized_data, req.validation_result)

    # 2. Derived fields
    recommendation = compute_recommendation(risk_score)
    confidence     = compute_confidence(risk_score, req.validation_result)
    flags          = collect_flags(req.standardized_data, req.validation_result)

    # 3. AI summary (via LLM service)
    prompt  = _build_prompt(req, risk_score, recommendation, flags)
    summary = await generate_summary(prompt)

    # 4. Human-readable reasoning
    reasoning = _build_reasoning(risk_score, recommendation, flags, req.validation_result)

    return AgentResponse(
        document_id=req.document_id,
        summary=summary,
        risk_score=risk_score,
        risk_breakdown=breakdown,
        recommendation=recommendation,
        confidence=confidence,
        reasoning=reasoning,
        flags=flags,
    )
