from __future__ import annotations

import os

import httpx
from langchain_core.language_models.chat_models import BaseChatModel

from ..config import ollama_base_url


def agent_provider() -> str:
    return os.getenv("AGENT_LLM_PROVIDER", os.getenv("LLM_PROVIDER", "ollama")).lower()


def agent_model_name() -> str:
    # Defaults to a local, tools-capable Ollama model. Any tools-capable model works.
    return os.getenv("OLLAMA_AGENT_MODEL", "qwen2.5:7b-instruct")


_TOOLS_CAPABILITY_CACHE: dict[str, bool] = {}


def _model_supports_native_tools(model: str) -> bool:
    """Ask Ollama whether the model advertises the 'tools' capability (cached per model).

    On any error we assume native support (the common case); structured mode can still
    be forced with OLLAMA_AGENT_TOOL_MODE=structured.
    """
    if model in _TOOLS_CAPABILITY_CACHE:
        return _TOOLS_CAPABILITY_CACHE[model]
    try:
        resp = httpx.post(f"{ollama_base_url()}/api/show", json={"name": model}, timeout=5)
        resp.raise_for_status()
        capabilities = resp.json().get("capabilities", []) or []
        supported = "tools" in capabilities
    except Exception:
        supported = True
    _TOOLS_CAPABILITY_CACHE[model] = supported
    return supported


def get_chat_model(provider: str | None = None) -> BaseChatModel:
    """Return a tool-calling chat model behind one swappable interface.

    Defaults to the existing local Ollama setup. Uses native Ollama function-calling when
    the model supports it; otherwise falls back to a structured-output tool-call parser.
    A hosted provider can be added here later without touching the agent loop.

    OLLAMA_AGENT_TOOL_MODE = auto (default) | native | structured.
    """
    provider = (provider or agent_provider()).lower()
    if provider != "ollama":
        raise ValueError(
            f"Unsupported AGENT_LLM_PROVIDER '{provider}'. Use 'ollama', or inject a "
            f"BaseChatModel via run_coach(chat_model=...)."
        )

    from langchain_ollama import ChatOllama

    model = agent_model_name()
    base_url = ollama_base_url()
    num_predict = int(os.getenv("OLLAMA_AGENT_NUM_PREDICT", "512"))
    mode = os.getenv("OLLAMA_AGENT_TOOL_MODE", "auto").lower()

    use_native = mode == "native" or (mode == "auto" and _model_supports_native_tools(model))
    if use_native:
        return ChatOllama(model=model, base_url=base_url, temperature=0, num_predict=num_predict)

    # Structured-output fallback for models without native tool support.
    from .structured_model import StructuredToolCallingModel

    base = ChatOllama(model=model, base_url=base_url, temperature=0, num_predict=num_predict, format="json")
    return StructuredToolCallingModel(base=base)
