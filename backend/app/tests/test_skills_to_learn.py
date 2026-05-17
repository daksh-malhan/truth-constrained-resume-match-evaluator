from app.schemas import Citation, RequirementMatch, ResumeEvidence, RunConfig, SourceType
from app.services.improvement_planner import generate_improvement_candidates


def _match(req_id: str, text: str, status: str = "missing") -> RequirementMatch:
    return RequirementMatch(
        requirement_id=req_id,
        requirement_text=text,
        matched_evidence_ids=[],
        retrieved_chunk_ids=[],
        match_type="missing",
        evidence_strength=0.0,
        confidence=0.8,
        importance_weight=1.0,
        weighted_score=0.0,
        status=status,  # type: ignore[arg-type]
        explanation="No supported evidence.",
        citations=[
            Citation(
                source_type=SourceType.job_description,
                source_location="Requirements paragraph 1",
                quote=text,
                paragraph_index=1,
            )
        ],
    )


def test_skills_to_learn_are_concrete_learning_targets_not_first_words():
    _, learn, _, _ = generate_improvement_candidates(
        "run_skill_learn",
        [
            _match("r1", "Understanding of OOP concepts"),
            _match("r2", "Experience with Git/version control"),
            _match("r3", "Work on data processing / ETL pipelines"),
        ],
        [],
        RunConfig(),
    )
    names = [item.skill for item in learn]
    assert "Object-oriented programming in Python" in names
    assert "Git version control workflow" in names
    assert "Data processing and ETL pipelines" in names
    assert "Understanding" not in names
    assert all(len(item.suggested_learning_focus.split()) >= 8 for item in learn)
    assert all(not item.suggested_learning_focus.startswith("Build a small project that demonstrates:") for item in learn)


def test_skills_to_learn_deduplicates_equivalent_requirements():
    _, learn, _, _ = generate_improvement_candidates(
        "run_skill_dedupe",
        [
            _match("r1", "Build REST APIs"),
            _match("r2", "Basic knowledge of REST APIs"),
        ],
        [],
        RunConfig(),
    )
    assert [item.skill for item in learn] == ["REST API design and consumption"]
