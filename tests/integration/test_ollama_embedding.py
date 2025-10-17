"""
Integration tests for Ollama embedding adapter.
Tests the OllamaEmbeddingAdapter with real Ollama service (or mocked).
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.cage.embedding_adapters import (
    OllamaEmbeddingAdapter,
    OpenAIEmbeddingAdapter,
    make_embedding_adapter,
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestOllamaEmbeddingAdapter:
    """Integration tests for OllamaEmbeddingAdapter."""

    @pytest.fixture  # type: ignore[misc]
    def ollama_adapter(self) -> OllamaEmbeddingAdapter:
        """Create an Ollama adapter instance for testing."""
        return OllamaEmbeddingAdapter(
            base_url="http://localhost:11434",
            model="bge-code-v1",
            normalize=True,
        )

    def test_adapter_initialization(
        self, ollama_adapter: OllamaEmbeddingAdapter
    ) -> None:
        """Test that adapter initializes with correct parameters."""
        assert ollama_adapter.base_url == "http://localhost:11434"
        assert ollama_adapter.model == "bge-code-v1"
        assert ollama_adapter.normalize is True
        assert ollama_adapter.dimension() == 768

    def test_adapter_name(self, ollama_adapter: OllamaEmbeddingAdapter) -> None:
        """Test that adapter returns correct name."""
        assert ollama_adapter.name() == "ollama-bge-code-v1"

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_embed_single_chunk_mocked(
        self, ollama_adapter: OllamaEmbeddingAdapter
    ) -> None:
        """Test embedding a single chunk with mocked response."""
        test_chunk = "def hello_world():\n    print('Hello, World!')"
        mock_embedding = [0.1] * 768  # Simulated 768-dim embedding

        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": mock_embedding}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            result = await ollama_adapter.embed([test_chunk])

            # Verify result structure
            assert "vectors" in result
            assert "dim" in result
            assert len(result["vectors"]) == 1
            assert len(result["vectors"][0]) == 768
            assert result["dim"] == 768

            # Verify API call
            mock_async_client.post.assert_called_once()
            call_args = mock_async_client.post.call_args
            assert call_args[0][0] == "http://localhost:11434/api/embeddings"
            assert call_args[1]["json"]["model"] == "bge-code-v1"
            assert call_args[1]["json"]["prompt"] == [test_chunk]

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_embed_multiple_chunks_mocked(
        self, ollama_adapter: OllamaEmbeddingAdapter
    ) -> None:
        """Test embedding multiple chunks with mocked response."""
        test_chunks = [
            "def function1(): pass",
            "def function2(): pass",
            "def function3(): pass",
        ]
        mock_embeddings = [[0.1] * 768, [0.2] * 768, [0.3] * 768]

        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": mock_embeddings}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            result = await ollama_adapter.embed(test_chunks)

            # Verify result structure
            assert "vectors" in result
            assert "dim" in result
            assert len(result["vectors"]) == 3
            assert all(len(v) == 768 for v in result["vectors"])
            assert result["dim"] == 768

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_embed_with_normalization(
        self, ollama_adapter: OllamaEmbeddingAdapter
    ) -> None:
        """Test that normalization is applied correctly."""
        test_chunk = "test code"
        # Create unnormalized vector (length != 1)
        unnormalized = [3.0, 4.0] + [0.0] * 766
        mock_embeddings = [unnormalized]

        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": mock_embeddings}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            result = await ollama_adapter.embed([test_chunk])

            # Calculate expected normalized values
            # Original: [3.0, 4.0, 0, 0, ...], norm = 5.0
            # Normalized: [0.6, 0.8, 0, 0, ...]
            assert result["vectors"][0][0] == pytest.approx(0.6, abs=1e-5)
            assert result["vectors"][0][1] == pytest.approx(0.8, abs=1e-5)

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_embed_without_normalization(self) -> None:
        """Test embedding without normalization."""
        adapter = OllamaEmbeddingAdapter(
            base_url="http://localhost:11434",
            model="bge-code-v1",
            normalize=False,
        )
        test_chunk = "test code"
        unnormalized = [3.0, 4.0] + [0.0] * 766
        mock_embeddings = [unnormalized]

        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": mock_embeddings}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_async_client

            result = await adapter.embed([test_chunk])

            # Vectors should not be normalized
            assert result["vectors"][0][0] == 3.0
            assert result["vectors"][0][1] == 4.0

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_embed_error_handling(
        self, ollama_adapter: OllamaEmbeddingAdapter
    ) -> None:
        """Test error handling when Ollama service is unavailable."""
        test_chunk = "test code"

        with patch("httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.__aenter__.return_value = mock_async_client
            mock_async_client.__aexit__.return_value = None
            mock_async_client.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )
            mock_client.return_value = mock_async_client

            with pytest.raises(RuntimeError) as exc_info:
                await ollama_adapter.embed([test_chunk])
            assert "Failed to generate Ollama embeddings" in str(exc_info.value)


class TestOpenAIEmbeddingAdapter:
    """Integration tests for OpenAIEmbeddingAdapter."""

    @pytest.fixture  # type: ignore[misc]
    def openai_adapter(self) -> OpenAIEmbeddingAdapter:
        """Create an OpenAI adapter instance for testing."""
        return OpenAIEmbeddingAdapter(
            api_key="test-api-key", model="text-embedding-3-small"
        )

    def test_adapter_initialization(
        self, openai_adapter: OpenAIEmbeddingAdapter
    ) -> None:
        """Test that adapter initializes with correct parameters."""
        assert openai_adapter.model == "text-embedding-3-small"
        assert openai_adapter.dimension() == 1536

    def test_adapter_name(self, openai_adapter: OpenAIEmbeddingAdapter) -> None:
        """Test that adapter returns correct name."""
        assert openai_adapter.name() == "openai-text-embedding-3-small"


class TestEmbeddingAdapterFactory:
    """Integration tests for embedding adapter factory."""

    def test_make_adapter_local_default(self) -> None:
        """Test factory creates local adapter by default."""
        with patch.dict(os.environ, {}, clear=True):
            adapter = make_embedding_adapter()
            assert isinstance(adapter, OllamaEmbeddingAdapter)
            assert adapter.name() == "ollama-bge-code-v1"

    def test_make_adapter_local_explicit(self) -> None:
        """Test factory creates local adapter when explicitly requested."""
        adapter = make_embedding_adapter("local")
        assert isinstance(adapter, OllamaEmbeddingAdapter)
        assert adapter.dimension() == 768

    def test_make_adapter_openai(self) -> None:
        """Test factory creates OpenAI adapter when requested."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            adapter = make_embedding_adapter("openai")
            assert isinstance(adapter, OpenAIEmbeddingAdapter)
            assert adapter.dimension() == 1536

    def test_make_adapter_from_env_local(self) -> None:
        """Test factory reads provider from environment variable."""
        with patch.dict(
            os.environ,
            {"EMBEDDING_PROVIDER": "local", "OLLAMA_BASE_URL": "http://test:11434"},
        ):
            adapter = make_embedding_adapter()
            assert isinstance(adapter, OllamaEmbeddingAdapter)
            assert adapter.base_url == "http://test:11434"

    def test_make_adapter_from_env_openai(self) -> None:
        """Test factory creates OpenAI adapter from environment."""
        with patch.dict(
            os.environ,
            {"EMBEDDING_PROVIDER": "openai", "OPENAI_API_KEY": "env-key"},
        ):
            adapter = make_embedding_adapter()
            assert isinstance(adapter, OpenAIEmbeddingAdapter)

    def test_make_adapter_custom_ollama_model(self) -> None:
        """Test factory with custom Ollama model."""
        with patch.dict(
            os.environ,
            {"EMBEDDING_PROVIDER": "local", "EMBEDDING_MODEL_LOCAL": "custom-model"},
        ):
            adapter = make_embedding_adapter()
            assert isinstance(adapter, OllamaEmbeddingAdapter)
            assert adapter.model == "custom-model"

    def test_make_adapter_custom_openai_model(self) -> None:
        """Test factory with custom OpenAI model."""
        with patch.dict(
            os.environ,
            {
                "EMBEDDING_PROVIDER": "openai",
                "OPENAI_API_KEY": "test-key",
                "EMBEDDING_MODEL_OPENAI": "text-embedding-ada-002",
            },
        ):
            adapter = make_embedding_adapter()
            assert isinstance(adapter, OpenAIEmbeddingAdapter)
            assert adapter.model == "text-embedding-ada-002"

    def test_make_adapter_case_insensitive(self) -> None:
        """Test that provider selection is case-insensitive."""
        adapter_upper = make_embedding_adapter("LOCAL")
        adapter_mixed = make_embedding_adapter("Local")
        adapter_lower = make_embedding_adapter("local")

        assert all(
            isinstance(a, OllamaEmbeddingAdapter)
            for a in [adapter_upper, adapter_mixed, adapter_lower]
        )


