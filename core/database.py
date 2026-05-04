"""
utils/database.py
─────────────────
SQLAlchemy database setup and session management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from config import settings

# ── Database Engine ───────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    echo=False,  # Set to True for SQL query logging
)

# ── Session Factory ───────────────────────────────────────────────────────────
async_session_factory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Database Session Context Manager ──────────────────────────────────────────
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup."""
    session = async_session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ── Database Models Base ──────────────────────────────────────────────────────
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# ── Database Initialization ───────────────────────────────────────────────────
async def init_database():
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Import all models to ensure they are registered
        from . import models

        await conn.run_sync(Base.metadata.create_all)


async def drop_database():
    """Drop all database tables (for testing)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
