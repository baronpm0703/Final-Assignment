"""Embedder implementations for the RAG knowledge pipeline.

Provides a Protocol-based interface so KnowledgeService works with any embedder.
Two concrete implementations:
  - HashingEmbedder: deterministic, zero-cost (offline, no API calls)
  - OpenAIEmbedder: calls OpenAI Embeddings API for high-quality semantic vectors
"""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Protocol

import openai

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    """Protocol that all embedders must satisfy."""

    @property
    def dimensions(self) -> int: ...

    def embed(self, text: str) -> list[float]: ...


# ── HashingEmbedder (offline, deterministic) ──────────────────────────────────


class HashingEmbedder:
    """Deterministic hashing-based embedder. Zero API cost, fast, but low semantic quality."""

    def __init__(self, dimensions: int = 128) -> None:
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in self._tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _tokens(self, text: str) -> list[str]:
        normalized = "".join(char.lower() if char.isalnum() else " " for char in text)
        return [token for token in normalized.split() if token]


# ── OpenAIEmbedder (API-based, high semantic quality) ─────────────────────────


class OpenAIEmbedder:
    """Embedder using OpenAI's text-embedding API (e.g. text-embedding-3-small).

    Produces high-quality semantic vectors suitable for cosine similarity search.
    Requires a valid OPENAI_API_KEY.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required for OpenAIEmbedder")
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        """Embed a single text string via OpenAI API."""
        text = text.strip()
        if not text:
            return [0.0] * self._dimensions

        response = self._client.embeddings.create(
            input=text,
            model=self._model,
            dimensions=self._dimensions,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call (more efficient for bulk ingestion)."""
        cleaned = [t.strip() or " " for t in texts]
        response = self._client.embeddings.create(
            input=cleaned,
            model=self._model,
            dimensions=self._dimensions,
        )
        return [item.embedding for item in response.data]


# ── Utilities ─────────────────────────────────────────────────────────────────


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(
        left_value * right_value for left_value, right_value in zip(left, right, strict=False)
    )
