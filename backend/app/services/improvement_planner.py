from __future__ import annotations

import re
from typing import List, Tuple

from ..schemas import EvaluationIteration, RequirementMatch, ResumeEvidence, RunConfig, ScoreBreakdown, SkillToLearn, StopReason, Suggestion, SuggestionCategory
from .skill_normalizer import detect_skills, normalize_term
from .truth_filter import classify_suggestion, safe_suggestions_only


LEARNING_PLANS = {
    "python": (
        "Python backend fundamentals",
        "Implement a typed Python service with functions, modules, error handling, file/JSON processing, and pytest coverage.",
    ),
    "backend development": (
        "Python backend service development",
        "Build a small FastAPI or Flask CRUD API with request validation, persistence, logging, and tests.",
    ),
    "rest api": (
        "REST API design and consumption",
        "Build and consume a REST API: define resources, status codes, validation, pagination, error responses, and an authenticated client script.",
    ),
    "etl": (
        "Data processing and ETL pipelines",
        "Create a CSV/JSON ingestion pipeline that validates records, transforms fields, handles bad rows, and writes clean output to SQLite or PostgreSQL.",
    ),
    "automation": (
        "Python automation scripting",
        "Write a CLI automation script that accepts arguments, processes files or API data, logs progress, and includes repeatable tests.",
    ),
    "debugging": (
        "Debugging and performance optimization",
        "Practice reproducing bugs, adding targeted logs, using a debugger/profiler, and reducing runtime for a slow Python function.",
    ),
    "oop": (
        "Object-oriented programming in Python",
        "Refactor a procedural script into classes with clear responsibilities, constructors, methods, composition, and unit tests.",
    ),
    "data structures": (
        "Data structures and algorithms fundamentals",
        "Practice arrays, strings, hash maps, stacks, queues, sorting, and Big-O analysis with Python implementations.",
    ),
    "algorithms": (
        "Data structures and algorithms fundamentals",
        "Practice arrays, strings, hash maps, stacks, queues, sorting, and Big-O analysis with Python implementations.",
    ),
    "git": (
        "Git version control workflow",
        "Practice branching, commits, pull requests, resolving merge conflicts, reading diffs, and writing clear commit messages.",
    ),
    "sql": (
        "SQL and relational data modeling",
        "Design a small schema, write joins and aggregations, add indexes, and connect it to a Python service.",
    ),
    "docker": (
        "Containerized development with Docker",
        "Containerize a Python API with a Dockerfile and compose file, configure environment variables, and run tests in the container.",
    ),
    "kubernetes": (
        "Kubernetes deployment basics",
        "Deploy a containerized API locally with manifests for Deployment, Service, ConfigMap, health checks, and basic rollout commands.",
    ),
}


PHRASE_PLANS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bbackend services?\b|\bbackend development\b", re.I), "backend development"),
    (re.compile(r"\brest\b|\bapi[s]?\b", re.I), "rest api"),
    (re.compile(r"\bdata processing\b|\betl\b|\bpipeline", re.I), "etl"),
    (re.compile(r"\bautomation\b|\bscript", re.I), "automation"),
    (re.compile(r"\bdebug|\bperformance\b|\boptimization\b", re.I), "debugging"),
    (re.compile(r"\boop\b|\bobject[- ]oriented\b", re.I), "oop"),
    (re.compile(r"\bdata structures?\b|\balgorithms?\b|\bdsa\b", re.I), "data structures"),
    (re.compile(r"\bgit\b|\bversion control\b", re.I), "git"),
]


def _learning_plan_for_requirement(requirement_text: str) -> tuple[str, str, str]:
    """Convert a missing/weak requirement into a learnable capability."""
    normalized_hits = [normalize_term(skill) for skill in detect_skills(requirement_text)]
    for pattern, canonical in PHRASE_PLANS:
        if pattern.search(requirement_text):
            title, focus = LEARNING_PLANS[canonical]
            return canonical, title, focus
    for skill in normalized_hits:
        if skill in LEARNING_PLANS:
            title, focus = LEARNING_PLANS[skill]
            return skill, title, focus

    cleaned = re.sub(r"\s+", " ", requirement_text.strip(" .,:;")).strip()
    cleaned = re.sub(r"^(strong|basic|good|solid|familiarity with|understanding of|experience with|knowledge of)\s+", "", cleaned, flags=re.I)
    title = cleaned[:70] if cleaned else "Missing role-specific capability"
    return normalize_term(title), title[0].upper() + title[1:], f"Build a small, reviewable project that demonstrates this requirement: {cleaned[:120]}"


