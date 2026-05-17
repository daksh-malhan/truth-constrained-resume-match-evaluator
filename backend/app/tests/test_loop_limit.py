from app.schemas import Citation, RequirementMatch, ResumeEvidence, RunConfig, ScoreBreakdown, SourceType
from app.services.improvement_planner import run_improvement_loop


def test_loop_is_capped_at_three_even_if_config_higher():
    config = RunConfig(max_iterations=8, threshold_score=10.0, min_improvement=0.0)
    evidence = [
        ResumeEvidence(
            id="ev1",
            section_name="Projects",
            text="Built a Dockerized Python API.",
            skills_detected=["docker", "python"],
            tools_detected=["docker", "python"],
            evidence_type="project",
            has_metric=False,
            impact_level="medium",
            source_location="Projects section, page 1",
            source_quote="Built a Dockerized Python API.",
            page_number=1,
        )
    ]
    citation = Citation(source_type=SourceType.resume, source_location="Projects section, page 1", quote="Built a Dockerized Python API.")
    matches = [
        RequirementMatch(
            requirement_id="r1",
            requirement_text="Kubernetes orchestration",
            matched_evidence_ids=["ev1"],
            retrieved_chunk_ids=[],
            match_type="adjacent",
            evidence_strength=0.4,
            confidence=0.8,
            importance_weight=1.0,
            weighted_score=0.32,
            status="weak_match",
            explanation="Docker is adjacent to Kubernetes.",
            citations=[citation],
        )
    ]
    iterations, projected, stop = run_improvement_loop("run_test", 5.0, ScoreBreakdown(final_score=5.0), matches, evidence, config)
    assert len(iterations) <= 3
    assert iterations[-1].stop_reason.value == "MAX_ITERATIONS_REACHED"

