"""
app/main.py
───────────
FastAPI application factory.
Registers all routers and middleware.
"""

import logging
import socket

import fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from core.middleware_logging import LoggingMiddleware
from core.rate_limiting import RateLimitingMiddleware
from routes import auth, health, rout

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format,
)
logger = logging.getLogger(__name__)

# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Decision, Summary & Risk Agent API",
    description=(
        "AI-powered document analysis agent that generates summaries, "
        "risk scores, and approval recommendations.\n\n"
        "**Endpoints**\n"
        "- `POST /api/v1/analyze` — single document\n"
        "- `POST /api/v1/batch`   — up to 20 documents in parallel\n"
        "- `GET  /health`         — liveness probe\n"
    ),
    version="1.0.0",
    contact={"name": "Risk Agent Team"},
    license_info={"name": "MIT"},
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitingMiddleware)


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: fastapi.Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router)          # ← /auth/token, /auth/users/me
app.include_router(rout.router, prefix="/api/v1")


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to the Risk Agent API!",
        "docs": "/docs",
        "health": "/health",
    }


# ── Run server ────────────────────────────────────────────────────────────────


def find_available_port(host: str, start_port: int, max_attempts: int = 5) -> int:
    port = start_port
    for _ in range(max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                port += 1
    raise RuntimeError(f"No available port found on {host} starting at {start_port}")


def main() -> None:
    import uvicorn

    host = settings.host
    port = find_available_port(host, settings.port)
    if port != settings.port:
        print(f"Port {settings.port} busy, starting server on {port} instead.")

    uvicorn.run(app, host=host, port=port, reload=settings.reload)


if __name__ == "__main__":
    main()
