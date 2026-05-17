from __future__ import annotations

from typing import List

from ..schemas import RequirementMatch, ResumeEvidence


def generate_keywords(matches: List[RequirementMatch]) -> List[str]:
    keywords: List[str] = []
    for match in matches:
        words = [w.strip(".,:;()").lower() for w in match.requirement_text.split()]
        for word in words:
            if len(word) > 3 and word not in keywords:
                keywords.append(word)
        if len(keywords) >= 20:
            break
    return keywords[:20]


def generate_notes(evidence: List[ResumeEvidence], missing_count: int) -> List[str]:
    notes = [
        "Prepare concise stories around the strongest cited projects or work bullets.",
        "Be ready to distinguish proven resume evidence from skills you are currently learning.",
    ]
    project_examples = [ev.text for ev in evidence if ev.evidence_type in {"project", "work_experience"}][:3]
    for example in project_examples:
        notes.append(f"Practice explaining this evidence: {example[:140]}")
    if missing_count:
        notes.append("For missing requirements, discuss learning plan and adjacent experience rather than claiming direct experience.")
    return notes

