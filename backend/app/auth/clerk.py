"""Clerk JWT authentication helpers for CyberSentinel AI.

Clerk issues RS256-signed JWTs.  This module:
1. Fetches the JWKS endpoint once per hour (cached in Redis).
2. Verifies the incoming JWT signature and standard claims.
3. Extracts the Clerk user_id, email, and role from the token payload.
4. Exposes a FastAPI dependency `get_current_user` for use in route handlers.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx
import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.redis_client import cache_get, cache_set

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JWKS_CACHE_KEY = "clerk:jwks"
JWKS_TTL = 3600  # 1 hour
JWKS_URL = "https://api.clerk.dev/v1/jwks"

# FastAPI bearer scheme (auto_error=False so we can return a custom 401)
_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# JWKS fetching / caching
# ---------------------------------------------------------------------------

async def _fetch_jwks() -> Dict[str, Any]:
    """Fetch JWKS from Clerk, returning the raw JSON dict."""
    headers: Dict[str, str] = {}
    if settings.CLERK_SECRET_KEY:
        headers["Authorization"] = f"Bearer {settings.CLERK_SECRET_KEY}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(JWKS_URL, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def get_jwks() -> Dict[str, Any]:
    """Return the JWKS, loading from Redis cache when available."""
    cached = await cache_get(JWKS_CACHE_KEY)
    if cached is not None:
        logger.debug("JWKS loaded from cache")
        return cached

    logger.info("Fetching fresh JWKS from Clerk", url=JWKS_URL)
    try:
        jwks = await _fetch_jwks()
        await cache_set(JWKS_CACHE_KEY, jwks, ttl=JWKS_TTL)
        return jwks
    except httpx.HTTPStatusError as exc:
        logger.error("Failed to fetch JWKS from Clerk", status_code=exc.response.status_code)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch authentication keys from Clerk.",
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Network error fetching JWKS from Clerk", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Network error while contacting Clerk.",
        ) from exc


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

async def verify_clerk_token(token: str) -> Dict[str, Any]:
    """Verify a Clerk-issued JWT and return the user info dict.

    Parameters
    ----------
    token:
        Raw Bearer token string (without the ``Bearer `` prefix).

    Returns
    -------
    dict with keys:
        - ``user_id``  — Clerk user ID (``sub`` claim)
        - ``email``    — Primary email address (from ``email`` claim or ``None``)
        - ``role``     — Role string from ``public_metadata.role`` (default ``"analyst"``)
        - ``metadata`` — Full ``public_metadata`` dict
        - ``payload``  — Full decoded payload for downstream use

    Raises
    ------
    fastapi.HTTPException(401)
        If the token is invalid, expired, or the signature cannot be verified.
    """
    jwks = await get_jwks()

    # Resolve the RSA public key that signed this specific token
    try:
        signing_key = _get_signing_key_from_jwks(jwks, token)
    except Exception as exc:
        logger.warning("Failed to resolve signing key", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not resolve JWT signing key.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        payload: Dict[str, Any] = pyjwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=settings.CLERK_JWT_ISSUER if settings.CLERK_JWT_ISSUER else None,
            options={
                "verify_exp": True,
                "verify_iss": bool(settings.CLERK_JWT_ISSUER),
                "verify_aud": False,  # Clerk tokens typically have no audience
            },
        )
    except pyjwt.ExpiredSignatureError as exc:
        logger.warning("Expired Clerk JWT")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except pyjwt.InvalidIssuerError as exc:
        logger.warning("Invalid JWT issuer")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except pyjwt.PyJWTError as exc:
        logger.warning("JWT validation failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id: str = payload.get("sub", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Clerk stores extra info in public_metadata
    public_metadata: Dict[str, Any] = payload.get("public_metadata", {}) or {}
    email: Optional[str] = (
        payload.get("email")
        or payload.get("primary_email_address")
        or None
    )
    role: str = public_metadata.get("role", "analyst")

    logger.debug("Clerk JWT verified", user_id=user_id, role=role)

    return {
        "user_id": user_id,
        "email": email,
        "role": role,
        "metadata": public_metadata,
        "payload": payload,
    }


def _get_signing_key_from_jwks(jwks: Dict[str, Any], token: str) -> Any:
    """Extract the correct signing key from a raw JWKS dict for *token*.

    Uses PyJWT's ``PyJWK`` helpers to match the ``kid`` header.
    """
    # Decode header only (no verification) to get the key id
    unverified_header = pyjwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    keys = jwks.get("keys", [])
    if not keys:
        raise ValueError("JWKS contains no keys")

    for key_data in keys:
        if kid is None or key_data.get("kid") == kid:
            jwk_obj = pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))
            return jwk_obj

    raise ValueError(f"No matching key found in JWKS for kid={kid!r}")


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

_DEV_USER: Dict[str, Any] = {
    "user_id": "dev_user_local",
    "email": "dev@localhost",
    "role": "admin",
    "org_id": "org_dev",
    "metadata": {},
    "payload": {},
}

def _is_clerk_configured() -> bool:
    """Return True only when a real Clerk secret key is present."""
    key = settings.CLERK_SECRET_KEY or ""
    return (
        key.startswith("sk_test_") or key.startswith("sk_live_")
    ) and "your" not in key.lower()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Dict[str, Any]:
    """FastAPI dependency that resolves the authenticated user from a Bearer token.

    In development (Clerk not configured), returns a mock dev user so every
    endpoint remains accessible without a real JWT.

    Usage::

        @router.get("/me")
        async def get_me(user: dict = Depends(get_current_user)):
            return {"user_id": user["user_id"]}

    Raises
    ------
    HTTPException(401)
        If no token is provided or it fails verification (production only).
    """
    # Dev-mode bypass: Clerk keys not set → return mock dev user
    if not _is_clerk_configured():
        logger.debug("Clerk not configured — using dev user bypass")
        return _DEV_USER

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await verify_clerk_token(credentials.credentials)
