from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .schemas import RunConfig

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = Path(os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}").replace("sqlite:///", ""))
VERSION = "0.1.0"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def default_config() -> RunConfig:
    provider = os.getenv("VECTOR_STORE_PROVIDER", "faiss")
    if provider not in {"qdrant", "chroma", "faiss"}:
        provider = "faiss"
    embedding_model = os.getenv("EMBEDDING_MODEL")
    if not embedding_model:
        embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "mxbai-embed-large:latest") if os.getenv("EMBEDDING_PROVIDER", "mock").lower() == "ollama" else "mock-hashing-embedding"
    return RunConfig(
        embedding_model=embedding_model,
        vector_store_provider=provider,  # type: ignore[arg-type]
    )


def merge_config(saved: Optional[Dict[str, Any]] = None, overrides: Optional[Dict[str, Any]] = None, threshold: Optional[float] = None) -> RunConfig:
    data = default_config().model_dump()
    if saved:
        data.update(saved)
    if overrides:
        data.update(overrides)
    if threshold is not None:
        data["threshold_score"] = threshold
    return RunConfig(**data)


def parse_json_overrides(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("config_overrides must be a JSON object")
    return loaded


def max_upload_bytes() -> int:
    mb = int(os.getenv("MAX_UPLOAD_MB", "8"))
    return mb * 1024 * 1024


def mock_mode_enabled() -> bool:
    return os.getenv("ENABLE_MOCK_MODE", "true").lower() in {"1", "true", "yes", "on"} or not os.getenv("OPENAI_API_KEY")


def ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
