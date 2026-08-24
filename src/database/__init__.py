"""
DAP Database Layer — Async PostgreSQL with SQLite fallback for testing.

Provides:
- asyncpg-backed connection pool for production (PostgreSQL)
- sqlite3-backed fallback for testing (zero external deps)

Usage:
    async with get_session() as session:
        # do queries
        await session.commit()

For testing with SQLite, set DATABASE_URL=sqlite+aiosqlite:///./dap_test.db
"""

from contextlib import asynccontextmanager
import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


# ─── Module-level engine (lazy init) ───────────
_engine = None
_session_factory = None


def _get_database_url():
    """Get the database URL from environment or use SQLite for testing."""
    db_url = os.getenv("DATABASE_URL")

    # Allow explicit test database URL override
    if db_url:
        return db_url

    # For testing without external PostgreSQL, use SQLite (in-memory)
    if os.getenv("TESTING") == "1":
        return "sqlite+aiosqlite:///./dap_test.db"

    # Production: PostgreSQL via asyncpg
    return "postgresql+asyncpg://postgres:secret@localhost:5432/dap"


def get_engine():
    """Return a cached SQLAlchemy async engine, creating it if needed."""
    global _engine

    if _engine is None:
        db_url = _get_database_url()
        echo_db = os.getenv("DATABASE_ECHO") == "1"  # Debug logging

        _engine = create_async_engine(
            db_url,
            echo=echo_db,
            pool_size=10 if "postgresql" in db_url else 5,
            max_overflow=20 if "postgresql" in db_url else 10,
        )

    return _engine


def get_session_factory():
    """Return a cached async session factory."""
    global _session_factory, _engine

    if _session_factory is None:
        _engine = get_engine()
        # Pool selection is handled by create_async_engine defaults
        # (AsyncAdaptedQueuePool for asyncpg, QueuePool/StaticPool for SQLite)
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _session_factory


@asynccontextmanager
async def get_session():
    """Async context manager for a database session.

    Usage:
        async with get_session() as session:
            # do queries
            await session.commit()
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    # Ensure engine is properly closed after tests
    if os.getenv("TESTING") == "1":
        try:
            await _engine.dispose()
        except Exception:
            pass


async def init_db():
    """Create all tables in the database.

    Call this once at startup (or in test setup) to ensure the schema exists.
    """
    async with get_engine().begin() as conn:
        from .models import Base  # noqa: F401 - imports all models

        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all tables in the database.

    Call this for clean test runs.
    """
    async with get_engine().begin() as conn:
        from .models import Base  # noqa: F401 - imports all models

        await conn.run_sync(Base.metadata.drop_all)
