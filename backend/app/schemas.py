from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    resume = "resume"
    job_description = "job_description"


class SuggestionCategory(str, Enum):
    safe_rewrite = "SAFE_REWRITE"
    needs_confirmation = "NEEDS_USER_CONFIRMATION"
    unsafe = "UNSAFE_OR_FABRICATED"


class StopReason(str, Enum):
    threshold_reached = "THRESHOLD_REACHED_PROJECTED"
    max_iterations = "MAX_ITERATIONS_REACHED"
    no_safe_improvements = "NO_SAFE_IMPROVEMENTS"
    min_improvement_not_met = "MIN_IMPROVEMENT_NOT_MET"
    truth_blocked = "TRUTH_CONSTRAINT_BLOCKED"
    rag_insufficient = "RAG_EVIDENCE_INSUFFICIENT"
    error = "ERROR"


class RunConfig(BaseModel):
    threshold_score: float = 8.0
    max_iterations: int = 3
    min_improvement: float = 0.3
    enable_improvement_loop: bool = True
    enable_truth_filter: bool = True
    enable_rag_retrieval: bool = True
    enable_prompt_injection_detection: bool = True
    core_technical_skills_weight: float = 3.0
    experience_seniority_weight: float = 1.5
    project_work_evidence_weight: float = 1.5
    responsibility_match_weight: float = 1.0
    domain_context_weight: float = 0.75
    education_certifications_weight: float = 0.5
    ats_keyword_weight: float = 0.75
    resume_communication_weight: float = 0.75
    interview_readiness_weight: float = 0.25
    max_risk_penalty: float = 1.0
    chunk_size: int = 600
    chunk_overlap: int = 100
    top_k_resume_chunks: int = 5
    top_k_job_chunks: int = 5
    similarity_threshold: float = 0.65
    embedding_model: str = "mock-hashing-embedding"
    vector_store_provider: Literal["qdrant", "chroma", "faiss"] = "faiss"
    reranking_enabled: bool = False
    citation_required: bool = True
    exact_match_score: float = 1.0
    direct_match_score: float = 0.8
    semantic_match_score: float = 0.6
    adjacent_match_score: float = 0.4
    weak_match_score: float = 0.2
    missing_match_score: float = 0.0
    must_have_weight: float = 1.0
    repeated_weight: float = 0.9
    main_responsibility_weight: float = 0.8
    preferred_weight: float = 0.6
    nice_to_have_weight: float = 0.4
    generic_weight: float = 0.3
    enable_ats_scoring: bool = True
    enable_ats_ranking_readiness: bool = True
    ats_parseability_weight: float = 15.0
    ats_section_structure_weight: float = 10.0
    ats_contact_extraction_weight: float = 8.0
    ats_keyword_alignment_weight: float = 18.0
    ats_required_skills_weight: float = 18.0
    ats_evidence_backing_weight: float = 12.0
    ats_formatting_safety_weight: float = 8.0
    ats_communication_quality_weight: float = 7.0
    ats_role_targeting_weight: float = 4.0
    ats_max_penalty: float = 15.0
    ats_exact_keyword_weight: float = 1.0
    ats_normalized_keyword_weight: float = 0.8
    ats_semantic_keyword_weight: float = 0.6
    ats_adjacent_keyword_weight: float = 0.4
    ats_weak_keyword_weight: float = 0.2
    penalize_keyword_stuffing: bool = True
    penalize_unparseable_formatting: bool = True
    penalize_missing_contact_info: bool = True
    penalize_unsupported_claims: bool = True
    penalize_prompt_injection: bool = True
    penalize_generic_resume: bool = True
    check_tables: bool = True
    check_columns: bool = True
    check_images: bool = True
    check_headers_footers: bool = True
    check_weird_characters: bool = True
    check_bullet_extraction: bool = True

    @field_validator("threshold_score")
    @classmethod
    def threshold_range(cls, value: float) -> float:
        if not 0 <= value <= 10:
            raise ValueError("threshold_score must be between 0 and 10")
        return value

    @field_validator("max_iterations")
    @classmethod
    def max_iterations_reasonable(cls, value: int) -> int:
        if not 0 <= value <= 10:
            raise ValueError("max_iterations must be between 0 and 10")
        return value

    @field_validator("similarity_threshold")
    @classmethod
    def similarity_range(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        return value

    @field_validator("chunk_size")
    @classmethod
    def chunk_size_reasonable(cls, value: int) -> int:
        if not 100 <= value <= 4000:
            raise ValueError("chunk_size must be between 100 and 4000")
        return value

    @field_validator("chunk_overlap")
    @classmethod
    def chunk_overlap_reasonable(cls, value: int) -> int:
        if not 0 <= value <= 1000:
            raise ValueError("chunk_overlap must be between 0 and 1000")
        return value

    @field_validator("top_k_resume_chunks", "top_k_job_chunks")
    @classmethod
    def top_k_reasonable(cls, value: int) -> int:
        if not 1 <= value <= 25:
            raise ValueError("top_k chunk settings must be between 1 and 25")
        return value

    @field_validator(
        "core_technical_skills_weight",
        "experience_seniority_weight",
        "project_work_evidence_weight",
        "responsibility_match_weight",
        "domain_context_weight",
        "education_certifications_weight",
        "ats_keyword_weight",
        "resume_communication_weight",
        "interview_readiness_weight",
        "max_risk_penalty",
        "exact_match_score",
        "direct_match_score",
        "semantic_match_score",
        "adjacent_match_score",
        "weak_match_score",
        "missing_match_score",
        "must_have_weight",
        "repeated_weight",
        "main_responsibility_weight",
        "preferred_weight",
        "nice_to_have_weight",
        "generic_weight",
        "ats_parseability_weight",
        "ats_section_structure_weight",
        "ats_contact_extraction_weight",
        "ats_keyword_alignment_weight",
        "ats_required_skills_weight",
        "ats_evidence_backing_weight",
        "ats_formatting_safety_weight",
        "ats_communication_quality_weight",
        "ats_role_targeting_weight",
        "ats_max_penalty",
        "ats_exact_keyword_weight",
        "ats_normalized_keyword_weight",
        "ats_semantic_keyword_weight",
        "ats_adjacent_keyword_weight",
        "ats_weak_keyword_weight",
    )
    @classmethod
    def non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("weights must be non-negative")
        return value


class ResumeSection(BaseModel):
    id: str
    section_name: str
    text: str
    page_number: int
    source_quote: str
    confidence: float = 0.8


class Citation(BaseModel):
    source_type: SourceType
    source_location: str
    quote: str
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    paragraph_index: Optional[int] = None
    chunk_id: Optional[str] = None
    similarity_score: Optional[float] = None


class ResumeEvidence(BaseModel):
    id: str
    section_name: str
    text: str
    skills_detected: List[str] = Field(default_factory=list)
    tools_detected: List[str] = Field(default_factory=list)
    evidence_type: Literal["project", "work_experience", "education", "certification", "skill", "summary", "other"] = "other"
    has_metric: bool = False
    metric_text: Optional[str] = None
    impact_level: Literal["low", "medium", "high", "unknown"] = "unknown"
    source_location: str
    source_quote: str
    page_number: Optional[int] = None
    confidence: float = 0.8


class JobRequirement(BaseModel):
    id: str
    text: str
    normalized_skill_or_requirement: str
    category: Literal["technical_skill", "responsibility", "experience", "education", "certification", "domain", "soft_skill", "tool", "keyword", "other"]
    importance: Literal["must_have", "repeated", "main_responsibility", "preferred", "nice_to_have", "generic"] = "generic"
    importance_weight: float = 0.3
    source_location: str
    source_quote: str
    paragraph_index: Optional[int] = None
    confidence: float = 0.8


class RagChunk(BaseModel):
    id: str
    run_id: str
    source_type: SourceType
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    paragraph_index: Optional[int] = None
    chunk_index: int
    original_text: str


class RetrievedChunk(BaseModel):
    chunk_id: str
    source_type: SourceType
    text: str
    similarity_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    citation: Citation


class RequirementMatch(BaseModel):
    requirement_id: str
    requirement_text: str
    matched_evidence_ids: List[str] = Field(default_factory=list)
    retrieved_chunk_ids: List[str] = Field(default_factory=list)
    match_type: Literal["exact", "direct", "semantic", "adjacent", "weak", "missing"] = "missing"
    evidence_strength: float = 0.0
    confidence: float = 0.8
    importance_weight: float = 0.3
    weighted_score: float = 0.0
    status: Literal["strong_match", "partial_match", "weak_match", "missing"] = "missing"
    explanation: str
    citations: List[Citation] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    core_technical_skills_score: float = 0.0
    experience_seniority_score: float = 0.0
    project_work_evidence_score: float = 0.0
    responsibility_match_score: float = 0.0
    domain_context_score: float = 0.0
    education_certification_score: float = 0.0
    ats_keyword_score: float = 0.0
    resume_communication_score: float = 0.0
    interview_readiness_score: float = 0.0
    risk_penalty: float = 0.0
    final_score: float = 0.0
    score_band: str = "poor match"


class Suggestion(BaseModel):
    id: str
    original_text: Optional[str] = None
    suggested_text: str
    category: SuggestionCategory
    reason: str
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    affected_requirement_ids: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    can_affect_projected_score: bool = False


class SkillToLearn(BaseModel):
    skill: str
    reason: str
    related_job_requirements: List[str] = Field(default_factory=list)
    priority: Literal["high", "medium", "low"] = "medium"
    citations: List[Citation] = Field(default_factory=list)
    suggested_learning_focus: str


class EvaluationIteration(BaseModel):
    iteration_number: int
    score_before: float
    projected_score_after: float
    improvement_delta: float
    safe_improvements: List[Suggestion] = Field(default_factory=list)
    skills_to_learn: List[SkillToLearn] = Field(default_factory=list)
    needs_confirmation_suggestions: List[Suggestion] = Field(default_factory=list)
    unsafe_rejected_suggestions: List[Suggestion] = Field(default_factory=list)
    stop_reason: Optional[StopReason] = None
    score_breakdown: ScoreBreakdown
    citations: List[Citation] = Field(default_factory=list)


class ATSKeywordMatch(BaseModel):
    keyword: str
    keyword_type: Literal["must_have", "preferred", "repeated", "responsibility", "domain", "soft_skill", "other"] = "other"
    match_status: Literal["exact", "normalized", "semantic", "adjacent", "weak", "missing"] = "missing"
    resume_evidence: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    score: float = 0.0
    recommendation: Optional[str] = None


class ATSSkillCoverage(BaseModel):
    skill: str
    required_importance: Literal["must_have", "preferred", "nice_to_have", "generic"] = "generic"
    coverage_status: Literal["covered", "partially_covered", "weak", "missing"] = "missing"
    evidence_backing: Literal["strong", "moderate", "weak", "none"] = "none"
    citations: List[Citation] = Field(default_factory=list)
    score: float = 0.0
    recommendation: str


class ATSPenalty(BaseModel):
    penalty_type: Literal["keyword_stuffing", "unsupported_claim", "missing_contact", "unparseable_formatting", "prompt_injection", "contradiction", "too_long", "generic_resume", "other"]
    severity: Literal["low", "medium", "high"] = "low"
    points_deducted: float = 0.0
    explanation: str
    recommendation: str
    citations: List[Citation] = Field(default_factory=list)


class ATSRecommendation(BaseModel):
    category: Literal["fix_immediately", "improve_wording", "add_if_true", "learn_before_applying", "formatting_improvement"]
    priority: Literal["high", "medium", "low"] = "medium"
    recommendation_text: str
    reason: str
    related_job_requirement: Optional[str] = None
    supporting_citations: List[Citation] = Field(default_factory=list)
    truth_status: Literal["safe_to_add", "add_only_if_true", "learn_first", "formatting_only"]


class ATSScoreBreakdown(BaseModel):
    parseability_score: float = 0.0
    section_structure_score: float = 0.0
    contact_extraction_score: float = 0.0
    keyword_alignment_score: float = 0.0
    required_skills_coverage_score: float = 0.0
    evidence_backing_score: float = 0.0
    formatting_safety_score: float = 0.0
    communication_quality_score: float = 0.0
    role_targeting_score: float = 0.0
    penalties: float = 0.0
    final_ats_score: float = 0.0
    ats_band: str = "Likely parsing or matching issues"
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[ATSRecommendation] = Field(default_factory=list)
    keyword_matches: List[ATSKeywordMatch] = Field(default_factory=list)
    skill_coverage: List[ATSSkillCoverage] = Field(default_factory=list)
    penalty_items: List[ATSPenalty] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)


