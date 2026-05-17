from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from .. import database
from ..config import default_config
from ..services.admin_config_service import get_active_config, reset_config, update_config

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/config")
def get_config():
    config = get_active_config()
    return {"config": config, "total_before_penalty": round(sum([
        config.core_technical_skills_weight,
        config.experience_seniority_weight,
        config.project_work_evidence_weight,
        config.responsibility_match_weight,
        config.domain_context_weight,
        config.education_certifications_weight,
        config.ats_keyword_weight,
        config.resume_communication_weight,
        config.interview_readiness_weight,
    ]), 2), "ats_total_before_penalty": round(sum([
        config.ats_parseability_weight,
        config.ats_section_structure_weight,
        config.ats_contact_extraction_weight,
        config.ats_keyword_alignment_weight,
        config.ats_required_skills_weight,
        config.ats_evidence_backing_weight,
        config.ats_formatting_safety_weight,
        config.ats_communication_quality_weight,
        config.ats_role_targeting_weight,
    ]), 2)}


@router.put("/config")
def put_config(payload: dict):
    return {"config": update_config(payload)}


@router.post("/config/reset")
def reset():
    return {"config": reset_config()}


@router.get("/logs")
def logs(run_id: Optional[str] = None, level: Optional[str] = None, limit: int = 200):
    return {"logs": database.fetch_logs(run_id=run_id, level=level, limit=limit)}


@router.get("/runs")
def runs(limit: int = 50):
    rows = database.fetch_runs(limit)
    completed = [r for r in rows if r["status"] == "completed"]
    avg_processing = round(sum((r["processing_time_ms"] or 0) for r in completed) / len(completed), 2) if completed else 0
    avg_initial = round(sum((r["initial_score"] or 0) for r in completed) / len(completed), 2) if completed else 0
    avg_projected = round(sum((r["projected_final_score"] or 0) for r in completed) / len(completed), 2) if completed else 0
    return {
        "runs": rows,
        "metrics": {
            "total_runs": len(rows),
            "failed_runs": len([r for r in rows if r["status"] == "failed"]),
            "average_processing_time_ms": avg_processing,
            "average_initial_score": avg_initial,
            "average_projected_score": avg_projected,
            "vector_store_provider": get_active_config().vector_store_provider,
        },
    }


@router.get("/runs/{run_id}")
def run_metadata(run_id: str):
    return {"run": database.fetch_run(run_id)}


@router.get("/runs/{run_id}/logs")
def run_logs(run_id: str):
    return {"logs": database.fetch_logs(run_id=run_id, limit=500)}
