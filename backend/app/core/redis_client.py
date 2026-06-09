import json
from typing import Any, Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError, RedisError

from backend.app.core.config import settings
from backend.app.core.logging import logger

# ---------------------------------------------------------------------------
# Module-level client (lazily initialised)
# ---------------------------------------------------------------------------

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Return the shared async Redis client, creating it on first call.

    The connection pool is reused across the application lifetime.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        logger.info("Redis client initialised", url=settings.REDIS_URL)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection pool.  Call during application shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis client closed")


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

async def cache_get(key: str) -> Optional[Any]:
    """Retrieve a JSON-encoded value from Redis by *key*.

    Returns the deserialised Python object on a cache hit, or ``None`` on a
    cache miss or any connection error.
    """
    try:
        client = await get_redis()
        raw = await client.get(key)
        if raw is None:
            logger.debug("Cache MISS", key=key)
            return None
        logger.debug("Cache HIT", key=key)
        return json.loads(raw)
    except RedisConnectionError as exc:
        logger.warning("Redis connection error during cache_get", key=key, error=str(exc))
        return None
    except RedisError as exc:
        logger.error("Redis error during cache_get", key=key, error=str(exc))
        return None
    except json.JSONDecodeError as exc:
        logger.error("Failed to deserialise cached value", key=key, error=str(exc))
        return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """Serialise *value* as JSON and store it in Redis under *key*.

    Parameters
    ----------
    key:
        Redis key.
    value:
        Any JSON-serialisable Python object.
    ttl:
        Time-to-live in seconds (default: 1 hour).

    Returns ``True`` on success, ``False`` on any error.
    """
    try:
        client = await get_redis()
        serialised = json.dumps(value, default=str)
        await client.setex(key, ttl, serialised)
        logger.debug("Cache SET", key=key, ttl=ttl)
        return True
    except RedisConnectionError as exc:
        logger.warning("Redis connection error during cache_set", key=key, error=str(exc))
        return False
    except (RedisError, TypeError) as exc:
        logger.error("Redis error during cache_set", key=key, error=str(exc))
        return False


async def cache_delete(key: str) -> bool:
    """Delete *key* from Redis.

    Returns ``True`` if the key existed and was deleted, ``False`` otherwise
    (including connection errors).
    """
    try:
        client = await get_redis()
        deleted = await client.delete(key)
        if deleted:
            logger.debug("Cache DELETE — key removed", key=key)
        else:
            logger.debug("Cache DELETE — key not found", key=key)
        return bool(deleted)
    except RedisConnectionError as exc:
        logger.warning("Redis connection error during cache_delete", key=key, error=str(exc))
        return False
    except RedisError as exc:
        logger.error("Redis error during cache_delete", key=key, error=str(exc))
        return False


async def cache_exists(key: str) -> bool:
    """Return ``True`` if *key* exists in Redis."""
    try:
        client = await get_redis()
        return bool(await client.exists(key))
    except RedisError as exc:
        logger.warning("Redis error during cache_exists", key=key, error=str(exc))
        return False
