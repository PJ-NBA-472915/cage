"""
Embedding Adapters for RAG System

Provides pluggable embedding providers (OpenAI, Ollama) for the RAG service.
"""

import logging
import os
from abc import ABC, abstractmethod

import httpx
import numpy as np
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class EmbeddingAdapter(ABC):
    """Abstract base class for embedding adapters."""

    @abstractmethod
    async def embed(self, chunks: list[str]) -> dict:
        """
        Generate embeddings for a list of text chunks.

        Args:
            chunks: List of text chunks to embed

        Returns:
            Dictionary with:
                - vectors: List of embedding vectors (List[List[float]])
                - dim: Dimension of embeddings (int)
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """Return the name of the embedding provider."""
        pass

    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass


class OpenAIEmbeddingAdapter(EmbeddingAdapter):
    """OpenAI embedding adapter using text-embedding-3-small."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
    ):
        """
        Initialize OpenAI embedding adapter.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI embedding model name
        """
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self._dimension = 1536  # text-embedding-3-small dimension

        logger.info(f"Initialized OpenAI embedding adapter with model: {model}")

    async def embed(self, chunks: list[str]) -> dict:
        """Generate OpenAI embeddings for text chunks."""
        try:
            response = await self.client.embeddings.create(
                model=self.model, input=chunks
            )

            vectors = [item.embedding for item in response.data]

            logger.info(
                f"Generated {len(vectors)} OpenAI embeddings (dim={self._dimension})"
            )

            return {"vectors": vectors, "dim": self._dimension}

        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            # Return dummy embeddings for fallback
            logger.warning("Using dummy embeddings due to OpenAI API failure")
            dummy_vectors = [[0.0] * self._dimension for _ in chunks]
            return {"vectors": dummy_vectors, "dim": self._dimension}

    def name(self) -> str:
        """Return provider name."""
        return f"openai-{self.model}"

    def dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension


class OllamaEmbeddingAdapter(EmbeddingAdapter):
    """Ollama embedding adapter using bge-code-v1 or other models."""

    def __init__(
        self,
        base_url: str = "http://ollama:11434",
        model: str = "bge-code-v1",
        normalize: bool = True,
    ):
        """
        Initialize Ollama embedding adapter.

        Args:
            base_url: Ollama API base URL
            model: Ollama model name (e.g., bge-code-v1, bge-m3)
            normalize: Whether to L2-normalize embeddings
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.normalize = normalize
        self._dimension = 768  # bge-code-v1 dimension

        logger.info(
            f"Initialized Ollama embedding adapter: {base_url}, model={model}, normalize={normalize}"
        )

    async def embed(self, chunks: list[str]) -> dict:
        """Generate Ollama embeddings for text chunks."""
        try:
            url = f"{self.base_url}/api/embeddings"

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    json={"model": self.model, "prompt": chunks},
                    headers={"Content-Type": "application/json"},
                )

                if not response.is_success:
                    error_msg = f"Ollama embed failed: HTTP {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                data = response.json()

                # Ollama returns {"embedding": [...]} for single prompt
                # or {"embeddings": [[...], [...]]} for multiple prompts
                if "embedding" in data:
                    vectors = [data["embedding"]]
                elif "embeddings" in data:
                    vectors = data["embeddings"]
                else:
                    raise ValueError(f"Unexpected Ollama response format: {data}")

                # Update dimension from actual response
                if vectors:
                    self._dimension = len(vectors[0])

                # Optional L2 normalization for cosine/inner-product equivalence
                if self.normalize:
                    vectors = self._normalize_vectors(vectors)

                logger.info(
                    f"Generated {len(vectors)} Ollama embeddings (dim={self._dimension})"
                )

                return {"vectors": vectors, "dim": self._dimension}

        except Exception as e:
            logger.error(f"Ollama embedding generation failed: {e}")
            raise RuntimeError(
                f"Failed to generate Ollama embeddings. "
                f"Please ensure Ollama is running at {self.base_url} "
                f"and model '{self.model}' is available."
            ) from e

    def _normalize_vectors(self, vectors: list[list[float]]) -> list[list[float]]:
        """L2-normalize vectors for cosine similarity."""
        normalized = []
        for vec in vectors:
            vec_np = np.array(vec, dtype=np.float32)
            norm = np.linalg.norm(vec_np)
            if norm > 0:
                vec_np = vec_np / norm
            normalized.append(vec_np.tolist())
        return normalized

    def name(self) -> str:
        """Return provider name."""
        return f"ollama-{self.model}"

    def dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension


def make_embedding_adapter(
    provider: str | None = None,
) -> EmbeddingAdapter:
    """
    Factory function to create embedding adapter based on configuration.

    Args:
        provider: Embedding provider ('openai' or 'local').
                 Defaults to EMBEDDING_PROVIDER env var or 'local'.

    Returns:
        EmbeddingAdapter instance

    Raises:
        ValueError: If unknown provider specified
        RuntimeError: If provider configuration is invalid
    """
    # Get provider from parameter, env var, or default to 'local'
    provider_str = provider or os.getenv("EMBEDDING_PROVIDER") or "local"
    provider_lower = provider_str.lower()

    logger.info(f"Creating embedding adapter for provider: {provider_lower}")

    if provider_lower == "openai":
        model = os.getenv("EMBEDDING_MODEL_OPENAI", "text-embedding-3-small")
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            logger.warning(
                "OPENAI_API_KEY not set. OpenAI embeddings may fail. "
                "Consider using EMBEDDING_PROVIDER=local"
            )

        return OpenAIEmbeddingAdapter(api_key=api_key, model=model)

    elif provider_lower == "local":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        model = os.getenv("EMBEDDING_MODEL_LOCAL", "bge-code-v1")

        return OllamaEmbeddingAdapter(base_url=base_url, model=model, normalize=True)

    else:
        raise ValueError(
            f"Unknown embedding provider: {provider_lower}. "
            f"Valid options: 'openai', 'local'"
        )
