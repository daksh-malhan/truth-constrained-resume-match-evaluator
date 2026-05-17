from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import database
from ..services.analysis_service import get_report

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs/{run_id}")
def run_report(run_id: str):
    report = get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Run report not found")
    return report


@router.get("/admin/runs/{run_id}/chunks")
def run_chunks(run_id: str):
    return {"run_id": run_id, "chunks": database.fetch_chunks(run_id)}

