from app.schemas import Citation, JobRequirement, RetrievedChunk, SourceType
from app.services.inference_matcher import InferredRequirementSupport, infer_requirement_support


def req(text: str = "Basic knowledge of REST APIs") -> JobRequirement:
    return JobRequirement(
        id="r1",
        text=text,
        normalized_skill_or_requirement="rest api",
        category="technical_skill",
        importance="must_have",
        importance_weight=1.0,
        source_location="Requirements paragraph 1",
        source_quote=text,
    )


def chunk(text: str = "Built a Python backend service exposing HTTP endpoints.") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk1",
        source_type=SourceType.resume,
        text=text,
        similarity_score=0.7,
        metadata={},
        citation=Citation(source_type=SourceType.resume, source_location="Projects page 1", quote=text, chunk_id="chunk1"),
    )


def test_inference_matcher_accepts_grounded_llm_partial(monkeypatch):
    def fake_post(*_, **__):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "message": {
                        "content": '{"can_infer": true, "inferred_match_type": "semantic", "evidence_strength": 0.6, "confidence": 0.8, "reason": "Backend HTTP endpoints imply basic REST API familiarity.", "supporting_chunk_ids": ["chunk1"]}'
                    }
                }

        return Response()

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("ENABLE_INFERENCE_MATCH_LLM", "true")
    monkeypatch.setattr("app.services.inference_matcher.httpx.post", fake_post)
    inferred = infer_requirement_support(req(), [chunk()])
    assert inferred.can_infer is True
    assert inferred.evidence_strength == 0.6
    assert inferred.supporting_chunk_ids == ["chunk1"]


def test_inference_matcher_rejects_uncited_or_overstrong_result(monkeypatch):
    def fake_post(*_, **__):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "message": {
                        "content": '{"can_infer": true, "inferred_match_type": "semantic", "evidence_strength": 1.0, "confidence": 1.0, "reason": "Unsupported.", "supporting_chunk_ids": ["not_real"]}'
                    }
                }

        return Response()

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("ENABLE_INFERENCE_MATCH_LLM", "true")
    monkeypatch.setattr("app.services.inference_matcher.httpx.post", fake_post)
    inferred = infer_requirement_support(req("Kubernetes production deployment"), [chunk()])
    assert inferred.can_infer is False
    assert inferred.evidence_strength == 0.0

