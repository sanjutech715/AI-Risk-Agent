"""
app/routers/health.py
─────────────────────
Liveness / readiness probe endpoints with dependency checks.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from config import settings
from core.cache import cache
from core.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System"])


async def check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    if not settings.health_check_database:
        return {"status": "disabled"}

    # If no real database is configured, avoid failing the detailed health check.
    db_url = settings.database_url.strip().lower()
    if (
        not db_url
        or "user:password" in db_url
        or db_url.startswith("sqlite")
        or db_url == "postgresql://user:password@localhost:5432/risk_agent"
    ):
        return {
            "status": "disabled",
            "reason": "Database is not configured for local development",
        }

    try:
        async with get_db_session() as session:
            # Simple query to test connection
            result = await session.execute(text("SELECT 1 AS test"))
            row = result.first()
            if row and row.test == 1:
                return {"status": "healthy"}
            else:
                return {"status": "unhealthy", "error": "Unexpected query result"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def check_cache() -> Dict[str, Any]:
    """Check cache connectivity."""
    if not settings.health_check_cache:
        return {"status": "disabled"}

    try:
        # Test cache with a simple set/get operation
        test_key = "health_check_test"
        test_value = {"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}

        await cache.set(test_key, test_value, ttl=10)
        retrieved_value = await cache.get(test_key)

        if retrieved_value and retrieved_value.get("test") == True:
            await cache.delete(test_key)  # Clean up
            return {"status": "healthy"}
        else:
            return {"status": "degraded", "error": "Cache set/get failed"}
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {"status": "degraded", "error": str(e)}


async def check_llm_service() -> Dict[str, Any]:
    """Check LLM service availability."""
    if not settings.health_check_llm:
        return {"status": "disabled"}

    try:
        # Import here to avoid circular imports
        from core.llm_service import generate_summary

        # Try a simple summary generation
        test_prompt = "Test prompt for health check."
        summary = await generate_summary(test_prompt)

        if summary and len(summary) > 0:
            return {"status": "healthy", "provider": "available"}
        else:
            return {"status": "degraded", "error": "Empty response from LLM"}
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health")
async def health():
    """Basic liveness probe."""
    return {
        "status": "ok",
        "agent": "Decision-Summary-Risk-Agent",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@router.get("/health/detailed")
async def health_detailed():
    """Detailed health check with dependency verification."""
    # Run all health checks
    database_health = await check_database()
    cache_health = await check_cache()
    llm_health = await check_llm_service()

    # Determine overall status
    all_checks = [database_health, cache_health, llm_health]
    healthy_checks = [check for check in all_checks if check.get("status") in ["healthy", "disabled"]]

    overall_status = "healthy" if len(healthy_checks) == len(all_checks) else "degraded"

    # Check for any unhealthy services
    unhealthy_services = [
        service
        for service, check in [("database", database_health), ("cache", cache_health), ("llm", llm_health)]
        if check.get("status") == "unhealthy"
    ]

    if unhealthy_services:
        overall_status = "unhealthy"

    response = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": "1.0.0",
        "checks": {
            "database": database_health,
            "cache": cache_health,
            "llm_service": llm_health,
        },
    }

    # Return error status if unhealthy
    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail=response)

    return response
