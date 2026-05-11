"""
app/routers/agent.py
─────────────────────
Document analysis endpoints with caching and database persistence:
  POST /api/v1/analyze   — single document
  POST /api/v1/batch     — up to 20 documents in parallel
"""

import asyncio
import logging
import time
from typing import Optional

import fastapi
from fastapi import APIRouter, Depends

from config import settings
from core.agent.models import AgentRequest, AgentResponse
from core.cache import cache
from core.database import get_db_session
from core.models import AnalysisResult
from services.agent import run_agent
from services.auth import oauth2_scheme
from services.auth_service import (User, get_current_active_user,
                                   get_current_user)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Agent"])


async def get_optional_active_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    if not settings.enable_authentication:
        return None

    if token is None:
        return None

    current_user = await get_current_user(token)
    return await get_current_active_user(current_user)


async def save_analysis_to_db(result: AgentResponse, processing_time_ms: int) -> None:
    """Save analysis result to database."""
    if not settings.database_url.startswith("postgresql"):
        return  # Skip if not using PostgreSQL

    try:
        async with get_db_session() as session:
            analysis = AnalysisResult(
                document_id=result.document_id,
                standardized_data=result.standardized_data.dict(),
                validation_result=result.validation_result.dict(),
                risk_score=result.risk_score,
                recommendation=result.recommendation,
                confidence=result.confidence,
                summary=result.summary,
                risk_breakdown=result.risk_breakdown.dict(),
                processing_time_ms=processing_time_ms,
                llm_provider=getattr(result, "llm_provider", None),
            )
            session.add(analysis)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to save analysis to database: {e}")


async def get_cached_result(cache_key: str) -> Optional[AgentResponse]:
    """Get cached analysis result."""
    if not settings.enable_caching:
        return None

    try:
        cached_data = await cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for key: {cache_key}")
            return AgentResponse(**cached_data)
    except Exception as e:
        logger.warning(f"Cache retrieval failed: {e}")

    return None


async def set_cached_result(cache_key: str, result: AgentResponse) -> None:
    """Cache analysis result."""
    if not settings.enable_caching:
        return

    try:
        await cache.set(cache_key, result.model_dump(), ttl=settings.cache_ttl_seconds)
        logger.info(f"Cached result for key: {cache_key}")
    except Exception as e:
        logger.warning(f"Cache storage failed: {e}")


def generate_cache_key(req: AgentRequest) -> str:
    """Generate cache key for request."""
    # Create a deterministic key based on request content
    import hashlib
    import json

    key_data = {
        "document_id": req.document_id,
        "standardized_data": req.standardized_data.model_dump(),
        "validation_result": req.validation_result.model_dump(),
    }
    key_string = json.dumps(key_data, sort_keys=True)
    return f"analysis:{hashlib.md5(key_string.encode()).hexdigest()}"


@router.post(
    "/analyze",
    response_model=AgentResponse,
    summary="Analyze a single document",
    responses={
        200: {"description": "Successful analysis"},
        422: {"description": "Validation error in request body"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Agent processing error"},
    },
)
async def analyze_document(
    req: AgentRequest,
    current_user: Optional[User] = Depends(get_optional_active_user),
):
    """
    Run the Decision, Summary & Risk Agent on a **single document**.

    Features:
    - Intelligent risk scoring and recommendation
    - AI-generated document summaries
    - Response caching for improved performance
    - Database persistence for audit trails

    Returns a risk score, recommendation (`approve` / `review` / `reject`),
    AI-generated summary, and a full risk breakdown.
    """
    start_time = time.time()
    cache_key = generate_cache_key(req)

    logger.info(f"Analyzing document: {req.document_id}")

    # Check cache first
    cached_result = await get_cached_result(cache_key)
    if cached_result:
        processing_time = int((time.time() - start_time) * 1000)
        logger.info(f"[{req.document_id}] cache hit, processing_time={processing_time}ms")
        return cached_result

    try:
        # Run analysis
        result = await run_agent(req)
        processing_time = int((time.time() - start_time) * 1000)

        # Cache the result
        await set_cached_result(cache_key, result)

        # Save to database
        await save_analysis_to_db(result, processing_time)

        logger.info(
            f"[{req.document_id}] score={result.risk_score:.4f} "
            f"rec={result.recommendation} conf={result.confidence:.4f} "
            f"processing_time={processing_time}ms"
        )

        return result

    except Exception as exc:
        processing_time = int((time.time() - start_time) * 1000)
        logger.error(f"Agent failed for {req.document_id} after {processing_time}ms: {exc}", exc_info=True)
        raise fastapi.HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/batch",
    response_model=list[AgentResponse],
    summary="Analyze multiple documents in parallel",
)
async def batch_analyze(
    requests: list[AgentRequest],
    current_user: Optional[User] = Depends(get_optional_active_user),
):
    """
    Process **up to 20 documents** concurrently.
    Results are returned in the same order as the input array.
    """
    if len(requests) > 20:
        raise fastapi.HTTPException(status_code=400, detail="Batch limit is 20 documents per request.")

    logger.info(f"Batch processing {len(requests)} document(s)")
    results = await asyncio.gather(*[run_agent(r) for r in requests], return_exceptions=True)

    responses: list[AgentResponse] = []
    for req, result in zip(requests, results):
        if isinstance(result, Exception):
            logger.error(f"Batch item {req.document_id} failed: {result}")
            raise fastapi.HTTPException(status_code=500, detail=f"{req.document_id}: {result}")
        responses.append(result)  # type: ignore[arg-type]

    return responses
