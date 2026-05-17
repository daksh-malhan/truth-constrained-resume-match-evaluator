from app.schemas import Citation, ResumeEvidence, SourceType, SuggestionCategory
from app.services.truth_filter import classify_suggestion


def evidence(text: str):
    return [
        ResumeEvidence(
            id="ev1",
            section_name="Projects",
            text=text,
            skills_detected=["python", "rag"],
            tools_detected=["python", "rag"],
            evidence_type="project",
            has_metric=False,
            impact_level="medium",
            source_location="Projects section, page 1",
            source_quote=text,
            page_number=1,
        )
    ]


def citation():
    return Citation(source_type=SourceType.resume, source_location="Projects section, page 1", quote="Built a RAG chatbot with Python.")


def test_safe_rewrite_uses_existing_evidence_only():
    suggestion = classify_suggestion("s1", "Clarify existing evidence: Built a RAG chatbot with Python.", evidence("Built a RAG chatbot with Python."), ["r1"], [citation()])
    assert suggestion.category == SuggestionCategory.safe_rewrite
    assert suggestion.can_affect_projected_score is True


def test_unsupported_tool_is_rejected():
    suggestion = classify_suggestion("s1", "Built a LangChain RAG chatbot deployed to AWS.", evidence("Built a RAG chatbot with Python."), ["r1"], [citation()])
    assert suggestion.category == SuggestionCategory.unsafe
    assert suggestion.can_affect_projected_score is False

