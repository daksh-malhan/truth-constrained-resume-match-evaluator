"use client";

import { useEffect, useMemo, useState } from "react";
import { RotateCcw, Save } from "lucide-react";
import { getAdminConfig, resetAdminConfig, saveAdminConfig } from "@/lib/api";

const fields = [
  "threshold_score", "max_iterations", "min_improvement", "enable_improvement_loop", "enable_truth_filter",
  "enable_rag_retrieval", "enable_prompt_injection_detection", "core_technical_skills_weight",
  "experience_seniority_weight", "project_work_evidence_weight", "responsibility_match_weight",
  "domain_context_weight", "education_certifications_weight", "ats_keyword_weight", "resume_communication_weight",
  "interview_readiness_weight", "max_risk_penalty", "chunk_size", "chunk_overlap", "top_k_resume_chunks",
  "top_k_job_chunks", "similarity_threshold", "embedding_model", "vector_store_provider", "reranking_enabled",
  "citation_required", "exact_match_score", "direct_match_score", "semantic_match_score", "adjacent_match_score",
  "weak_match_score", "missing_match_score", "must_have_weight", "repeated_weight", "main_responsibility_weight",
  "preferred_weight", "nice_to_have_weight", "generic_weight"
];

const atsFields = [
  "enable_ats_scoring", "enable_ats_ranking_readiness", "ats_parseability_weight", "ats_section_structure_weight",
  "ats_contact_extraction_weight", "ats_keyword_alignment_weight", "ats_required_skills_weight",
  "ats_evidence_backing_weight", "ats_formatting_safety_weight", "ats_communication_quality_weight",
  "ats_role_targeting_weight", "ats_max_penalty", "ats_exact_keyword_weight", "ats_normalized_keyword_weight",
  "ats_semantic_keyword_weight", "ats_adjacent_keyword_weight", "ats_weak_keyword_weight",
  "penalize_keyword_stuffing", "penalize_unparseable_formatting", "penalize_missing_contact_info",
  "penalize_unsupported_claims", "penalize_prompt_injection", "penalize_generic_resume",
  "check_tables", "check_columns", "check_images", "check_headers_footers", "check_weird_characters",
  "check_bullet_extraction"
];

export function AdminConfigForm() {
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [status, setStatus] = useState("");

  useEffect(() => {
    getAdminConfig()
      .then((data) => setConfig(data.config))
      .catch((err) => setStatus(err instanceof Error ? err.message : "Could not load config."));
  }, []);

  const total = useMemo(() => {
    return [
      "core_technical_skills_weight", "experience_seniority_weight", "project_work_evidence_weight",
      "responsibility_match_weight", "domain_context_weight", "education_certifications_weight",
      "ats_keyword_weight", "resume_communication_weight", "interview_readiness_weight"
    ].reduce((sum, key) => sum + Number(config[key] ?? 0), 0).toFixed(2);
  }, [config]);

  const atsTotal = useMemo(() => {
    return [
      "ats_parseability_weight", "ats_section_structure_weight", "ats_contact_extraction_weight",
      "ats_keyword_alignment_weight", "ats_required_skills_weight", "ats_evidence_backing_weight",
      "ats_formatting_safety_weight", "ats_communication_quality_weight", "ats_role_targeting_weight"
    ].reduce((sum, key) => sum + Number(config[key] ?? 0), 0).toFixed(2);
  }, [config]);

  function setValue(key: string, value: string | boolean) {
    const previous = config[key];
    const parsed = typeof value === "boolean" ? value : typeof previous === "number" ? Number(value) : value;
    setConfig({ ...config, [key]: parsed });
  }

  async function save() {
    try {
      const data = await saveAdminConfig(config);
      setConfig(data.config);
      setStatus("Settings saved.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not save settings.");
    }
  }

  async function reset() {
    try {
      const data = await resetAdminConfig();
      setConfig(data.config);
      setStatus("Settings reset.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not reset settings.");
    }
  }

  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Active Configuration</h2>
          <p className="text-sm text-slate-600">Match total before penalty: {total}</p>
          <p className="text-sm text-slate-600">ATS total before penalty: {atsTotal}</p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary" onClick={reset}><RotateCcw size={16} />Reset</button>
          <button className="btn btn-primary" onClick={save}><Save size={16} />Save</button>
        </div>
      </div>
      {status ? <p className="mt-3 text-sm text-emerald-700">{status}</p> : null}
      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {fields.map((field) => (
          <label key={field} className="grid gap-1">
            <span className="label">{field}</span>
            {typeof config[field] === "boolean" ? (
              <select className="input" value={String(config[field])} onChange={(event) => setValue(field, event.target.value === "true")}>
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            ) : field === "vector_store_provider" ? (
              <select className="input" value={String(config[field] ?? "faiss")} onChange={(event) => setValue(field, event.target.value)}>
                <option value="qdrant">qdrant</option>
                <option value="chroma">chroma</option>
                <option value="faiss">faiss</option>
              </select>
            ) : (
              <input className="input" value={String(config[field] ?? "")} onChange={(event) => setValue(field, event.target.value)} />
            )}
          </label>
        ))}
      </div>
      <div className="mt-8 border-t border-line pt-5">
        <h3 className="text-base font-semibold">ATS Simulation Controls</h3>
        <p className="mt-1 text-sm text-slate-600">Controls ATS-style readiness scoring, ranking readiness, keyword scoring, penalties, and formatting checks.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {atsFields.map((field) => (
            <label key={field} className="grid gap-1">
              <span className="label">{field}</span>
              {typeof config[field] === "boolean" ? (
                <select className="input" value={String(config[field])} onChange={(event) => setValue(field, event.target.value === "true")}>
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              ) : (
                <input className="input" value={String(config[field] ?? "")} onChange={(event) => setValue(field, event.target.value)} />
              )}
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
