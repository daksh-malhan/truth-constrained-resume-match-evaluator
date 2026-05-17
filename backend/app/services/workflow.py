from __future__ import annotations

ANALYSIS_WORKFLOW_NODES = [
    "validate_input",
    "detect_prompt_injection",
    "parse_resume_pdf",
    "parse_job_description",
    "chunk_documents",
    "build_rag_index",
    "extract_resume_sections",
    "extract_resume_facts",
    "extract_job_requirements",
    "normalize_skills",
    "retrieve_evidence",
    "compare_requirements",
    "calculate_score",
    "detect_missing_and_weak_skills",
    "generate_truth_constrained_suggestions",
    "classify_suggestions",
    "project_score_after_safe_improvements",
    "decide_continue_or_stop",
    "generate_final_review",
    "generate_interview_keywords",
    "generate_interview_prep_notes",
    "assemble_final_report",
    "persist_run",
    "persist_logs",
]


def describe_workflow() -> dict:
    return {
        "style": "LangGraph-style deterministic orchestration",
        "parallelizable_groups": [
            ["parse_resume_pdf", "parse_job_description"],
            ["extract_resume_facts", "extract_job_requirements"],
        ],
        "max_projected_improvement_iterations": 3,
        "nodes": ANALYSIS_WORKFLOW_NODES,
    }

