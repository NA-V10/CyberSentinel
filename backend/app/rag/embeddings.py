"""
OpenAI embeddings service for CyberSentinel AI.

Wraps the OpenAI async client with:
- Single-text and batch embedding generation
- Automatic retry with exponential back-off (tenacity)
- Structured logging via loguru
"""

from __future__ import annotations

import asyncio
from typing import List

from loguru import logger
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
import logging as _stdlib_logging

from backend.app.core.config import settings

# tenacity uses stdlib logging; bridge to loguru
_tenacity_logger = _stdlib_logging.getLogger("tenacity")


# ---------------------------------------------------------------------------
# Retry decorator factory
# ---------------------------------------------------------------------------

def _build_retry():
    """Return a tenacity ``retry`` decorator configured for OpenAI calls."""
    return retry(
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(_tenacity_logger, _stdlib_logging.WARNING),
        reraise=True,
    )


_openai_retry = _build_retry()


# ---------------------------------------------------------------------------
# EmbeddingService
# ---------------------------------------------------------------------------


class EmbeddingService:
    """Async service for generating OpenAI text embeddings.

    Parameters
    ----------
    api_key:
        OpenAI API key.  Defaults to ``settings.OPENAI_API_KEY``.
    model:
        Embedding model identifier.  Defaults to ``settings.OPENAI_EMBEDDING_MODEL``.
    """

    # Maximum texts per single OpenAI embeddings request
    _BATCH_CHUNK_SIZE: int = 100

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._model = model or settings.OPENAI_EMBEDDING_MODEL
        self._client = AsyncOpenAI(api_key=self._api_key)
        logger.info(
            "EmbeddingService initialised",
            model=self._model,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed_text(self, text: str) -> List[float]:
        """Generate a single embedding vector for *text*.

        Parameters
        ----------
        text:
            The input string to embed.

        Returns
        -------
        list[float]
            Embedding vector (1536-dimensional for ``text-embedding-3-small``).
        """
        if not text or not isinstance(text, str):
            raise ValueError("embed_text requires a non-empty string.")

        text = text.strip().replace("\n", " ")
        logger.debug("Embedding single text", chars=len(text), model=self._model)

        response = await self._embed_with_retry([text])
        embedding: List[float] = response.data[0].embedding
        logger.debug("Embedding generated", dims=len(embedding))
        return embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.

        Automatically chunks the input into slices of up to
        :attr:`_BATCH_CHUNK_SIZE` items to stay within the OpenAI API limits.

        Parameters
        ----------
        texts:
            List of strings to embed.

        Returns
        -------
        list[list[float]]
            Ordered list of embedding vectors, one per input text.
        """
        if not texts:
            return []

        cleaned = [t.strip().replace("\n", " ") for t in texts if t and isinstance(t, str)]
        if not cleaned:
            return []

        logger.info(
            "Batch embedding request",
            total=len(cleaned),
            model=self._model,
        )

        all_embeddings: List[List[float]] = []
        chunks = _chunk_list(cleaned, self._BATCH_CHUNK_SIZE)

        for idx, chunk in enumerate(chunks):
            logger.debug("Processing chunk", chunk_index=idx, chunk_size=len(chunk))
            response = await self._embed_with_retry(chunk)
            # OpenAI returns embeddings in the same order as input
            chunk_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(chunk_embeddings)

        logger.info(
            "Batch embedding complete",
            total_vectors=len(all_embeddings),
        )
        return all_embeddings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _embed_with_retry(self, texts: List[str]):
        """Call the OpenAI embeddings endpoint with automatic retry.

        The actual retry logic lives in a standalone async function so that
        tenacity can wrap it cleanly without issues with method binding.
        """
        return await _call_openai_embed(self._client, self._model, texts)


# ---------------------------------------------------------------------------
# Module-level helper (needed so tenacity can decorate a plain function)
# ---------------------------------------------------------------------------


@_openai_retry
async def _call_openai_embed(client: AsyncOpenAI, model: str, texts: List[str]):
    """Low-level wrapper around the OpenAI embeddings API with tenacity retry."""
    return await client.embeddings.create(input=texts, model=model)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _chunk_list(lst: list, size: int) -> List[list]:
    """Split *lst* into sublists of at most *size* elements."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]
