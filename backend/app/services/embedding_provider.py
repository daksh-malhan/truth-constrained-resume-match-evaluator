from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Iterable, List

import httpx

from ..config import ollama_base_url


def mock_embed_text(text: str, dimensions: int = 128) -> List[float]:
    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-zA-Z0-9+#.]+", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dimensions
        vector[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


def _ollama_embedding_model_chain() -> list[str]:
    primary = os.getenv("OLLAMA_EMBEDDING_MODEL", "mxbai-embed-large:latest")
    fallbacks = os.getenv("OLLAMA_EMBEDDING_FALLBACK_MODELS", "nomic-embed-text,snowflake-arctic-embed:latest")
    models = [primary] + [model.strip() for model in fallbacks.split(",") if model.strip()]
    deduped: list[str] = []
    for model in models:
        if model not in deduped:
            deduped.append(model)
    return deduped


def _ollama_embed_with_model(text: str, model: str) -> List[float]:
    response = httpx.post(
        f"{ollama_base_url()}/api/embed",
        json={"model": model, "input": text},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    embeddings = payload.get("embeddings") or []
    if not embeddings:
        raise ValueError("Ollama returned no embeddings")
    vector = embeddings[0]
    norm = math.sqrt(sum(float(x) * float(x) for x in vector)) or 1.0
    return [float(x) / norm for x in vector]


def _normalize_vector(vector: List[float]) -> List[float]:
    norm = math.sqrt(sum(float(x) * float(x) for x in vector)) or 1.0
    return [float(x) / norm for x in vector]


def _ollama_embed_batch_with_model(texts: List[str], model: str) -> List[List[float]]:
    response = httpx.post(
        f"{ollama_base_url()}/api/embed",
        json={"model": model, "input": texts},
        timeout=max(60, 15 * len(texts)),
    )
    response.raise_for_status()
    embeddings = response.json().get("embeddings") or []
    if len(embeddings) != len(texts):
        raise ValueError(f"Ollama returned {len(embeddings)} embeddings for {len(texts)} texts")
    return [_normalize_vector(vector) for vector in embeddings]


def ollama_embed_text(text: str) -> List[float]:
    errors: list[str] = []
    for model in _ollama_embedding_model_chain():
        try:
            return _ollama_embed_with_model(text, model)
        except Exception as exc:
            errors.append(f"{model}: {exc}")
    raise ValueError(f"All Ollama embedding models failed: {' | '.join(errors)}")


def embed_texts(texts: List[str], dimensions: int = 128) -> List[List[float]]:
    if not texts:
        return []
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").lower()
    if provider == "ollama":
        errors: list[str] = []
        for model in _ollama_embedding_model_chain():
            try:
                batch_size = int(os.getenv("OLLAMA_EMBEDDING_BATCH_SIZE", "32"))
                embeddings: List[List[float]] = []
                for start in range(0, len(texts), batch_size):
                    embeddings.extend(_ollama_embed_batch_with_model(texts[start : start + batch_size], model))
                return embeddings
            except Exception as exc:
                errors.append(f"{model}: {exc}")
        if os.getenv("ENABLE_MOCK_FALLBACK", "false").lower() not in {"1", "true", "yes", "on"}:
            raise ValueError(f"All Ollama batch embedding models failed: {' | '.join(errors)}")
    return [mock_embed_text(text, dimensions) for text in texts]


def embed_text(text: str, dimensions: int = 128) -> List[float]:
    provider = os.getenv("EMBEDDING_PROVIDER", "mock").lower()
    if provider == "ollama":
        try:
            return ollama_embed_text(text)
        except Exception:
            if os.getenv("ENABLE_MOCK_FALLBACK", "false").lower() in {"1", "true", "yes", "on"}:
                return mock_embed_text(text, dimensions)
            raise
    return mock_embed_text(text, dimensions)


def cosine(a: Iterable[float], b: Iterable[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
