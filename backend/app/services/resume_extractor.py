from __future__ import annotations

import re
from typing import List

from ..schemas import ResumeEvidence, ResumeSection
from .skill_normalizer import detect_skills


def _evidence_type(section_name: str) -> str:
    s = section_name.lower()
    if "project" in s:
        return "project"
    if "experience" in s or "work" in s:
        return "work_experience"
    if "education" in s:
        return "education"
    if "cert" in s:
        return "certification"
    if "skill" in s:
        return "skill"
    if "summary" in s:
        return "summary"
    return "other"


def extract_resume_evidence(sections: List[ResumeSection]) -> List[ResumeEvidence]:
    evidence: List[ResumeEvidence] = []
    counter = 0
    for section in sections:
        pieces = [p.strip(" \n\t-•") for p in re.split(r"\n[-•]|\n|(?<=[.!?])\s+", section.text) if p.strip()]
        for piece in pieces:
            if len(piece) < 8:
                continue
            skills = detect_skills(piece)
            metric_match = re.search(r"(\d+%|\$?\d+(?:\.\d+)?[kKmM]?|\b\d+\s*(users|requests|seconds|ms|projects|models)\b)", piece)
            impact_level = "high" if metric_match else ("medium" if skills else "unknown")
            evidence.append(
                ResumeEvidence(
                    id=f"resume_ev_{counter:03d}",
                    section_name=section.section_name,
                    text=piece,
                    skills_detected=skills,
                    tools_detected=skills,
                    evidence_type=_evidence_type(section.section_name),  # type: ignore[arg-type]
                    has_metric=metric_match is not None,
                    metric_text=metric_match.group(0) if metric_match else None,
                    impact_level=impact_level,  # type: ignore[arg-type]
                    source_location=f"{section.section_name} section, page {section.page_number}",
                    source_quote=piece[:300],
                    page_number=section.page_number,
                    confidence=0.85 if skills else 0.65,
                )
            )
            counter += 1
    return evidence

