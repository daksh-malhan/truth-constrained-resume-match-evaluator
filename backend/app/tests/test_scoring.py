from app.schemas import JobRequirement, ResumeEvidence, RunConfig
from app.services.scoring_engine import calculate_score, score_band, status_for_strength


def req(req_id: str, skill: str, category: str = "technical_skill", weight: float = 1.0):
    return JobRequirement(
        id=req_id,
        text=f"Required {skill}",
        normalized_skill_or_requirement=skill,
        category=category,
        importance="must_have",
        importance_weight=weight,
        source_location="Requirements paragraph 1",
        source_quote=f"Required {skill}",
        paragraph_index=1,
    )


def ev(text: str, skills: list[str]):
    return ResumeEvidence(
        id="ev1",
        section_name="Projects",
        text=text,
        skills_detected=skills,
        tools_detected=skills,
        evidence_type="project",
        has_metric=True,
        metric_text="3",
        impact_level="high",
        source_location="Projects section, page 1",
        source_quote=text,
        page_number=1,
    )


def test_score_band_boundaries():
    assert score_band(8.8) == "strong match"
    assert score_band(7.2) == "good match"
    assert score_band(6.0) == "partial match"
    assert score_band(4.5) == "weak match"
    assert score_band(3.9) == "poor match"


def test_status_for_strength():
    assert status_for_strength(0.9) == "strong_match"
    assert status_for_strength(0.7) == "partial_match"
    assert status_for_strength(0.4) == "weak_match"
    assert status_for_strength(0.1) == "missing"


def test_final_score_clamps_with_penalty():
    config = RunConfig(max_risk_penalty=1.0)
    breakdown = calculate_score([], [], [ev("Built three Python APIs.", ["python", "fastapi"])], config, prompt_injection_detected=True)
    assert 0 <= breakdown.final_score <= 10
    assert breakdown.risk_penalty == 0.25

