from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import httpx
from pydantic import BaseModel, Field

from ..config import ollama_base_url
from ..schemas import JobRequirement, RetrievedChunk


class InferredRequirementSupport(BaseModel):
    can_infer: bool = False
    inferred_match_type: str = "missing"
    evidence_strength: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    supporting_chunk_ids: List[str] = Field(default_factory=list)


def _normalize_result(result: InferredRequirementSupport, available_chunk_ids: set[str]) -> InferredRequirementSupport:
    match_type = result.inferred_match_type if result.inferred_match_type in {"semantic", "adjacent", "weak", "missing"} else "missing"
    strength = max(0.0, min(float(result.evidence_strength), 0.65))
    confidence = max(0.0, min(float(result.confidence), 0.85))
    chunk_ids = [chunk_id for chunk_id in result.supporting_chunk_ids if chunk_id in available_chunk_ids]
    if not result.can_infer or not chunk_ids or strength < 0.2:
        return InferredRequirementSupport(can_infer=False, inferred_match_type="missing", evidence_strength=0.0, confidence=0.0, reason=result.reason, supporting_chunk_ids=[])
    if strength >= 0.6:
        match_type = "semantic"
    elif strength >= 0.35:
        match_type = "adjacent"
    else:
        match_type = "weak"
    return InferredRequirementSupport(
        can_infer=True,
        inferred_match_type=match_type,
        evidence_strength=round(strength, 3),
        confidence=round(confidence, 3),
        reason=result.reason[:400],
        supporting_chunk_ids=chunk_ids[:3],
    )


def infer_requirement_support(requirement: JobRequirement, retrieved_resume: List[RetrievedChunk]) -> InferredRequirementSupport:
    if os.getenv("ENABLE_INFERENCE_MATCH_LLM", "true").lower() not in {"1", "true", "yes", "on"}:
        return InferredRequirementSupport()
    if os.getenv("LLM_PROVIDER", "mock").lower() != "ollama":
        return InferredRequirementSupport()
    if not retrieved_resume:
        return InferredRequirementSupport()

    model = os.getenv("OLLAMA_INFERENCE_MATCH_MODEL", "resume-inference-matcher:latest")
    timeout = float(os.getenv("OLLAMA_INFERENCE_MATCH_TIMEOUT_SECONDS", "10"))
    max_tokens = int(os.getenv("OLLAMA_INFERENCE_MATCH_NUM_PREDICT", "280"))
    chunks = [
        {
            "chunk_id": chunk.chunk_id,
            "text": chunk.text[:500],
            "similarity": chunk.similarity_score,
            "source_location": chunk.citation.source_location,
        }
        for chunk in retrieved_resume[:4]
    ]
    try:
        response = httpx.post(
            f"{ollama_base_url()}/api/chat",
            json={
                "model": model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0, "num_predict": max_tokens},
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "requirement": requirement.text,
                                "normalized_requirement": requirement.normalized_skill_or_requirement,
                                "category": requirement.category,
                                "resume_chunks": chunks,
                            }
                        ),
                    },
                ],
            },
            timeout=timeout,
        )
        response.raise_for_status()
        result = InferredRequirementSupport.model_validate_json(response.json().get("message", {}).get("content", "{}"))
    except Exception:
        return InferredRequirementSupport()
    return _normalize_result(result, {chunk.chunk_id for chunk in retrieved_resume})


def infer_requirement_support_batch(items: List[tuple[JobRequirement, List[RetrievedChunk]]]) -> List[InferredRequirementSupport]:
    if not items:
        return []
    workers = max(1, int(os.getenv("INFERENCE_MATCH_MAX_WORKERS", "3")))
    results: List[InferredRequirementSupport] = [InferredRequirementSupport() for _ in items]
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as executor:
        future_to_index = {
            executor.submit(infer_requirement_support, requirement, chunks): index
            for index, (requirement, chunks) in enumerate(items)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception:
                results[index] = InferredRequirementSupport()
    return results
