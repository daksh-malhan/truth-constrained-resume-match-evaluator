export type Citation = {
  source_type: "resume" | "job_description";
  source_location: string;
  quote: string;
  page_number?: number;
  section_name?: string;
  paragraph_index?: number;
  chunk_id?: string;
  similarity_score?: number;
};

export type RequirementMatch = {
  requirement_id: string;
  requirement_text: string;
  match_type: string;
  evidence_strength: number;
  confidence: number;
  weighted_score: number;
  status: "strong_match" | "partial_match" | "weak_match" | "missing";
  explanation: string;
  citations: Citation[];
};

export type ScoreBreakdown = {
  core_technical_skills_score: number;
  experience_seniority_score: number;
  project_work_evidence_score: number;
  responsibility_match_score: number;
  domain_context_score: number;
  education_certification_score: number;
  ats_keyword_score: number;
  resume_communication_score: number;
  interview_readiness_score: number;
  risk_penalty: number;
  final_score: number;
  score_band: string;
};

export type Suggestion = {
  id: string;
  original_text?: string;
  suggested_text: string;
  category: "SAFE_REWRITE" | "NEEDS_USER_CONFIRMATION" | "UNSAFE_OR_FABRICATED";
  reason: string;
  citations: Citation[];
  can_affect_projected_score: boolean;
};

export type SkillToLearn = {
  skill: string;
  reason: string;
  priority: "high" | "medium" | "low";
  suggested_learning_focus: string;
  citations: Citation[];
};

export type EvaluationIteration = {
  iteration_number: number;
  score_before: number;
  projected_score_after: number;
  improvement_delta: number;
  safe_improvements: Suggestion[];
  skills_to_learn: SkillToLearn[];
  needs_confirmation_suggestions: Suggestion[];
  unsafe_rejected_suggestions: Suggestion[];
  stop_reason?: string;
  score_breakdown: ScoreBreakdown;
  citations: Citation[];
};

export type ATSRecommendation = {
  category: "fix_immediately" | "improve_wording" | "add_if_true" | "learn_before_applying" | "formatting_improvement";
  priority: "high" | "medium" | "low";
  recommendation_text: string;
  reason: string;
  related_job_requirement?: string;
  supporting_citations: Citation[];
  truth_status: "safe_to_add" | "add_only_if_true" | "learn_first" | "formatting_only";
};

export type ATSKeywordMatch = {
  keyword: string;
  keyword_type: string;
  match_status: "exact" | "normalized" | "semantic" | "adjacent" | "weak" | "missing";
  resume_evidence: string[];
  citations: Citation[];
  score: number;
  recommendation?: string;
};

export type ATSSkillCoverage = {
  skill: string;
  required_importance: string;
  coverage_status: "covered" | "partially_covered" | "weak" | "missing";
  evidence_backing: "strong" | "moderate" | "weak" | "none";
  citations: Citation[];
  score: number;
  recommendation: string;
};

export type ATSPenalty = {
  penalty_type: string;
  severity: "low" | "medium" | "high";
  points_deducted: number;
  explanation: string;
  recommendation: string;
  citations: Citation[];
};

export type ATSScoreBreakdown = {
  parseability_score: number;
  section_structure_score: number;
  contact_extraction_score: number;
  keyword_alignment_score: number;
  required_skills_coverage_score: number;
  evidence_backing_score: number;
  formatting_safety_score: number;
  communication_quality_score: number;
  role_targeting_score: number;
  penalties: number;
  final_ats_score: number;
  ats_band: string;
  warnings: string[];
  recommendations: ATSRecommendation[];
  keyword_matches: ATSKeywordMatch[];
  skill_coverage: ATSSkillCoverage[];
  penalty_items: ATSPenalty[];
  citations: Citation[];
};

export type ATSRankingReadiness = {
  ranking_readiness_score: number;
  ranking_readiness_band: string;
  explanation: string;
  top_factors_helping: string[];
  top_factors_hurting: string[];
  recommendations: ATSRecommendation[];
};

export type FinalReport = {
  run_id: string;
  initial_score: number;
  projected_final_score: number;
  threshold: number;
  threshold_reached_projected: boolean;
  iterations: EvaluationIteration[];
  stop_reason?: string;
  score_breakdown: ScoreBreakdown;
  ats_score: number;
  ats_score_breakdown: ATSScoreBreakdown;
  ats_ranking_readiness: ATSRankingReadiness;
  matched_requirements: RequirementMatch[];
  partial_matches: RequirementMatch[];
  missing_requirements: RequirementMatch[];
  safe_improvements_to_add: Suggestion[];
  skills_to_learn: SkillToLearn[];
  needs_confirmation_suggestions: Suggestion[];
  unsafe_rejected_suggestions: Suggestion[];
  interview_keywords: string[];
  interview_preparation_notes: string[];
  final_review: string;
  citations: Citation[];
  retrieved_chunks_summary: Record<string, unknown>;
  logs_summary: Record<string, unknown>;
  config_used: Record<string, unknown>;
};

export type RunRow = {
  run_id: string;
  created_at: string;
  resume_filename: string;
  job_title?: string;
  initial_score?: number;
  projected_final_score?: number;
  threshold: number;
  iterations_used: number;
  stop_reason?: string;
  processing_time_ms?: number;
  retrieval_calls_count: number;
  citations_count: number;
  safe_suggestions_count: number;
  needs_confirmation_count: number;
  unsafe_rejected_count: number;
  prompt_injection_detected: number;
  status: string;
  error_message?: string;
};
