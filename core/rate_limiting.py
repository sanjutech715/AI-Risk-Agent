"""
middleware/rate_limiting.py
──────────────────────────
Simple in-memory rate limiting middleware.
"""

import logging
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings

logger = logging.getLogger(__name__)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(self, app):
        super().__init__(app)
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if not settings.enable_rate_limiting:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()
        window = settings.rate_limit_window_seconds
        limit = settings.rate_limit_requests

        request_queue = self.requests[client_ip]
        while request_queue and request_queue[0] <= now - window:
            request_queue.popleft()

        if len(request_queue) >= limit:
            logger.warning(f"Rate limit exceeded for {client_ip} on {request.url}")
            retry_after = window
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "detail": f"Rate limit exceeded: {limit} requests per {window} seconds",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-Rate-Limit-Limit": str(limit),
                    "X-Rate-Limit-Window": str(window),
                },
            )

        request_queue.append(now)
        response = await call_next(request)

        if hasattr(response, "headers"):
            response.headers["X-Rate-Limit-Limit"] = str(limit)
            response.headers["X-Rate-Limit-Window"] = str(window)
            response.headers["X-Rate-Limit-Remaining"] = str(max(0, limit - len(request_queue)))

        return response

    def _get_client_ip(self, request: Request) -> str:
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()

        client = request.client
        return client.host if client else "unknown"
