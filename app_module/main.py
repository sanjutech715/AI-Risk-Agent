"""
app/main.py
───────────
FastAPI application factory.
Registers all routers and middleware.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import fastapi


from routers import health, agent

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
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
    allow_origins=["*"],      # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(agent.router, prefix="/api/v1")

# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to the Risk Agent API!",
        "docs": "/docs",
        "health": "/health",
    }
