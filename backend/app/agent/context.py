from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..config import default_config
from ..schemas import JobRequirement, RequirementMatch, ResumeEvidence, ResumeSection, RunConfig, ScoreBreakdown
from ..services.analysis_service import importance_weight_map
from ..services.job_parser import extract_job_requirements, parse_job_paragraphs
from ..services.rag_indexer import build_chunks
from ..services.resume_extractor import extract_resume_evidence
from ..services.scoring_engine import calculate_score, compare_requirements


# Lines that look like resume section headers (short, mostly a known keyword).
_HEADER_KEYWORDS = (
    "summary", "objective", "experience", "work", "employment", "projects",
    "project", "skills", "education", "certification", "certifications", "awards",
)


def _looks_like_header(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 40:
        return False
    lowered = stripped.lower().rstrip(":")
    if lowered in _HEADER_KEYWORDS:
        return True
    # ALL CAPS short line containing a known keyword (e.g. "WORK EXPERIENCE").
    if stripped == stripped.upper() and any(k in lowered for k in _HEADER_KEYWORDS):
        return True
    return False


def split_resume_sections(resume_text: str) -> List[ResumeSection]:
    """Split raw resume text into sections so the existing extractor can run on it.

    The PDF path produces ResumeSection objects; this rebuilds the same shape from
    plain text without reimplementing evidence extraction.
    """
    lines = resume_text.splitlines()
    sections: List[Tuple[str, List[str]]] = []
    current_name = "Summary"
    current_body: List[str] = []
    for line in lines:
        if _looks_like_header(line):
            if current_body:
                sections.append((current_name, current_body))
            current_name = line.strip().rstrip(":").title()
            current_body = []
        else:
            current_body.append(line)
    if current_body:
        sections.append((current_name, current_body))
    if not sections:
        sections = [("Summary", lines)]

    result: List[ResumeSection] = []
    for idx, (name, body) in enumerate(sections):
        text = "\n".join(body).strip()
        if not text:
            continue
        result.append(
            ResumeSection(
                id=f"section_{idx:03d}",
                section_name=name,
                text=text,
                page_number=1,
                source_quote=text[:300],
                confidence=0.8,
            )
        )
    if not result:
        result = [
            ResumeSection(
                id="section_000",
                section_name="Summary",
                text=resume_text.strip() or "(empty resume)",
                page_number=1,
                source_quote=resume_text.strip()[:300],
                confidence=0.6,
            )
        ]
    return result


def _run_id_for(resume: str, job_description: str) -> str:
    digest = hashlib.sha1(f"{resume}␟{job_description}".encode("utf-8")).hexdigest()[:12]
    return f"coach_{digest}"


@dataclass
class CoachContext:
    """Per-session, text-based view over the existing evaluator services.

    Built once per (resume, job_description) pair and reused across tool calls so a
    single agent run does not re-index or re-score on every step.
    """

    resume: str
    job_description: str
    target_role: str
    run_id: str
    config: RunConfig
    evidence: List[ResumeEvidence]
    requirements: List[JobRequirement]
    _matches: Optional[List[RequirementMatch]] = field(default=None, repr=False)
    _score: Optional[ScoreBreakdown] = field(default=None, repr=False)

    @property
    def matches(self) -> List[RequirementMatch]:
        if self._matches is None:
            self._matches, _ = compare_requirements(self.run_id, self.requirements, self.evidence, self.config)
        return self._matches

    @property
    def score(self) -> ScoreBreakdown:
        if self._score is None:
            self._score = calculate_score(self.requirements, self.matches, self.evidence, self.config)
        return self._score

    def resume_terms(self) -> set[str]:
        terms: set[str] = set()
        for ev in self.evidence:
            terms.update(t.lower() for t in ev.skills_detected + ev.tools_detected)
        return terms


_CACHE: "OrderedDict[str, CoachContext]" = OrderedDict()
_CACHE_MAX = 32


def build_coach_context(resume: str, job_description: str, target_role: str = "") -> CoachContext:
    """Build (or reuse) a text-based coaching context backed by the real evaluator."""
    run_id = _run_id_for(resume, job_description)
    cached = _CACHE.get(run_id)
    if cached is not None:
        cached.target_role = target_role or cached.target_role
        _CACHE.move_to_end(run_id)
        return cached

    config = default_config()
    sections = split_resume_sections(resume)
    job_paragraphs = parse_job_paragraphs(job_description)
    # Index only original source text (resume + JD), exactly like the PDF pipeline.
    build_chunks(run_id, sections, job_paragraphs, config.chunk_size, config.chunk_overlap, config.vector_store_provider)
    evidence = extract_resume_evidence(sections)
    requirements = extract_job_requirements(job_description, importance_weight_map(config))

    ctx = CoachContext(
        resume=resume,
        job_description=job_description,
        target_role=target_role,
        run_id=run_id,
        config=config,
        evidence=evidence,
        requirements=requirements,
    )
    _CACHE[run_id] = ctx
    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return ctx


def clear_context_cache() -> None:
    _CACHE.clear()
