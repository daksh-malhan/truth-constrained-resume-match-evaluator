from app.schemas import ResumeEvidence
from app.services.resume_contextualizer import ResumeEvidenceUpdate, contextualize_resume_evidence, deterministic_contextualize_resume


def evidence_item(text: str, evidence_type: str = "other") -> ResumeEvidence:
    return ResumeEvidence(
        id="ev1",
        section_name="Skills",
        text=text,
        skills_detected=["python"],
        tools_detected=["python"],
        evidence_type=evidence_type,
        has_metric=False,
        impact_level="unknown",
        source_location="Skills section, page 1",
        source_quote=text,
        page_number=1,
    )


def test_deterministic_contextualizer_promotes_action_oriented_project_evidence():
    evidence = [evidence_item("Developed a Python backend service with REST APIs.")]
    context = deterministic_contextualize_resume(evidence)
    assert context.evidence_updates
    assert context.evidence_updates[0].evidence_type == "project"


def test_contextualizer_does_not_add_unsupported_skills(monkeypatch):
    evidence = [evidence_item("Developed a Python backend service.")]

    def fake_llm_contextualize_resume(_):
        from app.services.resume_contextualizer import ResumeContextResult

        return ResumeContextResult(
            candidate_context_summary="Grounded summary",
            used_llm=True,
            evidence_updates=[
                ResumeEvidenceUpdate(
                    evidence_id="ev1",
                    evidence_type="project",
                    impact_level="medium",
                    concrete_skills_tools=["Python", "Kubernetes"],
                )
            ],
        )

    monkeypatch.setenv("ENABLE_RESUME_CONTEXT_LLM", "true")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setattr("app.services.resume_contextualizer.llm_contextualize_resume", fake_llm_contextualize_resume)
    updated, context = contextualize_resume_evidence(evidence, "Developed a Python backend service.")
    assert context.used_llm is True
    assert updated[0].evidence_type == "project"
    assert "python" in updated[0].skills_detected
    assert "kubernetes" not in updated[0].skills_detected

