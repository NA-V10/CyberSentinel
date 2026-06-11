from typing import AsyncGenerator, Optional

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
    engine_kwargs: dict = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    }

    # Neon uses PgBouncer in transaction mode — prepared statements are not
    # supported across connections, so we must disable asyncpg's cache.
    # Also need explicit SSL since the pooler endpoint requires it.
    db_url: str = settings.DATABASE_URL
    if "neon.tech" in db_url or "sslmode=require" in db_url:
        engine_kwargs["connect_args"] = {
            "prepared_statement_cache_size": 0,
            "ssl": "require",
        }
        # asyncpg does not accept sslmode as a URL query param — strip it
        # so SQLAlchemy does not try to pass it through as-is.
        from urllib.parse import urlparse, urlencode, urlunparse, parse_qs
        parsed = urlparse(db_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs.pop("sslmode", None)
        qs.pop("channel_binding", None)
        cleaned = parsed._replace(query=urlencode({k: v[0] for k, v in qs.items()}))
        db_url = urlunparse(cleaned)

    return create_async_engine(db_url, **engine_kwargs)


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

async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    """FastAPI dependency that yields an async database session.

    Yields ``None`` instead of raising when the database is unavailable so
    that endpoints can degrade gracefully rather than returning a 500 error.

    Usage::

        @router.get("/items")
        async def list_items(db: Optional[AsyncSession] = Depends(get_db)):
            if db is None:
                return []  # DB unavailable — return safe fallback
            ...
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    except Exception as exc:
        logger.warning("Database unavailable — yielding None session", error=str(exc))
        yield None


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
    try:
        import backend.app.models.premium_models  # noqa: F401
    except ImportError:
        pass

    logger.info("Initialising database — creating tables if they do not exist")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialisation complete")


async def close_db() -> None:
    """Dispose of all pooled connections.  Call during application shutdown."""
    await engine.dispose()
    logger.info("Database engine disposed")