def generate_improvement_candidates(run_id: str, weak_matches: List[RequirementMatch], evidence: List[ResumeEvidence], config: RunConfig) -> Tuple[List[Suggestion], List[SkillToLearn], List[Suggestion], List[Suggestion]]:
    """Create safe rewrites, learn-first items, confirmation prompts, and rejections."""
    safe: List[Suggestion] = []
    learn: List[SkillToLearn] = []
    confirm: List[Suggestion] = []
    unsafe: List[Suggestion] = []
    source_by_id = {ev.id: ev for ev in evidence}
    learned_keys: set[str] = set()

    for idx, match in enumerate(weak_matches[:8]):
        citations = match.citations
        matched_evidence = [source_by_id[eid] for eid in match.matched_evidence_ids if eid in source_by_id]
        if matched_evidence:
            ev = matched_evidence[0]
            candidate = f"Clarify existing evidence without adding new claims: {ev.text}"
            suggestion = classify_suggestion(f"sug_safe_{idx}", candidate, matched_evidence, [match.requirement_id], citations, ev.text)
            if suggestion.category == SuggestionCategory.safe_rewrite:
                safe.append(suggestion)
            else:
                unsafe.append(suggestion)

        canonical_skill, learning_title, learning_focus = _learning_plan_for_requirement(match.requirement_text)
        if canonical_skill not in learned_keys:
            learned_keys.add(canonical_skill)
            learn.append(
                SkillToLearn(
                    skill=learning_title,
                    reason=(
                        "The job asks for this concrete capability, but the original resume evidence is missing or only weakly supports it. "
                        "Treat this as a learning target, not a resume claim."
                    ),
                    related_job_requirements=[match.requirement_id],
                    priority="high" if match.status == "missing" else "medium",
                    citations=citations,
                    suggested_learning_focus=learning_focus,
                )
            )
        confirm.append(
            Suggestion(
                id=f"sug_confirm_{idx}",
                suggested_text=f"If true, confirm direct experience with: {match.requirement_text[:120]}",
                category=SuggestionCategory.needs_confirmation,
                reason="This may be useful but is not explicitly supported by the uploaded resume.",
                supporting_evidence_ids=[],
                affected_requirement_ids=[match.requirement_id],
                citations=citations,
                can_affect_projected_score=False,
            )
        )
        unsafe.append(
            Suggestion(
                id=f"sug_unsafe_{idx}",
                suggested_text=f"Claim direct, measurable production experience for: {match.requirement_text[:120]}",
                category=SuggestionCategory.unsafe,
                reason="Unsupported production or metric claims would fabricate experience.",
                supporting_evidence_ids=[],
                affected_requirement_ids=[match.requirement_id],
                citations=citations,
                can_affect_projected_score=False,
            )
        )
    return safe, learn, confirm, unsafe


def project_score(score_before: float, safe_improvements: List[Suggestion], config: RunConfig) -> float:
    """Project score changes from SAFE_REWRITE suggestions only."""
    effective = safe_suggestions_only(safe_improvements)
    delta = min(1.2, 0.35 * len(effective))
    return round(min(10.0, score_before + delta), 2)


def run_improvement_loop(
    run_id: str,
    initial_score: float,
    base_breakdown: ScoreBreakdown,
    matches: List[RequirementMatch],
    evidence: List[ResumeEvidence],
    config: RunConfig,
) -> Tuple[List[EvaluationIteration], float, StopReason | None]:
    if not config.enable_improvement_loop:
        return [], initial_score, None

    iterations: List[EvaluationIteration] = []
    current = initial_score
    stop_reason: StopReason | None = None
    weak = [m for m in matches if m.status in {"missing", "weak_match", "partial_match"}]

    for iteration_number in range(1, min(config.max_iterations, 3) + 1):
        safe, learn, confirm, unsafe = generate_improvement_candidates(run_id, weak, evidence, config)
        projected = project_score(current, safe, config)
        delta = round(projected - current, 2)

        if projected >= config.threshold_score:
            stop_reason = StopReason.threshold_reached
        elif not safe:
            stop_reason = StopReason.no_safe_improvements
        elif delta < config.min_improvement:
            stop_reason = StopReason.min_improvement_not_met
        elif iteration_number >= min(config.max_iterations, 3):
            stop_reason = StopReason.max_iterations

        iteration = EvaluationIteration(
            iteration_number=iteration_number,
            score_before=current,
            projected_score_after=projected,
            improvement_delta=delta,
            safe_improvements=safe,
            skills_to_learn=learn,
            needs_confirmation_suggestions=confirm,
            unsafe_rejected_suggestions=unsafe,
            stop_reason=stop_reason,
            score_breakdown=base_breakdown.model_copy(update={"final_score": projected, "score_band": "good match" if projected >= 7 else base_breakdown.score_band}),
            citations=[citation for match in weak[:5] for citation in match.citations],
        )
        iterations.append(iteration)
        current = projected
        if stop_reason:
            break
    return iterations, current, stop_reason
