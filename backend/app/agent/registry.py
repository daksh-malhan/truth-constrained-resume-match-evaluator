from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import StructuredTool, tool

from . import tools
from .context import CoachContext


def build_coach_tools(ctx: CoachContext) -> List[StructuredTool]:
    """Build the four coaching tools bound to a session context.

    The model-facing JSON schemas match the project spec. `resume` and
    `job_description` default to the active session, so the model does not have to
    echo the full documents back on every call.
    """

    @tool
    def score_resume(resume: str = "", job_description: str = "") -> dict:
        """Score how well the resume matches the target job (0-10) with a component breakdown.
        resume/job_description default to the active coaching session."""
        return tools.score_resume(ctx).model_dump()

    @tool
    def find_gaps(resume: str = "", job_description: str = "") -> dict:
        """Find missing job requirements and buried (under-surfaced) resume keywords.
        resume/job_description default to the active coaching session."""
        return tools.find_gaps(ctx).model_dump()

    @tool
    def rewrite_bullet(bullet: str, target_role: str = "", missing_keywords: Optional[List[str]] = None) -> dict:
        """Rewrite one resume bullet to be stronger for the target role.
        The rewrite is truth-checked; any unverifiable claim is flagged, never asserted."""
        return tools.rewrite_bullet(ctx, bullet, target_role, missing_keywords or []).model_dump()

    @tool
    def check_truth(bullet: str) -> dict:
        """Check whether a bullet is fully supported by the resume.
        Returns supported (bool) and a list of unsupported_claims."""
        return tools.check_truth(ctx, bullet).model_dump()

    return [score_resume, find_gaps, rewrite_bullet, check_truth]
