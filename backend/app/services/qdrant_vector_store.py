from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

import httpx

from ..config import qdrant_url
from ..schemas import Citation, RagChunk, RetrievedChunk, SourceType


def collection_name(run_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", run_id)
    return f"resume_match_{safe}"


def is_available() -> bool:
    try:
        response = httpx.get(f"{qdrant_url()}/collections", timeout=2)
        return response.status_code < 500
    except Exception:
        return False


def ensure_collection(run_id: str, vector_size: int) -> None:
    response = httpx.put(
        f"{qdrant_url()}/collections/{collection_name(run_id)}",
        json={"vectors": {"size": vector_size, "distance": "Cosine"}},
        timeout=10,
    )
    response.raise_for_status()


def upsert_chunks(run_id: str, chunks: Iterable[RagChunk]) -> None:
    chunk_list = [chunk for chunk in chunks if chunk.embedding]
    if not chunk_list:
        return
    ensure_collection(run_id, len(chunk_list[0].embedding or []))
    points = []
    for chunk in chunk_list:
        points.append(
            {
                "id": chunk.chunk_index,
                "vector": chunk.embedding,
                "payload": {
                    "chunk_id": chunk.id,
                    "run_id": chunk.run_id,
                    "source_type": chunk.source_type.value,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                    "page_number": chunk.page_number,
                    "section_name": chunk.section_name,
                    "paragraph_index": chunk.paragraph_index,
                    "chunk_index": chunk.chunk_index,
                    "original_text": chunk.original_text,
                },
            }
        )
    response = httpx.put(
        f"{qdrant_url()}/collections/{collection_name(run_id)}/points",
        params={"wait": "true"},
        json={"points": points},
        timeout=30,
    )
    response.raise_for_status()


def _extract_points(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = payload.get("result", {})
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        points = result.get("points")
        if isinstance(points, list):
            return points
    return []


def query_chunks(run_id: str, query_vector: List[float], source_type: Optional[str], top_k: int) -> List[RetrievedChunk]:
    limit = top_k if not source_type or source_type == "both" else top_k * 4
    response = httpx.post(
        f"{qdrant_url()}/collections/{collection_name(run_id)}/points/query",
        json={"query": query_vector, "limit": limit, "with_payload": True},
        timeout=15,
    )
    response.raise_for_status()
    results: List[RetrievedChunk] = []
    for point in _extract_points(response.json()):
        payload = point.get("payload") or {}
        if source_type and source_type != "both" and payload.get("source_type") != source_type:
            continue
        score = round(float(point.get("score", 0.0)), 4)
        source = SourceType(payload.get("source_type", "resume"))
        metadata = payload.get("metadata") or {}
        location = metadata.get("source_location", payload.get("source_type", "source"))
        citation = Citation(
            source_type=source,
            source_location=location,
            quote=str(payload.get("text", ""))[:300],
            page_number=payload.get("page_number"),
            section_name=payload.get("section_name"),
            paragraph_index=payload.get("paragraph_index"),
            chunk_id=payload.get("chunk_id"),
            similarity_score=score,
        )
        results.append(
            RetrievedChunk(
                chunk_id=payload.get("chunk_id"),
                source_type=source,
                text=payload.get("text", ""),
                similarity_score=score,
                metadata=metadata,
                citation=citation,
            )
        )
        if len(results) >= top_k:
            break
    return results
