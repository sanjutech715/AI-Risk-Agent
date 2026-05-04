"""
app/services/llm_service.py
────────────────────────────
Pluggable LLM service wrapper.
Supports local Ollama deployments or Anthropic via environment configuration.
"""

import os
import logging
import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
OLLAMA_DEFAULT_URL = "http://127.0.0.1:11434"
OLLAMA_DEFAULT_MODEL = "llama2"
FALLBACK_SUMMARY = (
    "Summary unavailable — set OLLAMA_URL or ANTHROPIC_API_KEY to enable AI-generated summaries."
)


def _build_ollama_payload(prompt: str) -> dict:
    return {
        "model": os.getenv("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL),
        "prompt": prompt,
        "max_tokens": 250,
        "temperature": 0.2,
    }


def _build_anthropic_payload(prompt: str) -> dict:
    return {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }


async def _generate_ollama_summary(prompt: str, endpoint: str) -> str:
    url = endpoint.rstrip("/") + "/v1/generate"
    payload = _build_ollama_payload(prompt)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            raise RuntimeError("Ollama returned no results")
        return results[0].get("content", "").strip()


async def _generate_anthropic_summary(prompt: str, api_key: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = _build_anthropic_payload(prompt)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if "content" in data and data["content"]:
            return data["content"][0].get("text", "").strip()
        if "completion" in data:
            return data["completion"].get("content", "").strip()
        raise RuntimeError("Unexpected Anthropic response format")


async def generate_summary(prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    ollama_url = os.getenv("OLLAMA_URL")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if provider == "ollama" or ollama_url:
        endpoint = ollama_url or OLLAMA_DEFAULT_URL
        logger.info("Generating summary with Ollama at %s", endpoint)
        try:
            return await _generate_ollama_summary(prompt, endpoint)
        except Exception as exc:
            logger.error("Ollama summary generation failed: %s", exc, exc_info=True)

    if provider == "anthropic" or anthropic_key:
        if anthropic_key:
            logger.info("Generating summary with Anthropic")
            try:
                return await _generate_anthropic_summary(prompt, anthropic_key)
            except Exception as exc:
                logger.error("Anthropic summary generation failed: %s", exc, exc_info=True)

    logger.warning("No LLM provider configured or available — using fallback summary.")
    return FALLBACK_SUMMARY
