from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from ..config import parse_json_overrides
from ..services.analysis_service import analyze_resume_job

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze")
async def analyze(
    resume_pdf: UploadFile = File(...),
    job_description_text: str = Form(...),
    threshold: Optional[float] = Form(None),
    config_overrides: Optional[str] = Form(None),
):
    try:
        pdf_bytes = await resume_pdf.read()
        overrides = parse_json_overrides(config_overrides)
        return await run_in_threadpool(
            analyze_resume_job,
            resume_filename=resume_pdf.filename or "resume.pdf",
            content_type=resume_pdf.content_type,
            pdf_bytes=pdf_bytes,
            job_description_text=job_description_text,
            threshold=threshold,
            config_overrides=overrides,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)})