class TestEmbeddingCompatibility:
    """Integration tests for embedding adapter compatibility."""

    @pytest.mark.asyncio  # type: ignore[misc]
    async def test_ollama_openai_dimension_difference(self) -> None:
        """Test that Ollama and OpenAI adapters have different dimensions."""
        ollama = OllamaEmbeddingAdapter()
        openai = OpenAIEmbeddingAdapter(api_key="test")

        assert ollama.dimension() == 768
        assert openai.dimension() == 1536
        assert ollama.dimension() != openai.dimension()

    def test_adapter_interface_consistency(self) -> None:
        """Test that all adapters implement the same interface."""
        ollama = OllamaEmbeddingAdapter()
        openai = OpenAIEmbeddingAdapter(api_key="test")

        # Check required methods exist
        for adapter in [ollama, openai]:
            assert hasattr(adapter, "embed")
            assert hasattr(adapter, "name")
            assert hasattr(adapter, "dimension")
            assert callable(adapter.embed)
            assert callable(adapter.name)
            assert callable(adapter.dimension)

    def test_adapter_name_format(self) -> None:
        """Test that adapter names follow consistent format."""
        ollama = OllamaEmbeddingAdapter(model="test-model")
        openai = OpenAIEmbeddingAdapter(api_key="test", model="test-embedding")

        assert ollama.name().startswith("ollama-")
        assert openai.name().startswith("openai-")
        assert "-" in ollama.name()
        assert "-" in openai.name()
