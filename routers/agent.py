"""
app/routers/agent.py
─────────────────────
Document analysis endpoints:
  POST /api/v1/analyze   — single document
  POST /api/v1/batch     — up to 20 documents in parallel
"""

import asyncio
import logging

import fastapi
from fastapi import APIRouter

from agent_module.models import AgentRequest, AgentResponse
from agent_module.decision_agent import run_agent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Agent"])


@router.post(
    "/analyze",
    response_model=AgentResponse,
    summary="Analyze a single document",
    responses={
        200: {"description": "Successful analysis"},
        422: {"description": "Validation error in request body"},
        500: {"description": "Agent processing error"},
    },
)
async def analyze_document(req: AgentRequest):
    """
    Run the Decision, Summary & Risk Agent on a **single document**.

    Returns a risk score, recommendation (`approve` / `review` / `reject`),
    AI-generated summary, and a full risk breakdown.
    """
    logger.info(f"Analyzing document: {req.document_id}")
    try:
        result = await run_agent(req)
        logger.info(
            f"[{req.document_id}] score={result.risk_score:.4f} "
            f"rec={result.recommendation} conf={result.confidence:.4f}"
        )
        return result
    except Exception as exc:
        logger.error(f"Agent failed for {req.document_id}: {exc}", exc_info=True)
        raise fastapi.HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/batch",
    response_model=list[AgentResponse],
    summary="Analyze multiple documents in parallel",
)
async def batch_analyze(requests: list[AgentRequest]):
    """
    Process **up to 20 documents** concurrently.
    Results are returned in the same order as the input array.
    """
    if len(requests) > 20:
        raise fastapi.HTTPException(
            status_code=400, detail="Batch limit is 20 documents per request."
        )

    logger.info(f"Batch processing {len(requests)} document(s)")
    results = await asyncio.gather(
        *[run_agent(r) for r in requests], return_exceptions=True
    )

    responses: list[AgentResponse] = []
    for req, result in zip(requests, results):
        if isinstance(result, Exception):
            logger.error(f"Batch item {req.document_id} failed: {result}")
            raise fastapi.HTTPException(
                status_code=500, detail=f"{req.document_id}: {result}"
            )
        responses.append(result)  # type: ignore[arg-type]

    return responses
