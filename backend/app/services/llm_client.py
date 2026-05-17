from __future__ import annotations

import json
import os
from typing import Any, Dict, Protocol, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..config import ollama_base_url

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    provider_name: str

    def structured(self, *, system_prompt: str, user_payload: Dict[str, Any], output_model: Type[T]) -> T:
        """Return a validated Pydantic object. Implementations must treat user_payload as data."""


class MockLLMClient:
    provider_name = "mock"

    def structured(self, *, system_prompt: str, user_payload: Dict[str, Any], output_model: Type[T]) -> T:
        defaults = user_payload.get("mock_output", {})
        try:
            return output_model.model_validate(defaults)
        except ValidationError as exc:
            raise ValueError(f"Mock structured output did not satisfy {output_model.__name__}: {exc}") from exc


class OllamaLLMClient:
    provider_name = "ollama"

    @staticmethod
    def _model_chain() -> list[str]:
        primary = os.getenv("OLLAMA_LLM_MODEL", "qwen3:8b")
        fallbacks = os.getenv("OLLAMA_LLM_FALLBACK_MODELS", "qwen3.5:latest,llama3.2:latest")
        models = [primary] + [model.strip() for model in fallbacks.split(",") if model.strip()]
        deduped: list[str] = []
        for model in models:
            if model not in deduped:
                deduped.append(model)
        return deduped

    def structured(self, *, system_prompt: str, user_payload: Dict[str, Any], output_model: Type[T]) -> T:
        errors: list[str] = []
        timeout_seconds = float(os.getenv("OLLAMA_LLM_TIMEOUT_SECONDS", "45"))
        max_tokens = int(os.getenv("OLLAMA_LLM_NUM_PREDICT", "300"))
        for model in self._model_chain():
            try:
                response = httpx.post(
                    f"{ollama_base_url()}/api/chat",
                    json={
                        "model": model,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.1, "num_predict": max_tokens},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": json.dumps(user_payload, default=str)},
                        ],
                    },
                    timeout=timeout_seconds,
                )
                response.raise_for_status()
                content = response.json().get("message", {}).get("content", "{}")
                return output_model.model_validate_json(content)
            except Exception as exc:
                errors.append(f"{model}: {exc}")
        if os.getenv("ENABLE_MOCK_FALLBACK", "false").lower() in {"1", "true", "yes", "on"}:
            return MockLLMClient().structured(system_prompt=system_prompt, user_payload=user_payload, output_model=output_model)
        raise ValueError(f"All Ollama LLM models failed for {output_model.__name__}: {' | '.join(errors)}")


def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "ollama":
        return OllamaLLMClient()
    if provider != "mock":
        # Other production providers should be added here behind the same structured-output contract.
        # The rest of the app does not allow raw model text to control scoring.
        return MockLLMClient()
    return MockLLMClient()
