from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Tuple

from .. import database
from ..config import max_upload_bytes, merge_config
from ..schemas import FinalReport, RequirementMatch, RunConfig, SourceType, StopReason
from .admin_config_service import get_active_config
from .ats_scoring import calculate_ats_score
from .comparison_summarizer import generate_comparison_narrative
from .interview_prep import generate_keywords, generate_notes
from .job_cleaner import clean_job_description
from .job_parser import extract_job_requirements, infer_job_title, parse_job_paragraphs
from .logging_service import log_event
from .pdf_parser import parse_resume_pdf, validate_pdf
from .prompt_injection import detect_prompt_injection
from .rag_indexer import build_chunks
from .resume_contextualizer import contextualize_resume_evidence
from .resume_extractor import extract_resume_evidence
from .scoring_engine import calculate_score, compare_requirements
from .improvement_planner import run_improvement_loop


def importance_weight_map(config: RunConfig) -> Dict[str, float]:
    return {
        "must_have": config.must_have_weight,
        "repeated": config.repeated_weight,
        "main_responsibility": config.main_responsibility_weight,
        "preferred": config.preferred_weight,
        "nice_to_have": config.nice_to_have_weight,
        "generic": config.generic_weight,
    }


def split_matches(matches: List[RequirementMatch]) -> Tuple[List[RequirementMatch], List[RequirementMatch], List[RequirementMatch]]:
    matched = [m for m in matches if m.status == "strong_match"]
    partial = [m for m in matches if m.status in {"partial_match", "weak_match"}]
    missing = [m for m in matches if m.status == "missing"]
    return matched, partial, missing


