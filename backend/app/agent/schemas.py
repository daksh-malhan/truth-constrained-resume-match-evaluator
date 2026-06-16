from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..schemas import ScoreBreakdown


# --- Tool result models (clean JSON schemas exposed to the LLM) ---


class ScoreResult(BaseModel):
    score: float = Field(..., description="Deterministic resume-vs-job match score, 0-10.")
    breakdown: ScoreBreakdown


class GapsResult(BaseModel):
    missing_requirements: List[str] = Field(
        default_factory=list,
        description="Job requirements with no supporting resume evidence.",
    )
    buried_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords present in the resume but not surfaced as a strong match to the job.",
    )


class TruthResult(BaseModel):
    supported: bool = Field(..., description="True only if every claim in the bullet is grounded in the resume.")
    unsupported_claims: List[str] = Field(
        default_factory=list,
        description="Specific fabricated skills, metrics, or outcome claims not present in the resume.",
    )


class RewriteResult(BaseModel):
    rewrite: str = Field(..., description="Suggested rewrite of the bullet.")
    rationale: str = Field(..., description="Why the rewrite is stronger for the target role.")
    truth_supported: bool = Field(..., description="False if the rewrite introduces unverifiable claims.")
    unsupported_claims: List[str] = Field(default_factory=list)
    flagged: bool = Field(False, description="True when the rewrite must NOT be asserted as-is.")


# --- Agent request / response / trace models ---


class CoachRequest(BaseModel):
    resume: str
    job_description: str
    target_role: str = ""


class ToolCallTrace(BaseModel):
    step: int
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0
    error: Optional[str] = None


class CoachResponse(BaseModel):
    target_role: str
    initial_score: Optional[float] = None
    score_breakdown: Optional[ScoreBreakdown] = None
    gaps: Optional[GapsResult] = None
    bullet_rewrites: List[RewriteResult] = Field(default_factory=list)
    truth_constraint_notes: List[str] = Field(default_factory=list)
    final_summary: str = ""
    iterations: int = 0
    stop_reason: str = "completed"
    tool_call_trace: List[ToolCallTrace] = Field(default_factory=list)
    llm_provider: str = ""
    model: str = ""
