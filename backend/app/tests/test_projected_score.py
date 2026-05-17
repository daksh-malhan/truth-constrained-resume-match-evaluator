from app.schemas import Citation, SourceType, Suggestion, SuggestionCategory, RunConfig
from app.services.improvement_planner import project_score


def test_projected_score_uses_only_safe_rewrites():
    citation = Citation(source_type=SourceType.resume, source_location="Projects page 1", quote="Built a Python RAG project.")
    safe = Suggestion(id="safe", suggested_text="Clarify Python RAG project.", category=SuggestionCategory.safe_rewrite, reason="grounded", citations=[citation], can_affect_projected_score=True)
    unsafe = Suggestion(id="unsafe", suggested_text="Claim AWS deployment.", category=SuggestionCategory.unsafe, reason="unsupported", citations=[], can_affect_projected_score=False)
    projected = project_score(6.0, [safe, unsafe], RunConfig())
    assert projected == 6.35

