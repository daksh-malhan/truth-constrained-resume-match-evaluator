from __future__ import annotations

import json
import os
from typing import Dict, List

import httpx
from pydantic import BaseModel, Field

from ..config import ollama_base_url
from ..schemas import ResumeEvidence
from .skill_normalizer import detect_skills


class ResumeEvidenceUpdate(BaseModel):
    evidence_id: str
    evidence_type: str
    impact_level: str = "unknown"
    contextual_summary: str = ""
    concrete_skills_tools: List[str] = Field(default_factory=list)


class ResumeContextResult(BaseModel):
    candidate_context_summary: str = ""
    evidence_updates: List[ResumeEvidenceUpdate] = Field(default_factory=list)
    used_llm: bool = False
    warning: str | None = None


ACTION_VERBS = (
    "built", "created", "developed", "implemented", "modeled", "designed", "organized",
    "containerized", "integrated", "automated", "optimized", "debugged", "persisted",
    "served", "backed", "trained", "deployed",
)


def deterministic_contextualize_resume(evidence: List[ResumeEvidence]) -> ResumeContextResult:
    updates: List[ResumeEvidenceUpdate] = []
    project_like = 0
    skill_terms: set[str] = set()
    for item in evidence:
        lowered = item.text.lower()
        inferred_type = item.evidence_type
        if item.evidence_type in {"other", "skill", "summary"} and any(verb in lowered for verb in ACTION_VERBS):
            inferred_type = "project"
            project_like += 1
        elif item.evidence_type == "other" and any(term in lowered for term in ["coursework", "degree", "university", "education"]):
            inferred_type = "education"
        skills = detect_skills(item.text)
        skill_terms.update(skills)
        impact = "high" if item.has_metric else ("medium" if skills or inferred_type in {"project", "work_experience"} else item.impact_level)
        if inferred_type != item.evidence_type or impact != item.impact_level:
            updates.append(
                ResumeEvidenceUpdate(
                    evidence_id=item.id,
                    evidence_type=inferred_type,
                    impact_level=impact,
                    contextual_summary=item.text[:180],
                    concrete_skills_tools=skills,
                )
            )
    summary = f"Resume contains {project_like} action-oriented project/work evidence items and explicit skills/tools: {', '.join(sorted(skill_terms)[:16])}."
    return ResumeContextResult(candidate_context_summary=summary, evidence_updates=updates, used_llm=False)


def llm_contextualize_resume(evidence: List[ResumeEvidence]) -> ResumeContextResult:
    model = os.getenv("OLLAMA_RESUME_CONTEXT_MODEL", "llama3.2:latest")
    timeout = float(os.getenv("OLLAMA_RESUME_CONTEXT_TIMEOUT_SECONDS", "25"))
    max_tokens = int(os.getenv("OLLAMA_RESUME_CONTEXT_NUM_PREDICT", "450"))
    priority = sorted(
        evidence,
        key=lambda item: (
            not any(verb in item.text.lower() for verb in ACTION_VERBS),
            not bool(item.skills_detected),
            len(item.text),
        ),
    )[:24]
    compact = [
        {
            "id": item.id,
            "section": item.section_name,
            "text": item.text[:260],
            "current_type": item.evidence_type,
            "skills_detected": item.skills_detected,
            "has_metric": item.has_metric,
        }
        for item in priority
    ]
    system_prompt = (
        "Classify resume evidence context using only the supplied evidence. Return compact strict JSON with "
        "candidate_context_summary and evidence_updates. evidence_updates must reference existing evidence_id values. "
        "Use evidence_type project for action-oriented project bullets, work_experience for job bullets, skill for lists, "
        "education for coursework/degrees, otherwise other. Do not invent tools, metrics, companies, degrees, or outcomes."
    )
    response = httpx.post(
        f"{ollama_base_url()}/api/chat",
        json={
            "model": model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps({"resume_evidence": compact})},
            ],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    content = response.json().get("message", {}).get("content", "{}")
    try:
        result = ResumeContextResult.model_validate_json(content)
    except Exception:
        raw = json.loads(content)
        if not isinstance(raw.get("candidate_context_summary", ""), str):
            raw["candidate_context_summary"] = json.dumps(raw.get("candidate_context_summary", ""), default=str)
        repaired_updates = []
        for update in raw.get("evidence_updates", []) or []:
            if isinstance(update, dict):
                repaired = dict(update)
                if "evidence_id" not in repaired and "id" in repaired:
                    repaired["evidence_id"] = repaired["id"]
                if "evidence_type" not in repaired and "type" in repaired:
                    repaired["evidence_type"] = repaired["type"]
                repaired_updates.append(repaired)
        raw["evidence_updates"] = repaired_updates
        result = ResumeContextResult.model_validate(raw)
    result.used_llm = True
    return result


def _apply_update(item: ResumeEvidence, update: ResumeEvidenceUpdate, full_resume_text: str) -> ResumeEvidence:
    allowed_types = {"project", "work_experience", "education", "certification", "skill", "summary", "other"}
    allowed_impacts = {"low", "medium", "high", "unknown"}
    data = item.model_dump()
    if update.evidence_type in allowed_types:
        data["evidence_type"] = update.evidence_type
    if update.impact_level in allowed_impacts:
        data["impact_level"] = update.impact_level
    grounded_terms = []
    full_lower = full_resume_text.lower()
    for term in update.concrete_skills_tools:
        normalized = term.strip().lower()
        if normalized and normalized in full_lower:
            grounded_terms.append(normalized)
    detected = sorted(set(data.get("skills_detected", []) + data.get("tools_detected", []) + detect_skills(" ".join(grounded_terms))))
    data["skills_detected"] = detected
    data["tools_detected"] = detected
    data["confidence"] = max(float(data.get("confidence", 0.65)), 0.82)
    return ResumeEvidence(**data)


def contextualize_resume_evidence(evidence: List[ResumeEvidence], full_resume_text: str) -> tuple[List[ResumeEvidence], ResumeContextResult]:
    if os.getenv("ENABLE_RESUME_CONTEXT_LLM", "true").lower() in {"1", "true", "yes", "on"} and os.getenv("LLM_PROVIDER", "mock").lower() == "ollama":
        try:
            context = llm_contextualize_resume(evidence)
            deterministic = deterministic_contextualize_resume(evidence)
            existing_update_ids = {update.evidence_id for update in context.evidence_updates}
            context.evidence_updates.extend(update for update in deterministic.evidence_updates if update.evidence_id not in existing_update_ids)
            if deterministic.candidate_context_summary and deterministic.candidate_context_summary not in context.candidate_context_summary:
                context.candidate_context_summary = f"{context.candidate_context_summary} {deterministic.candidate_context_summary}".strip()
        except Exception as exc:
            context = deterministic_contextualize_resume(evidence)
            context.warning = f"Resume context LLM failed; deterministic contextualizer used: {exc}"
    else:
        context = deterministic_contextualize_resume(evidence)

    by_id: Dict[str, ResumeEvidence] = {item.id: item for item in evidence}
    for update in context.evidence_updates:
        if update.evidence_id in by_id:
            by_id[update.evidence_id] = _apply_update(by_id[update.evidence_id], update, full_resume_text)
    return [by_id[item.id] for item in evidence], context
