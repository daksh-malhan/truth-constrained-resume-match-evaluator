from app.schemas import Citation, RequirementMatch, SourceType


def test_major_match_claim_carries_citation():
    match = RequirementMatch(
        requirement_id="r1",
        requirement_text="FastAPI",
        matched_evidence_ids=["ev1"],
        retrieved_chunk_ids=["chunk1"],
        match_type="exact",
        evidence_strength=1.0,
        confidence=0.9,
        importance_weight=1.0,
        weighted_score=0.9,
        status="strong_match",
        explanation="FastAPI appears in project evidence.",
        citations=[Citation(source_type=SourceType.resume, source_location="Projects page 1", quote="Built FastAPI service.")],
    )
    assert match.citations
    assert match.citations[0].source_type == SourceType.resume

