from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, Field

from ..schemas import SuggestionCategory
from ..services.llm_client import LLMClient, get_llm_client
from ..services.skill_normalizer import detect_skills
from ..services.truth_filter import classify_suggestion
from .context import CoachContext
from .schemas import GapsResult, RewriteResult, ScoreResult, TruthResult


# --- score_resume -----------------------------------------------------------


def score_resume(ctx: CoachContext) -> ScoreResult:
    """Score the resume against the job using the existing deterministic engine."""
    breakdown = ctx.score
    return ScoreResult(score=breakdown.final_score, breakdown=breakdown)


# --- find_gaps --------------------------------------------------------------


def find_gaps(ctx: CoachContext) -> GapsResult:
    """Identify missing requirements and buried (under-surfaced) resume keywords."""
    missing: List[str] = []
    for match in ctx.matches:
        if match.status == "missing":
            missing.append(match.requirement_text.strip())

    # Buried keywords: requirement skills the resume actually contains, but which did
    # not land as a strong match (present yet under-emphasized for this job).
    resume_terms = ctx.resume_terms()
    strong_terms = {
        req.normalized_skill_or_requirement.lower()
        for req, match in zip(ctx.requirements, ctx.matches)
        if match.status == "strong_match"
    }
    buried: List[str] = []
    seen: set[str] = set()
    for req in ctx.requirements:
        term = req.normalized_skill_or_requirement.lower()
        if term in resume_terms and term not in strong_terms and term not in seen:
            seen.add(term)
            buried.append(req.normalized_skill_or_requirement)

    # De-duplicate missing requirements while preserving order.
    deduped_missing: List[str] = []
    seen_missing: set[str] = set()
    for text in missing:
        key = text.lower()
        if key not in seen_missing:
            seen_missing.add(key)
            deduped_missing.append(text)
    return GapsResult(missing_requirements=deduped_missing, buried_keywords=buried)


# --- check_truth ------------------------------------------------------------

_UNSAFE_TERMS = ["certified", "led team", "deployed to aws", "production scale", "improved by", "increased by", "in production", "at scale"]


def _unsupported_claims(ctx: CoachContext, bullet: str) -> List[str]:
    source_text = " ".join(ev.text for ev in ctx.evidence).lower()
    resume_terms = ctx.resume_terms()
    claims: List[str] = []

    for skill in detect_skills(bullet):
        if skill.lower() not in resume_terms:
            claims.append(f"Unsupported skill/tool not in resume: '{skill}'")

    for number in re.findall(r"\$?\d+(?:\.\d+)?%?", bullet):
        if number not in source_text:
            claims.append(f"Unverifiable metric not in resume: '{number}'")

    for term in _UNSAFE_TERMS:
        if term in bullet.lower() and term not in source_text:
            claims.append(f"Unsupported claim: '{term}'")

    # De-duplicate, preserve order.
    deduped: List[str] = []
    seen: set[str] = set()
    for claim in claims:
        if claim not in seen:
            seen.add(claim)
            deduped.append(claim)
    return deduped


def check_truth(ctx: CoachContext, bullet: str) -> TruthResult:
    """Reuse the truth-constraint logic to verify a bullet against the resume."""
    claims = _unsupported_claims(ctx, bullet)
    # Cross-check with the existing classifier so the decision stays consistent with
    # the rest of the evaluator's truth filter.
    classified = classify_suggestion(
        suggestion_id="coach_truth_check",
        suggested_text=bullet,
        resume_evidence=ctx.evidence,
        affected_requirement_ids=[],
        citations=[],
    )
    supported = not claims and classified.category != SuggestionCategory.unsafe
    return TruthResult(supported=supported, unsupported_claims=claims)


# --- rewrite_bullet ---------------------------------------------------------


class _RewriteDraft(BaseModel):
    rewrite: str = Field("", description="Rewritten bullet using only facts in the original/resume.")
    rationale: str = Field("", description="Why the rewrite is stronger for the target role.")


_REWRITE_SYSTEM_PROMPT = (
    "You rewrite a single resume bullet to be stronger for a target role. "
    "Truth constraint: use ONLY facts already present in the original bullet and resume. "
    "Never invent metrics, numbers, employers, seniority, or deployment/production claims. "
    "You may weave in a missing keyword ONLY if the original already demonstrates it. "
    "Return JSON with 'rewrite' and 'rationale'."
)


def rewrite_bullet(
    ctx: CoachContext,
    bullet: str,
    target_role: str = "",
    missing_keywords: Optional[List[str]] = None,
    *,
    llm_client: Optional[LLMClient] = None,
) -> RewriteResult:
    """Generate a stronger bullet, then enforce the truth constraint on the output."""
    missing_keywords = missing_keywords or []
    client = llm_client or get_llm_client()
    try:
        draft = client.structured(
            system_prompt=_REWRITE_SYSTEM_PROMPT,
            user_payload={
                "original_bullet": bullet,
                "target_role": target_role or ctx.target_role,
                "missing_keywords": missing_keywords,
                "resume_excerpt": ctx.resume[:1500],
            },
            output_model=_RewriteDraft,
        )
        rewrite_text = draft.rewrite.strip() or bullet
        rationale = draft.rationale.strip()
    except Exception as exc:  # pragma: no cover - exercised via fake client in tests
        rewrite_text = bullet
        rationale = f"Rewrite generation failed; returning original bullet unchanged ({exc})."

    truth = check_truth(ctx, rewrite_text)
    flagged = not truth.supported
    if flagged:
        rationale = (
            f"{rationale} FLAGGED: this rewrite introduces unverifiable claims and must not be "
            f"asserted as written: {'; '.join(truth.unsupported_claims)}"
        ).strip()
    return RewriteResult(
        rewrite=rewrite_text,
        rationale=rationale,
        truth_supported=truth.supported,
        unsupported_claims=truth.unsupported_claims,
        flagged=flagged,
    )
