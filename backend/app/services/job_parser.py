from __future__ import annotations

import re
from typing import List

from ..schemas import JobRequirement
from .skill_normalizer import detect_skills


def parse_job_paragraphs(text: str) -> List[str]:
    chunks = [p.strip(" \n\t-•") for p in re.split(r"\n\s*\n|\n[-•]\s*|\n\d+\.\s+", text) if p.strip()]
    if len(chunks) <= 1:
        chunks = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
    return chunks


def infer_job_title(text: str) -> str | None:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if len(first) <= 80 and any(token in first.lower() for token in ["engineer", "developer", "scientist", "analyst", "manager"]):
        return first
    return None


def _importance(paragraph: str) -> str:
    p = paragraph.lower()
    if any(x in p for x in ["required", "must have", "minimum", "need "]):
        return "must_have"
    if any(x in p for x in ["responsible", "build", "design", "develop", "own "]):
        return "main_responsibility"
    if any(x in p for x in ["preferred", "nice to have", "bonus"]):
        return "preferred"
    return "generic"


def _category(term: str, paragraph: str) -> str:
    p = paragraph.lower()
    if term in {"aws", "gcp", "azure", "docker", "kubernetes", "qdrant", "pinecone", "weaviate", "faiss", "postgresql", "mysql", "sqlite"}:
        return "tool"
    if any(x in p for x in ["degree", "education", "certification", "certified"]):
        return "education"
    if any(x in p for x in ["responsible", "collaborate", "communicate", "design", "build", "develop"]):
        return "responsibility"
    return "technical_skill"


def extract_job_requirements(job_description: str, weights: dict[str, float]) -> List[JobRequirement]:
    paragraphs = parse_job_paragraphs(job_description)
    requirements: List[JobRequirement] = []
    seen: set[str] = set()
    counter = 0
    for idx, paragraph in enumerate(paragraphs):
        skills = detect_skills(paragraph)
        if not skills and len(paragraph.split()) >= 4:
            skills = [paragraph[:80].lower()]
        for skill in skills:
            key = f"{skill}:{idx}"
            if key in seen:
                continue
            seen.add(key)
            importance = _importance(paragraph)
            requirements.append(
                JobRequirement(
                    id=f"job_req_{counter:03d}",
                    text=paragraph,
                    normalized_skill_or_requirement=skill,
                    category=_category(skill, paragraph),  # type: ignore[arg-type]
                    importance=importance,  # type: ignore[arg-type]
                    importance_weight=weights.get(importance, 0.3),
                    source_location=f"Requirements paragraph {idx + 1}",
                    source_quote=paragraph[:300],
                    paragraph_index=idx + 1,
                    confidence=0.8,
                )
            )
            counter += 1
    return requirements

