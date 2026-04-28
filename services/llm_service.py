"""
app/services/llm_service.py
────────────────────────────
Thin wrapper around the Anthropic Messages API.
Isolates all LLM I/O from the agent orchestration logic.
"""

import os
import logging
import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"
FALLBACK_SUMMARY = (
    "Summary unavailable — set the ANTHROPIC_API_KEY environment variable "
    "to enable AI-generated summaries."
)


async def generate_summary(prompt: str) -> str:
    """
    Call the Anthropic API and return the generated summary text.

    Falls back to a placeholder when ANTHROPIC_API_KEY is not set,
    so the rest of the agent pipeline always works in dev/test.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — using fallback summary.")
        return FALLBACK_SUMMARY

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()
