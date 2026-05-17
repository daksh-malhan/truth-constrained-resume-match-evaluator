from __future__ import annotations

from typing import Iterable, List

from ..schemas import Citation, ResumeEvidence, Suggestion, SuggestionCategory
from .skill_normalizer import detect_skills


def classify_suggestion(
    suggestion_id: str,
    suggested_text: str,
    resume_evidence: List[ResumeEvidence],
    affected_requirement_ids: List[str],
    citations: List[Citation],
    original_text: str | None = None,
) -> Suggestion:
    """Classify a generated suggestion before it can influence projected scoring."""
    source_text = " ".join(ev.text for ev in resume_evidence)
    source_skills = set(detect_skills(source_text))
    suggested_skills = set(detect_skills(suggested_text))
    unsupported_skills = suggested_skills - source_skills
    adds_metric = any(ch.isdigit() for ch in suggested_text) and not any(ev.has_metric for ev in resume_evidence if ev.text == original_text)

    unsafe_terms = ["certified", "led team", "deployed to aws", "production scale", "improved by", "increased by"]
    unsafe_phrase = any(term in suggested_text.lower() and term not in source_text.lower() for term in unsafe_terms)

    # Truth constraints are intentionally conservative: any new skill, metric, or
    # production/deployment claim not found in source evidence is rejected.
    if unsupported_skills or adds_metric or unsafe_phrase:
        category = SuggestionCategory.unsafe
        reason = "Rejected because it adds unsupported skills, metrics, deployment, seniority, or outcome claims not present in the original resume evidence."
        can_affect = False
    elif citations:
        category = SuggestionCategory.safe_rewrite
        reason = "Uses only facts and terminology already present in the original resume evidence."
        can_affect = True
    else:
        category = SuggestionCategory.needs_confirmation
        reason = "May be true, but the original resume evidence does not explicitly support it."
        can_affect = False

    return Suggestion(
        id=suggestion_id,
        original_text=original_text,
        suggested_text=suggested_text,
        category=category,
        reason=reason,
        supporting_evidence_ids=[ev.id for ev in resume_evidence[:3]],
        affected_requirement_ids=affected_requirement_ids,
        citations=citations,
        can_affect_projected_score=can_affect,
    )


def safe_suggestions_only(suggestions: Iterable[Suggestion]) -> List[Suggestion]:
    return [s for s in suggestions if s.category == SuggestionCategory.safe_rewrite and s.can_affect_projected_score]
