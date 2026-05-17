from __future__ import annotations

import os
from typing import List, Tuple

from pydantic import BaseModel, Field

from ..schemas import RequirementMatch, ScoreBreakdown
from .llm_client import get_llm_client


class ComparisonNarrative(BaseModel):
    summary: str = Field(..., description="Truth-constrained narrative summary grounded in supplied matches.")
    remaining_risks: List[str] = Field(default_factory=list)


def generate_comparison_narrative(matches: List[RequirementMatch], score: ScoreBreakdown, threshold_reached: bool) -> Tuple[str | None, str | None]:
    if os.getenv("LLM_PROVIDER", "mock").lower() != "ollama":
        return None, None
    compact_matches = [
        {
            "requirement": match.requirement_text,
            "status": match.status,
            "match_type": match.match_type,
            "evidence_strength": match.evidence_strength,
            "citations": [citation.model_dump(mode="json") for citation in match.citations[:2]],
        }
        for match in matches[:12]
    ]
    client = get_llm_client()
    try:
        narrative = client.structured(
            system_prompt=(
                "You summarize resume-job fit using only the supplied structured match data and citations. "
                "Do not invent resume claims. Use projected-score wording only."
            ),
            user_payload={
                "score": score.model_dump(mode="json"),
                "threshold_reached_projected": threshold_reached,
                "matches": compact_matches,
            },
            output_model=ComparisonNarrative,
        )
    except Exception:
        return None, "Local LLM comparison narrative failed or timed out; deterministic scoring/reporting still completed."
    risks = " ".join(narrative.remaining_risks[:3])
    return f"{narrative.summary} {risks}".strip(), None
