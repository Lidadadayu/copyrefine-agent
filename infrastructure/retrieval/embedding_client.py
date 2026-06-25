from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Iterable, List

import requests
from loguru import logger

from config.settings import get_settings


class HashEmbeddingFunction:
    """
    Chroma-compatible deterministic fallback embedding function.

    It keeps retrieval available when the external embedding service is not
    configured or temporarily unavailable. Production deployments should prefer
    OpenAICompatibleEmbeddingFunction with text-embedding-v3.
    """

    def __init__(self, dimensions: int = 64, salt: str = "contentpilot_hash_embedding") -> None:
        self.dimensions = int(dimensions)
        self.salt = str(salt)

    def name(self) -> str:
        return f"hash_embedding_{self.dimensions}"

    def get_config(self) -> Dict[str, Any]:
        return {"dimensions": self.dimensions, "salt": self.salt}

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "HashEmbeddingFunction":
        return HashEmbeddingFunction(
            dimensions=int(config.get("dimensions", 64)),
            salt=str(config.get("salt", "contentpilot_hash_embedding")),
        )

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> List[str]:
        return ["cosine", "l2", "ip"]

    def validate_config_update(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        old_dim = int(old_config.get("dimensions", self.dimensions))
        new_dim = int(new_config.get("dimensions", self.dimensions))
        if old_dim != new_dim:
            raise ValueError("HashEmbeddingFunction dimensions cannot be changed for an existing collection.")

    def __call__(self, input: List[str]) -> List[List[float]]:  # noqa: A002
        return self.embed_documents(input)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compatibility with LangChain-style embedding interfaces used by some Chroma versions."""
        return [self._embed(str(text or "")) for text in texts]

    def embed_query(self, text: str | None = None, input: Any = None) -> Any:  # noqa: A002
        """Support LangChain-style and Chroma 1.5 keyword query calls."""
        if input is not None:
            values = input if isinstance(input, list) else [input]
            return self.embed_documents([str(value or "") for value in values])
        return self._embed(str(text or ""))

    def _embed(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        compact = "".join(text.lower().split())

        tokens: List[str] = []
        tokens.extend(text.lower().split())
        tokens.extend(compact[i : i + 2] for i in range(max(len(compact) - 1, 0)))
        tokens.extend(compact[i : i + 3] for i in range(max(len(compact) - 2, 0)))

        for token in tokens:
            digest = hashlib.md5(f"{self.salt}:{token}".encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self.dimensions
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vector[idx] += sign

        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class OpenAICompatibleEmbeddingFunction:
    """
    Chroma-compatible embedding function for OpenAI-compatible /embeddings APIs.

    Default target is DashScope compatible-mode text-embedding-v3:
    https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "text-embedding-v3",
        timeout: int = 60,
        batch_size: int = 16,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.strip()
        self.model = model.strip() or "text-embedding-v3"
        self.timeout = int(timeout)
        self.batch_size = max(1, int(batch_size))

    def name(self) -> str:
        safe_model = "".join(ch if ch.isalnum() else "_" for ch in self.model.lower()).strip("_")
        return safe_model or "text_embedding_v3"

    def get_config(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "batch_size": self.batch_size,
        }

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "OpenAICompatibleEmbeddingFunction":
        settings = get_settings()
        return OpenAICompatibleEmbeddingFunction(
            api_key=settings.embedding_api_key or settings.llm_api_key,
            base_url=str(config.get("base_url") or settings.embedding_base_url),
            model=str(config.get("model") or settings.embedding_model),
            timeout=int(config.get("timeout") or settings.embedding_timeout),
            batch_size=int(config.get("batch_size") or settings.embedding_batch_size),
        )

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> List[str]:
        return ["cosine", "l2", "ip"]

    def validate_config_update(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        if old_config.get("model") != new_config.get("model"):
            raise ValueError("Embedding model cannot be changed for an existing Chroma collection.")

    def __call__(self, input: List[str]) -> List[List[float]]:  # noqa: A002
        return self.embed_documents(input)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compatibility with LangChain-style embedding interfaces used by some Chroma versions."""
        normalized = [str(text or "") for text in texts]
        vectors: List[List[float]] = []
        for batch in _chunked(normalized, self.batch_size):
            vectors.extend(self._embed_batch(batch))
        return vectors

    def embed_query(self, text: str | None = None, input: Any = None) -> Any:  # noqa: A002
        """Support LangChain-style and Chroma 1.5 keyword query calls."""
        if input is not None:
            values = input if isinstance(input, list) else [input]
            return self.embed_documents([str(value or "") for value in values])

        vectors = self.embed_documents([str(text or "")])
        if not vectors:
            raise RuntimeError("Embedding query returned no vectors.")
        return vectors[0]

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            raise RuntimeError("Embedding API key is missing.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "input": texts}

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()
        rows = data.get("data") or []
        rows = sorted(rows, key=lambda item: int(item.get("index", 0)))
        vectors = [row.get("embedding") for row in rows]

        if len(vectors) != len(texts) or not all(isinstance(vec, list) for vec in vectors):
            raise RuntimeError("Invalid embedding response format.")

        return [[float(x) for x in vec] for vec in vectors]


def get_embedding_function() -> Any:
    """
    Return the configured Chroma embedding function.

    When EMBEDDING_PROVIDER is mock/hash/empty or the API key is missing, the
    system falls back to HashEmbeddingFunction, keeping local development usable.
    """

    settings = get_settings()
    provider = (settings.embedding_provider or "").lower().strip()
    api_key = settings.embedding_api_key or settings.llm_api_key

    if provider in {"dashscope", "openai", "openai_compatible"} and api_key:
        return OpenAICompatibleEmbeddingFunction(
            api_key=api_key,
            base_url=settings.embedding_base_url,
            model=settings.embedding_model,
            timeout=settings.embedding_timeout,
            batch_size=settings.embedding_batch_size,
        )

    if provider and provider not in {"mock", "hash", "local"}:
        logger.warning("Unsupported EMBEDDING_PROVIDER={}, fallback to hash embedding.", provider)

    return HashEmbeddingFunction(dimensions=settings.hash_embedding_dimensions)


def _chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