class ATSRankingReadiness(BaseModel):
    ranking_readiness_score: float = 0.0
    ranking_readiness_band: str = "Likely to be filtered or overlooked"
    explanation: str = "Ranking readiness estimates how searchable and competitive this resume appears for the pasted job description based on ATS-style signals."
    top_factors_helping: List[str] = Field(default_factory=list)
    top_factors_hurting: List[str] = Field(default_factory=list)
    recommendations: List[ATSRecommendation] = Field(default_factory=list)


class OperationalLog(BaseModel):
    id: str
    run_id: str
    timestamp: datetime
    event_type: str
    message: str
    duration_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    level: Literal["info", "warning", "error"] = "info"


class AnalysisRun(BaseModel):
    run_id: str
    created_at: datetime
    resume_filename: str
    job_title: Optional[str] = None
    initial_score: Optional[float] = None
    projected_final_score: Optional[float] = None
    threshold: float = 8.0
    iterations_used: int = 0
    stop_reason: Optional[str] = None
    processing_time_ms: Optional[int] = None
    llm_calls_count: int = 0
    retrieval_calls_count: int = 0
    average_retrieval_similarity: float = 0.0
    citations_count: int = 0
    safe_suggestions_count: int = 0
    needs_confirmation_count: int = 0
    unsafe_rejected_count: int = 0
    prompt_injection_detected: bool = False
    status: Literal["completed", "failed", "running"] = "running"
    error_message: Optional[str] = None


