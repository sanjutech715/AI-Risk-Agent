"""
app/routers/health.py
─────────────────────
Liveness / readiness probe endpoints.
"""

from datetime import datetime, timezone
from fastapi import APIRouter
from agent_module.models import HealthResponse

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Liveness probe — returns agent status and current timestamp."""
    return HealthResponse(
        status="ok",
        agent="Decision-Summary-Risk-Agent",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