def analyze_resume_job(
    *,
    resume_filename: str,
    content_type: str | None,
    pdf_bytes: bytes,
    job_description_text: str,
    threshold: float | None = None,
    config_overrides: Dict[str, Any] | None = None,
) -> FinalReport:
    """Run the full analysis pipeline and persist a self-contained report.

    The orchestration keeps source evidence and generated recommendations separate:
    resume/JD chunks feed retrieval and citations, while projected improvements are
    stored only as guidance and never re-indexed as resume truth.
    """
    started = time.perf_counter()
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    saved_config = get_active_config().model_dump()
    config = merge_config(saved_config, config_overrides, threshold)
    database.insert_run(run_id, resume_filename, config.threshold_score, config.model_dump())
    log_event(run_id, "RUN_CREATED", "Analysis run created", metadata={"threshold": config.threshold_score})

    try:
        validate_pdf(resume_filename, content_type, pdf_bytes, max_upload_bytes())
        log_event(run_id, "PDF_VALIDATED", "Uploaded PDF passed validation", metadata={"filename": resume_filename, "bytes": len(pdf_bytes)})
        log_event(run_id, "JOB_DESCRIPTION_RECEIVED", "Job description received", metadata={"characters": len(job_description_text)})

        sections = parse_resume_pdf(pdf_bytes)
        log_event(run_id, "PDF_PARSED", "Resume PDF parsed into sections", metadata={"sections": len(sections)})
        resume_text = "\n".join(section.text for section in sections)
        resume_injection, resume_hits = detect_prompt_injection(resume_text)
        jd_injection, jd_hits = detect_prompt_injection(job_description_text)
        prompt_injection_detected = config.enable_prompt_injection_detection and (resume_injection or jd_injection)
        if prompt_injection_detected:
            log_event(run_id, "PROMPT_INJECTION_DETECTED", "Potential prompt injection content was detected and ignored.", level="warning", metadata={"resume_hits": resume_hits, "job_hits": jd_hits})
        source_paragraphs = parse_job_paragraphs(job_description_text)
        cleaned_jd = clean_job_description(job_description_text)
        if cleaned_jd.warning:
            log_event(run_id, "LLM_OUTPUT_REPAIR_ATTEMPTED", cleaned_jd.warning, level="warning", metadata={"stage": "job_description_cleaner"})
        requirement_source_text = cleaned_jd.cleaned_text or job_description_text
        requirements = extract_job_requirements(requirement_source_text, importance_weight_map(config))
        log_event(
            run_id,
            "JOB_DESCRIPTION_PARSED",
            "Job description cleaned and parsed into concrete candidate requirements",
            metadata={
                "source_paragraphs": len(source_paragraphs),
                "cleaned_requirements": len(cleaned_jd.concrete_requirements),
                "ignored_snippets": len(cleaned_jd.ignored_snippets),
                "used_cleaner_llm": cleaned_jd.used_llm,
                "requirements": len(requirements),
            },
        )

        chunks = build_chunks(run_id, sections, source_paragraphs, config.chunk_size, config.chunk_overlap, config.vector_store_provider)
        log_event(run_id, "RAG_CHUNKS_CREATED", "RAG chunks created from original source documents only", metadata={"chunks": len(chunks)})
        log_event(
            run_id,
            "EMBEDDINGS_GENERATED",
            "Embeddings generated through the configured embedding provider",
            metadata={"embedding_model": config.embedding_model, "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "mock")},
        )
        log_event(run_id, "VECTOR_STORE_INDEXED", "Chunks indexed in configured vector store with SQLite metadata fallback", metadata={"provider": config.vector_store_provider})

        evidence = extract_resume_evidence(sections)
        evidence, resume_context = contextualize_resume_evidence(evidence, resume_text)
        if resume_context.warning:
            log_event(run_id, "LLM_OUTPUT_REPAIR_ATTEMPTED", resume_context.warning, level="warning", metadata={"stage": "resume_contextualizer"})
        log_event(
            run_id,
            "RESUME_EXTRACTION_COMPLETED",
            "Structured resume evidence extracted and context-classified before scoring",
            metadata={
                "evidence_items": len(evidence),
                "resume_context_updates": len(resume_context.evidence_updates),
                "used_resume_context_llm": resume_context.used_llm,
                "candidate_context_summary": resume_context.candidate_context_summary[:500],
            },
        )
        log_event(run_id, "JOB_EXTRACTION_COMPLETED", "Structured job requirements extracted", metadata={"requirements": len(requirements)})
        log_event(run_id, "SKILL_NORMALIZATION_COMPLETED", "Skills/tools normalized with partial-credit mapping")

        log_event(run_id, "RETRIEVAL_STARTED", "Retrieving source evidence for each requirement")
        matches, similarities = compare_requirements(run_id, requirements, evidence, config)
        log_event(run_id, "RETRIEVAL_COMPLETED", "Retrieved source chunks for requirement comparison", metadata={"retrieval_calls": len(requirements) * 2})
        log_event(run_id, "COMPARISON_COMPLETED", "Requirement-level comparison completed", metadata={"matches": len(matches)})

        score = calculate_score(requirements, matches, evidence, config, prompt_injection_detected)
        initial_score = score.final_score
        log_event(run_id, "SCORE_CALCULATED", "Initial deterministic score calculated", metadata=score.model_dump())

        iterations = []
        projected = initial_score
        stop_reason: StopReason | None = None
        # Projection is deliberately capped and based only on SAFE_REWRITE suggestions.
        # Needs-confirmation and unsafe ideas are visible to users but cannot move the score.
        if initial_score < config.threshold_score:
            log_event(run_id, "IMPROVEMENT_LOOP_STARTED", "Truth-constrained projected improvement loop started")
            iterations, projected, stop_reason = run_improvement_loop(run_id, initial_score, score, matches, evidence, config)
            log_event(run_id, "IMPROVEMENT_SUGGESTIONS_GENERATED", "Generated projected suggestions without updating source documents", metadata={"iterations": len(iterations)})
            log_event(run_id, "TRUTH_FILTER_APPLIED", "Truth filter classified suggestions")
            log_event(run_id, "PROJECTED_SCORE_CALCULATED", "Projected score calculated using SAFE_REWRITE suggestions only", metadata={"projected_score": projected})
            log_event(run_id, "LOOP_STOPPED", "Improvement loop stopped", metadata={"stop_reason": stop_reason.value if stop_reason else None})
        else:
            stop_reason = StopReason.threshold_reached

        matched, partial, missing = split_matches(matches)
        all_safe = [s for it in iterations for s in it.safe_improvements]
        all_learn = []
        seen_learning_skills = set()
        for iteration in iterations:
            for skill in iteration.skills_to_learn:
                key = skill.skill.lower()
                if key not in seen_learning_skills:
                    seen_learning_skills.add(key)
                    all_learn.append(skill)
        all_confirm = [s for it in iterations for s in it.needs_confirmation_suggestions]
        all_unsafe = [s for it in iterations for s in it.unsafe_rejected_suggestions]
        citations = [citation for match in matches for citation in match.citations]
        final_score_breakdown = score.model_copy(update={"final_score": projected})
        final_score_breakdown.score_band = "strong match" if projected >= 8.5 else "good match" if projected >= 7 else score.score_band

        threshold_reached = projected >= config.threshold_score
        if threshold_reached:
            review = "Projected threshold reached after applying verified improvements. The recommendation set remains separate from the original resume and is not treated as source truth."
        else:
            review = "Threshold not safely reachable without adding unverified claims. Safe improvements are shown separately from missing skills and rejected unsupported claims."
        local_llm_review, llm_warning = generate_comparison_narrative(matches, final_score_breakdown, threshold_reached)
        llm_calls_count = int(cleaned_jd.used_llm) + int(resume_context.used_llm) + (1 if local_llm_review else 0)
        if local_llm_review:
            review += f" Local LLM comparison note: {local_llm_review}"
        if llm_warning:
            log_event(run_id, "LLM_OUTPUT_REPAIR_ATTEMPTED", llm_warning, level="warning", metadata={"provider": os.getenv("LLM_PROVIDER", "mock")})
        if prompt_injection_detected:
            review += " Potential prompt injection content was detected and ignored."
        log_event(run_id, "FINAL_REVIEW_GENERATED", "Final review generated")

        # ATS scoring is a separate readiness simulation. It reuses the same source
        # evidence and match objects, but it does not change the resume/job match score.
        ats_started = time.perf_counter()
        log_event(run_id, "ATS_SCORING_STARTED", "ATS-style readiness scoring started")
        ats_breakdown, ats_ranking = calculate_ats_score(
            resume_text=resume_text,
            sections=sections,
            evidence=evidence,
            requirements=requirements,
            matches=matches,
            main_match_score=projected,
            config=config,
            prompt_injection_detected=prompt_injection_detected,
            unsafe_suggestions=all_unsafe,
        )
        ats_duration_ms = int((time.perf_counter() - ats_started) * 1000)
        log_event(run_id, "ATS_PARSEABILITY_SCORED", "ATS parseability scored", metadata={"score": ats_breakdown.parseability_score, "warnings": len(ats_breakdown.warnings)})
        log_event(run_id, "ATS_SECTIONS_SCORED", "ATS section structure scored", metadata={"score": ats_breakdown.section_structure_score})
        log_event(run_id, "ATS_CONTACT_EXTRACTION_SCORED", "ATS contact extraction scored", metadata={"score": ats_breakdown.contact_extraction_score})
        log_event(run_id, "ATS_KEYWORDS_ANALYZED", "ATS keywords analyzed", metadata={"score": ats_breakdown.keyword_alignment_score, "keywords": len(ats_breakdown.keyword_matches)})
        log_event(run_id, "ATS_REQUIRED_SKILLS_SCORED", "ATS required skills coverage scored", metadata={"score": ats_breakdown.required_skills_coverage_score, "skills": len(ats_breakdown.skill_coverage)})
        log_event(run_id, "ATS_EVIDENCE_BACKING_SCORED", "ATS evidence backing scored", metadata={"score": ats_breakdown.evidence_backing_score})
        log_event(run_id, "ATS_FORMATTING_SCORED", "ATS formatting safety scored", metadata={"score": ats_breakdown.formatting_safety_score})
        log_event(run_id, "ATS_PENALTIES_CALCULATED", "ATS penalties calculated", metadata={"penalties": ats_breakdown.penalties, "penalty_items": len(ats_breakdown.penalty_items)})
        log_event(run_id, "ATS_RANKING_READINESS_CALCULATED", "ATS ranking readiness calculated", metadata={"score": ats_ranking.ranking_readiness_score, "band": ats_ranking.ranking_readiness_band})
        log_event(run_id, "ATS_RECOMMENDATIONS_GENERATED", "ATS recommendations generated", metadata={"recommendations": len(ats_breakdown.recommendations)})
        log_event(run_id, "ATS_SCORING_COMPLETED", "ATS-style readiness scoring completed", duration_ms=ats_duration_ms, metadata={"ats_score": ats_breakdown.final_ats_score, "band": ats_breakdown.ats_band})

        report = FinalReport(
            run_id=run_id,
            initial_score=initial_score,
            projected_final_score=projected,
            threshold=config.threshold_score,
            threshold_reached_projected=threshold_reached,
            iterations=iterations,
            stop_reason=stop_reason.value if stop_reason else None,
            score_breakdown=final_score_breakdown,
            ats_score=ats_breakdown.final_ats_score,
            ats_score_breakdown=ats_breakdown,
            ats_ranking_readiness=ats_ranking,
            matched_requirements=matched,
            partial_matches=partial,
            missing_requirements=missing,
            safe_improvements_to_add=all_safe,
            skills_to_learn=all_learn,
            needs_confirmation_suggestions=all_confirm,
            unsafe_rejected_suggestions=all_unsafe,
            interview_keywords=generate_keywords(matches),
            interview_preparation_notes=generate_notes(evidence, len(missing)),
            final_review=review,
            citations=citations,
            retrieved_chunks_summary={
                "source_index_policy": "Only original resume PDF chunks and original job description chunks are indexed.",
                "total_chunks": len(chunks),
                "resume_chunks": len([c for c in chunks if c.source_type == SourceType.resume]),
                "job_description_chunks": len([c for c in chunks if c.source_type == SourceType.job_description]),
                "average_similarity": round(sum(similarities) / len(similarities), 3) if similarities else 0,
            },
            logs_summary={
                "prompt_injection_detected": prompt_injection_detected,
                "llm_provider": os.getenv("LLM_PROVIDER", "mock"),
                "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "mock"),
                "mock_fallback_enabled": os.getenv("ENABLE_MOCK_FALLBACK", "false").lower() in {"1", "true", "yes", "on"},
                "job_cleaner_used_llm": cleaned_jd.used_llm,
                "resume_context_used_llm": resume_context.used_llm,
                "candidate_context_summary": resume_context.candidate_context_summary,
            },
            config_used=config.model_dump(),
        )
        log_event(run_id, "FINAL_REPORT_GENERATED", "Final report assembled", metadata={"citations": len(citations)})

        processing_ms = int((time.perf_counter() - started) * 1000)
        database.update_run(
            run_id,
            job_title=infer_job_title(job_description_text),
            initial_score=initial_score,
            projected_final_score=projected,
            iterations_used=len(iterations),
            stop_reason=report.stop_reason,
            processing_time_ms=processing_ms,
            llm_calls_count=llm_calls_count,
            retrieval_calls_count=len(requirements) * 2,
            average_retrieval_similarity=report.retrieved_chunks_summary["average_similarity"],
            citations_count=len(citations),
            safe_suggestions_count=len(all_safe),
            needs_confirmation_count=len(all_confirm),
            unsafe_rejected_count=len(all_unsafe),
            prompt_injection_detected=1 if prompt_injection_detected else 0,
            status="completed",
            final_report_json=report.model_dump_json(),
        )
        log_event(run_id, "RUN_COMPLETED", "Analysis run completed", duration_ms=processing_ms)
        database.save_json_rows("suggestions", run_id, [s.model_dump(mode="json") for s in all_safe + all_confirm + all_unsafe], "suggestion_json")
        database.save_json_rows("requirement_matches", run_id, [m.model_dump(mode="json") for m in matches], "match_json")
        database.save_json_rows("citations", run_id, [c.model_dump(mode="json") for c in citations], "citation_json")
        with database.get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO score_breakdowns (run_id, score_json) VALUES (?, ?)", (run_id, score.model_dump_json()))
        return report
    except Exception as exc:
        log_event(run_id, "RUN_FAILED", str(exc), level="error")
        database.update_run(run_id, status="failed", error_message=str(exc))
        raise


def get_report(run_id: str) -> FinalReport | None:
    row = database.fetch_run(run_id)
    if not row or not row.get("final_report_json"):
        return None
    return FinalReport.model_validate_json(row["final_report_json"])