class FinalReport(BaseModel):
    run_id: str
    initial_score: float
    projected_final_score: float
    threshold: float
    threshold_reached_projected: bool
    iterations: List[EvaluationIteration] = Field(default_factory=list)
    stop_reason: Optional[str] = None
    score_breakdown: ScoreBreakdown
    ats_score: float = 0.0
    ats_score_breakdown: ATSScoreBreakdown = Field(default_factory=ATSScoreBreakdown)
    ats_ranking_readiness: ATSRankingReadiness = Field(default_factory=ATSRankingReadiness)
    matched_requirements: List[RequirementMatch] = Field(default_factory=list)
    partial_matches: List[RequirementMatch] = Field(default_factory=list)
    missing_requirements: List[RequirementMatch] = Field(default_factory=list)
    safe_improvements_to_add: List[Suggestion] = Field(default_factory=list)
    skills_to_learn: List[SkillToLearn] = Field(default_factory=list)
    needs_confirmation_suggestions: List[Suggestion] = Field(default_factory=list)
    unsafe_rejected_suggestions: List[Suggestion] = Field(default_factory=list)
    interview_keywords: List[str] = Field(default_factory=list)
    interview_preparation_notes: List[str] = Field(default_factory=list)
    final_review: str
    citations: List[Citation] = Field(default_factory=list)
    retrieved_chunks_summary: Dict[str, Any] = Field(default_factory=dict)
    logs_summary: Dict[str, Any] = Field(default_factory=dict)
    config_used: Dict[str, Any] = Field(default_factory=dict)
