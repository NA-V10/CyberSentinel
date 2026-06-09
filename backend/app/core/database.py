from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.app.core.config import settings
from backend.app.core.logging import logger


# ---------------------------------------------------------------------------
# Declarative base — all models inherit from this class
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """SQLAlchemy declarative base shared by all ORM models."""


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _build_engine() -> AsyncEngine:
    """Create an async SQLAlchemy engine from the configured DATABASE_URL."""
    engine_kwargs = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,       # recycles dead connections
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,        # recycle connections every 30 min
    }

    return create_async_engine(settings.DATABASE_URL, **engine_kwargs)


engine: AsyncEngine = _build_engine()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Usage::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Startup helper
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Create all tables defined on Base.metadata.

    Call this once during application startup.  For production migrations
    prefer Alembic; this function is useful for development and testing.
    """
    # Import all models so their tables are registered on Base.metadata
    # before create_all is called.
    import backend.app.models.incident  # noqa: F401

    logger.info("Initialising database — creating tables if they do not exist")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialisation complete")


async def close_db() -> None:
    """Dispose of all pooled connections.  Call during application shutdown."""
    await engine.dispose()
    logger.info("Database engine disposed")
