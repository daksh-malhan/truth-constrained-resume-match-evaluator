from __future__ import annotations

import os
from typing import Iterable, List, Optional

from .. import database
from ..schemas import Citation, RagChunk, RetrievedChunk, ResumeSection, SourceType
from .embedding_provider import cosine, embed_text, embed_texts
from . import qdrant_vector_store


def vector_store_fallback_enabled() -> bool:
    return os.getenv("ENABLE_VECTOR_STORE_FALLBACK", "true").lower() in {"1", "true", "yes", "on"}


def _chunk_text(text: str, size: int, overlap: int) -> List[str]:
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def build_chunks(run_id: str, sections: List[ResumeSection], job_paragraphs: List[str], chunk_size: int, overlap: int, vector_store_provider: str | None = None) -> List[RagChunk]:
    """Build the source evidence index from original documents only."""
    chunks: List[RagChunk] = []
    chunk_index = 0
    for section in sections:
        for text in _chunk_text(section.text, chunk_size, overlap):
            chunk_id = f"resume_chunk_{chunk_index:04d}"
            chunks.append(
                RagChunk(
                    id=chunk_id,
                    run_id=run_id,
                    source_type=SourceType.resume,
                    text=text,
                    embedding=None,
                    metadata={"source_location": f"{section.section_name} section, page {section.page_number}"},
                    page_number=section.page_number,
                    section_name=section.section_name,
                    chunk_index=chunk_index,
                    original_text=text,
                )
            )
            chunk_index += 1
    for pidx, paragraph in enumerate(job_paragraphs, start=1):
        for text in _chunk_text(paragraph, chunk_size, overlap):
            chunk_id = f"jd_chunk_{chunk_index:04d}"
            chunks.append(
                RagChunk(
                    id=chunk_id,
                    run_id=run_id,
                    source_type=SourceType.job_description,
                    text=text,
                    embedding=None,
                    metadata={"source_location": f"Requirements paragraph {pidx}"},
                    paragraph_index=pidx,
                    chunk_index=chunk_index,
                    original_text=text,
                )
            )
            chunk_index += 1
    # Generated recommendations are intentionally excluded here. The vector index is
    # reserved for source-of-truth resume and job-description chunks.
    embeddings = embed_texts([chunk.text for chunk in chunks])
    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding
    database.save_chunks([c.model_dump(mode="json") for c in chunks])
    provider = (vector_store_provider or os.getenv("VECTOR_STORE_PROVIDER", "faiss")).lower()
    if provider == "qdrant":
        try:
            qdrant_vector_store.upsert_chunks(run_id, chunks)
        except Exception:
            if not vector_store_fallback_enabled():
                raise
    return chunks


def retrieve(run_id: str, query: str, source_type: Optional[str] = None, top_k: int = 5, vector_store_provider: str | None = None) -> List[RetrievedChunk]:
    query_embedding = embed_text(query)
    provider = (vector_store_provider or os.getenv("VECTOR_STORE_PROVIDER", "faiss")).lower()
    if provider == "qdrant":
        try:
            qdrant_results = qdrant_vector_store.query_chunks(run_id, query_embedding, source_type, top_k)
            if qdrant_results:
                return qdrant_results
        except Exception:
            if not vector_store_fallback_enabled():
                raise

    # SQLite stores the same source chunks as a local, deterministic fallback when
    # Qdrant is unavailable or has not returned results for a run.
    chunks = database.fetch_chunks(run_id)
    scored = []
    for chunk in chunks:
        if source_type and source_type != "both" and chunk["source_type"] != source_type:
            continue
        if not chunk.get("embedding"):
            continue
        scored.append((cosine(query_embedding, chunk["embedding"]), chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    results: List[RetrievedChunk] = []
    for score, chunk in scored[:top_k]:
        location = chunk["metadata"].get("source_location", chunk["source_type"])
        citation = Citation(
            source_type=chunk["source_type"],
            source_location=location,
            quote=chunk["text"][:300],
            page_number=chunk.get("page_number"),
            section_name=chunk.get("section_name"),
            paragraph_index=chunk.get("paragraph_index"),
            chunk_id=chunk["id"],
            similarity_score=round(float(score), 4),
        )
        results.append(
            RetrievedChunk(
                chunk_id=chunk["id"],
                source_type=chunk["source_type"],
                text=chunk["text"],
                similarity_score=round(float(score), 4),
                metadata=chunk["metadata"],
                citation=citation,
            )
        )
    return results
