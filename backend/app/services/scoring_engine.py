from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from typing import Dict, Iterable, List, Tuple

from ..schemas import Citation, JobRequirement, RequirementMatch, ResumeEvidence, RetrievedChunk, RunConfig, ScoreBreakdown
from .embedding_provider import embed_text
from .inference_matcher import infer_requirement_support_batch
from .rag_indexer import retrieve
from .skill_normalizer import best_partial_match, detect_skills


def score_band(score: float) -> str:
    if score >= 8.5:
        return "strong match"
    if score >= 7.0:
        return "good match"
    if score >= 5.5:
        return "partial match"
    if score >= 4.0:
        return "weak match"
    return "poor match"


def status_for_strength(strength: float) -> str:
    if strength >= 0.85:
        return "strong_match"
    if strength >= 0.6:
        return "partial_match"
    if strength >= 0.2:
        return "weak_match"
    return "missing"


def match_type_for_strength(strength: float) -> str:
    if strength >= 0.98:
        return "exact"
    if strength >= 0.8:
        return "direct"
    if strength >= 0.6:
        return "semantic"
    if strength >= 0.35:
        return "adjacent"
    if strength >= 0.2:
        return "weak"
    return "missing"


def compare_requirements(run_id: str, requirements: List[JobRequirement], evidence: List[ResumeEvidence], config: RunConfig) -> Tuple[List[RequirementMatch], List[float]]:
    """Compare job requirements to resume evidence with retrieval and bounded LLM inference.

    The deterministic path assigns exact/direct/semantic/adjacent credit first. Only
    weak or missing cases are sent to the lightweight inference matcher, and that
    matcher is capped so it can never claim stronger than semantic partial support.
    """
    resume_terms = sorted({skill for ev in evidence for skill in ev.skills_detected + ev.tools_detected})
    similarities: List[float] = []
    evidence_by_skill: Dict[str, List[ResumeEvidence]] = defaultdict(list)
    for ev in evidence:
        for skill in ev.skills_detected + ev.tools_detected:
            evidence_by_skill[skill].append(ev)

    def retrieve_for_requirement(index: int, req: JobRequirement) -> tuple[int, List[RetrievedChunk], List[RetrievedChunk]]:
        query_embedding = embed_text(req.text)
        retrieved_resume = retrieve(
            run_id,
            req.text,
            "resume",
            config.top_k_resume_chunks,
            config.vector_store_provider,
            query_embedding=query_embedding,
        )
        retrieved_jd = retrieve(
            run_id,
            req.text,
            "job_description",
            min(2, config.top_k_job_chunks),
            config.vector_store_provider,
            query_embedding=query_embedding,
        )
        return index, retrieved_resume, retrieved_jd

    retrieval_results: List[tuple[List[RetrievedChunk], List[RetrievedChunk]]] = [([], []) for _ in requirements]
    if requirements:
        workers = max(1, int(os.getenv("RAG_RETRIEVAL_MAX_WORKERS", "8")))
        # Resume and JD retrieval are independent per requirement, so they can run
        # concurrently without changing the deterministic scoring formula.
        with ThreadPoolExecutor(max_workers=min(workers, len(requirements))) as executor:
            futures = [executor.submit(retrieve_for_requirement, index, req) for index, req in enumerate(requirements)]
            for future in as_completed(futures):
                index, retrieved_resume, retrieved_jd = future.result()
                retrieval_results[index] = (retrieved_resume, retrieved_jd)

    base_matches = []
    inference_items: List[tuple[JobRequirement, List[RetrievedChunk]]] = []
    inference_indexes: List[int] = []
    for index, req in enumerate(requirements):
        retrieved_resume, retrieved_jd = retrieval_results[index]
        similarities.extend([r.similarity_score for r in retrieved_resume + retrieved_jd])

        target = req.normalized_skill_or_requirement
        matched_term, partial = best_partial_match(target, resume_terms)
        direct_evidence = evidence_by_skill.get(target, [])
        matched_evidence = direct_evidence or (evidence_by_skill.get(matched_term or "", []) if matched_term else [])

        if target in resume_terms:
            strength = 1.0 if any(ev.has_metric or ev.evidence_type in {"project", "work_experience"} for ev in direct_evidence) else 0.75
        elif partial >= 0.8:
            strength = config.direct_match_score
        elif partial >= 0.6:
            strength = config.semantic_match_score
        elif partial >= 0.3:
            strength = config.adjacent_match_score
        elif retrieved_resume and retrieved_resume[0].similarity_score >= config.similarity_threshold:
            strength = config.weak_match_score
        else:
            strength = config.missing_match_score

        confidence = min(0.95, max(req.confidence, retrieved_resume[0].similarity_score if retrieved_resume else 0.4))
        min_inference_similarity = float(os.getenv("INFERENCE_MATCH_MIN_SIMILARITY", "0.32"))
        if strength < config.semantic_match_score and retrieved_resume and retrieved_resume[0].similarity_score >= min_inference_similarity:
            inference_indexes.append(index)
            inference_items.append((req, retrieved_resume))

        base_matches.append(
            {
                "req": req,
                "target": target,
                "matched_evidence": matched_evidence,
                "retrieved_resume": retrieved_resume,
                "retrieved_jd": retrieved_jd,
                "strength": strength,
                "confidence": confidence,
                "inference_reason": "",
                "inferred_chunk_ids": set(),
            }
        )

    # Batched inference preserves output order through inference_indexes, avoiding
    # serial local-LLM calls while keeping each result tied to its original requirement.
    inferred_results = infer_requirement_support_batch(inference_items)
    for base_index, inferred in zip(inference_indexes, inferred_results):
        base = base_matches[base_index]
        if inferred.can_infer and inferred.evidence_strength > base["strength"]:
            base["strength"] = inferred.evidence_strength
            base["confidence"] = max(base["req"].confidence, inferred.confidence)
            base["inference_reason"] = f" LLM inference: {inferred.reason}"
            base["inferred_chunk_ids"] = set(inferred.supporting_chunk_ids)

    matches: List[RequirementMatch] = []
    for base in base_matches:
        req = base["req"]
        target = base["target"]
        matched_evidence = base["matched_evidence"]
        retrieved_resume = base["retrieved_resume"]
        retrieved_jd = base["retrieved_jd"]
        strength = base["strength"]
        confidence = base["confidence"]
        inferred_chunk_ids = base["inferred_chunk_ids"]
        weighted_score = strength * req.importance_weight * confidence
        citations: List[Citation] = [r.citation for r in retrieved_resume[:2] + retrieved_jd[:1]]
        explanation = (
            f"Requirement '{target}' has {match_type_for_strength(strength)} evidence"
            if strength > 0
            else f"No resume evidence safely supports '{target}'."
        )
        if base["inference_reason"]:
            explanation += base["inference_reason"]
        matches.append(
            RequirementMatch(
                requirement_id=req.id,
                requirement_text=req.text,
                matched_evidence_ids=[ev.id for ev in matched_evidence[:3]],
                retrieved_chunk_ids=[r.chunk_id for r in retrieved_resume[:3] + retrieved_jd[:1] if r.chunk_id not in inferred_chunk_ids] + list(inferred_chunk_ids),
                match_type=match_type_for_strength(strength),  # type: ignore[arg-type]
                evidence_strength=round(strength, 3),
                confidence=round(confidence, 3),
                importance_weight=req.importance_weight,
                weighted_score=round(weighted_score, 3),
                status=status_for_strength(strength),  # type: ignore[arg-type]
                explanation=explanation,
                citations=citations,
            )
        )
    return matches, similarities


