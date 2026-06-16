from app import database
from app.agent.context import build_coach_context
from app.agent import tools


RESUME = """PROJECTS
Built a FastAPI service in Python with pytest coverage and a SQLite backend.
Created a Dockerized REST API that processes JSON records and logs progress.

SKILLS
Python, FastAPI, Docker, SQL, Git
"""

JOB = """Backend Engineer Intern
Required: strong Python and REST API development.
Must have experience with Docker and SQL databases.
Preferred: Kubernetes orchestration and AWS deployment.
"""


def context():
    database.init_db()
    return build_coach_context(resume=RESUME, job_description=JOB)


def test_score_resume_returns_bounded_score_and_breakdown():
    ctx = context()
    result = tools.score_resume(ctx)
    assert 0.0 <= result.score <= 10.0
    # Breakdown reuses the existing deterministic ScoreBreakdown components.
    assert result.breakdown.final_score == result.score
    assert result.breakdown.core_technical_skills_score >= 0.0


def test_find_gaps_reports_missing_requirements_and_buried_keywords():
    ctx = context()
    result = tools.find_gaps(ctx)
    # Kubernetes / AWS are in the JD but not the resume -> missing.
    missing_blob = " ".join(result.missing_requirements).lower()
    assert "kubernetes" in missing_blob or "aws" in missing_blob
    # buried_keywords are resume-present skills that did not land as strong matches.
    assert isinstance(result.buried_keywords, list)


def test_check_truth_accepts_supported_bullet():
    ctx = context()
    result = tools.check_truth(ctx, "Built a FastAPI service in Python with pytest coverage.")
    assert result.supported is True
    assert result.unsupported_claims == []


def test_check_truth_flags_unsupported_metric_and_skill():
    ctx = context()
    result = tools.check_truth(ctx, "Improved latency by 90% using Kubernetes in production at AWS scale.")
    assert result.supported is False
    assert result.unsupported_claims  # non-empty list of fabricated claims


class _FakeClient:
    """Deterministic LLMClient stand-in that returns a fixed rewrite draft."""

    provider_name = "fake"

    def __init__(self, rewrite: str, rationale: str = "stronger phrasing"):
        self._rewrite = rewrite
        self._rationale = rationale

    def structured(self, *, system_prompt, user_payload, output_model):
        return output_model.model_validate({"rewrite": self._rewrite, "rationale": self._rationale})


def test_rewrite_bullet_keeps_supported_rewrite_unflagged():
    ctx = context()
    client = _FakeClient("Engineered a FastAPI service in Python with pytest coverage and SQLite.")
    result = tools.rewrite_bullet(
        ctx,
        "Built a FastAPI service.",
        target_role="Backend Engineer",
        missing_keywords=["python"],
        llm_client=client,
    )
    assert result.truth_supported is True
    assert result.flagged is False
    assert result.unsupported_claims == []


def test_rewrite_bullet_flags_fabricated_metric():
    ctx = context()
    client = _FakeClient("Built a FastAPI service that improved latency by 40% in production.")
    result = tools.rewrite_bullet(
        ctx,
        "Built a FastAPI service.",
        target_role="Backend Engineer",
        llm_client=client,
    )
    # The truth constraint must flag, not assert, the fabricated metric.
    assert result.truth_supported is False
    assert result.flagged is True
    assert any("40" in claim for claim in result.unsupported_claims)
    assert "FLAGGED" in result.rationale
