"""Embedding provider abstractions for vector generation.

Defines the ``EmbeddingProvider`` interface and concrete implementations:
OpenAI (remote API) and Mock (for testing/development).  The local
sentence-transformers provider is available as an optional dependency.

Use ``get_embedding_provider()`` to select the active backend based on
application settings.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


# ── Abstract provider ────────────────────────────────────────────────────────


class EmbeddingProvider(ABC):
    """Abstract base for embedding vector providers."""

    @abstractmethod
    async def generate_embeddings(
        self,
        texts: Sequence[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts.

        Args:
            texts: List of input strings to embed.
            model: Optional model override (provider-specific).

        Returns:
            List of float vectors, one per input text.
        """
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the embedding vectors."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier for the active embedding model."""
        ...


# ── OpenAI ───────────────────────────────────────────────────────────────────


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding vectors via the OpenAI Embeddings API."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    async def generate_embeddings(
        self,
        texts: Sequence[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        model = model or settings.EMBEDDING_MODEL

        # OpenAI supports up to 2048 inputs per call; split into batches
        batch_size = settings.EMBEDDING_BATCH_SIZE
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self._client.embeddings.create(
                model=model,
                input=list(batch),
            )
            # Responses are returned in the same order as the input
            for data in response.data:
                all_embeddings.append(data.embedding)

        return all_embeddings

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION

    @property
    def model_name(self) -> str:
        return settings.EMBEDDING_MODEL


# ── Local (sentence-transformers) ────────────────────────────────────────────


class LocalEmbeddingProvider(EmbeddingProvider):
    """Embedding vectors via a local sentence-transformers model.

    Requires the ``local`` extra dependency group:
        pip install aevix-backend[local]
    """

    def __init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "LocalEmbeddingProvider requires sentence-transformers. "
                "Install with: pip install aevix-backend[local]"
            ) from exc

        model_name = settings.EMBEDDING_MODEL
        if not model_name or model_name == settings.EMBEDDING_MODEL:
            model_name = "all-MiniLM-L6-v2"
        self._model = SentenceTransformer(str(model_name))
        self._dim = self._model.get_sentence_embedding_dimension()

    async def generate_embeddings(
        self,
        texts: Sequence[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        # sentence-transformers is synchronous; run in a thread pool to
        # avoid blocking the async event loop.
        loop = asyncio.get_running_loop()

        embeddings = await loop.run_in_executor(
            None,
            lambda: self._model.encode(
                list(texts),
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist(),
        )
        return embeddings

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return str(self._model.model_card_data.base_model or "local")


# ── Mock (for development / testing) ─────────────────────────────────────────


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock provider that returns zero vectors for testing.

    The returned vectors have dimension 4 so they are trivially
    distinguishable from real embeddings in assertions.
    """

    def __init__(self) -> None:
        self._dim = 1536

    async def generate_embeddings(
        self,
        texts: Sequence[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        return [[0.0] * self._dim for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "mock"


# ── Factory ──────────────────────────────────────────────────────────────────


# ── Pipeline (lazy import to avoid circular deps with document chunkers) ────


def get_embedding_pipeline(db: AsyncSession) -> EmbeddingPipeline:
    """Return an ``EmbeddingPipeline`` bound to the given DB session."""
    from app.services.embeddings.pipeline import EmbeddingPipeline as _Pipeline

    return _Pipeline(db)


def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider based on settings.

    Priority:
    1. If ``EMBEDDING_PROVIDER`` is ``"local"`` → ``LocalEmbeddingProvider``
    2. If ``EMBEDDING_PROVIDER`` is ``"openai"`` and key set → ``OpenAIEmbeddingProvider``
    3. If ``OPENAI_API_KEY`` is set → ``OpenAIEmbeddingProvider``
    4. Otherwise → ``MockEmbeddingProvider`` (safe for dev/testing)
    """
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "local":
        return LocalEmbeddingProvider()
    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAIEmbeddingProvider()
    if settings.OPENAI_API_KEY:
        return OpenAIEmbeddingProvider()

    return MockEmbeddingProvider()
