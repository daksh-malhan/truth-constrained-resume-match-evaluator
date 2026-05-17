from __future__ import annotations

from pathlib import Path
from typing import Optional

from .. import database
from ..schemas import ResumeSection, RunConfig
from .analysis_service import get_report, importance_weight_map
from .job_parser import extract_job_requirements
from .pdf_parser import parse_resume_pdf as parse_pdf_bytes
from .rag_indexer import retrieve
from .resume_extractor import extract_resume_evidence
from .scoring_engine import calculate_score, compare_requirements
from .improvement_planner import generate_improvement_candidates


try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    FastMCP = None  # type: ignore


def create_mcp_server():
    if FastMCP is None:
        raise RuntimeError("mcp package is not installed")
    mcp = FastMCP("truth-constrained-resume-match-evaluator")

    @mcp.tool()
    def parse_resume_pdf(file_path: str) -> dict:
        path = Path(file_path)
        sections = parse_pdf_bytes(path.read_bytes())
        return {"sections": [s.model_dump(mode="json") for s in sections]}

    @mcp.tool()
    def extract_resume_facts(run_id: str) -> dict:
        chunks = database.fetch_chunks(run_id)
        sections: list[ResumeSection] = []
        for idx, chunk in enumerate([c for c in chunks if c["source_type"] == "resume"]):
            sections.append(
                ResumeSection(
                    id=f"section_{idx}",
                    section_name=chunk.get("section_name") or "Other",
                    text=chunk["text"],
                    page_number=chunk.get("page_number") or 1,
                    source_quote=chunk["text"][:300],
                    confidence=0.75,
                )
            )
        facts = extract_resume_evidence(sections)
        return {"facts": [fact.model_dump(mode="json") for fact in facts]}

    @mcp.tool()
    def extract_job_requirements(job_description_text: str) -> dict:
        config = RunConfig()
        reqs = extract_job_requirements(job_description_text, importance_weight_map(config))
        return {"requirements": [r.model_dump(mode="json") for r in reqs]}

    @mcp.tool()
    def build_rag_index(run_id: str) -> dict:
        chunks = database.fetch_chunks(run_id)
        return {"run_id": run_id, "indexed_chunks_count": len(chunks), "vector_store_provider": "sqlite-local", "metadata": {"source_truth_only": True}}

    @mcp.tool()
    def retrieve_evidence(run_id: str, query: str, source_type: Optional[str] = "both", top_k: int = 5) -> dict:
        results = retrieve(run_id, query, source_type, top_k)
        return {"chunks": [r.model_dump(mode="json") for r in results]}

    @mcp.tool()
    def get_run_report(run_id: str) -> dict:
        report = get_report(run_id)
        return report.model_dump(mode="json") if report else {"error": "run not found"}

    @mcp.tool()
    def compare_resume_to_job(run_id: str) -> dict:
        report = get_report(run_id)
        if not report:
            return {"error": "run not found"}
        return {
            "matched_requirements": [m.model_dump(mode="json") for m in report.matched_requirements],
            "partial_matches": [m.model_dump(mode="json") for m in report.partial_matches],
            "missing_requirements": [m.model_dump(mode="json") for m in report.missing_requirements],
        }

    @mcp.tool()
    def calculate_match_score(run_id: str) -> dict:
        report = get_report(run_id)
        if not report:
            return {"error": "run not found"}
        return {"score_breakdown": report.score_breakdown.model_dump(mode="json"), "final_score": report.projected_final_score}

    @mcp.tool()
    def generate_improvement_plan(run_id: str, threshold: float) -> dict:
        report = get_report(run_id)
        if not report:
            return {"error": "run not found"}
        return {
            "threshold": threshold,
            "safe_improvements": [s.model_dump(mode="json") for s in report.safe_improvements_to_add],
            "skills_to_learn": [s.model_dump(mode="json") for s in report.skills_to_learn],
            "needs_confirmation": [s.model_dump(mode="json") for s in report.needs_confirmation_suggestions],
            "rejected": [s.model_dump(mode="json") for s in report.unsafe_rejected_suggestions],
        }

    @mcp.tool()
    def get_run_logs(run_id: str) -> dict:
        return {"logs": database.fetch_logs(run_id=run_id, limit=500)}

    return mcp


if __name__ == "__main__":  # pragma: no cover
    database.init_db()
    create_mcp_server().run()