def _category_score(requirements: List[JobRequirement], matches: List[RequirementMatch], categories: Iterable[str], weight: float) -> float:
    req_ids = {r.id for r in requirements if r.category in set(categories)}
    relevant = [m for m in matches if m.requirement_id in req_ids]
    if not relevant:
        # Neutral/full credit for irrelevant categories prevents a job description
        # with no education/cloud/domain requirement from penalizing the candidate.
        return weight
    numerator = sum(m.evidence_strength * m.importance_weight * m.confidence for m in relevant)
    denominator = sum(m.importance_weight for m in relevant) or 1.0
    return round(max(0.0, min(weight, numerator / denominator * weight)), 3)


def calculate_score(requirements: List[JobRequirement], matches: List[RequirementMatch], evidence: List[ResumeEvidence], config: RunConfig, prompt_injection_detected: bool = False) -> ScoreBreakdown:
    core = _category_score(requirements, matches, {"technical_skill", "tool"}, config.core_technical_skills_weight)
    experience = _category_score(requirements, matches, {"experience"}, config.experience_seniority_weight)
    project = round(min(config.project_work_evidence_weight, (sum(1 for ev in evidence if ev.evidence_type in {"project", "work_experience"} and ev.skills_detected) / 4) * config.project_work_evidence_weight), 3)
    responsibility = _category_score(requirements, matches, {"responsibility"}, config.responsibility_match_weight)
    domain = _category_score(requirements, matches, {"domain"}, config.domain_context_weight)
    education = _category_score(requirements, matches, {"education", "certification"}, config.education_certifications_weight)
    resume_text = " ".join(ev.text for ev in evidence)
    req_terms = {r.normalized_skill_or_requirement for r in requirements}
    resume_terms = set(detect_skills(resume_text))
    ats = round((len(req_terms & resume_terms) / (len(req_terms) or 1)) * config.ats_keyword_weight, 3)
    communication = round(min(config.resume_communication_weight, (0.35 + 0.1 * sum(1 for ev in evidence if ev.has_metric)) * config.resume_communication_weight), 3)
    interview = round(min(config.interview_readiness_weight, (sum(1 for ev in evidence if ev.evidence_type in {"project", "work_experience"} and len(ev.text.split()) > 6) / 5) * config.interview_readiness_weight), 3)
    risk = min(config.max_risk_penalty, 0.25 if prompt_injection_detected else 0.0)
    total = core + experience + project + responsibility + domain + education + ats + communication + interview - risk
    final = round(max(0.0, min(10.0, total)), 2)
    return ScoreBreakdown(
        core_technical_skills_score=core,
        experience_seniority_score=experience,
        project_work_evidence_score=project,
        responsibility_match_score=responsibility,
        domain_context_score=domain,
        education_certification_score=education,
        ats_keyword_score=ats,
        resume_communication_score=communication,
        interview_readiness_score=interview,
        risk_penalty=risk,
        final_score=final,
        score_band=score_band(final),
    )
