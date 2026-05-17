"use client";

import { useState } from "react";
import { FileText, Loader2, Search } from "lucide-react";
import { analyzeResume } from "@/lib/api";
import type { FinalReport } from "@/lib/types";

export function UploadForm({ onResult }: { onResult: (report: FinalReport) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [jd, setJd] = useState("");
  const [threshold, setThreshold] = useState("8.0");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setError("");
    if (!file) {
      setError("Upload a resume PDF first.");
      return;
    }
    setLoading(true);
    try {
      const form = new FormData();
      form.set("resume_pdf", file);
      form.set("job_description_text", jd);
      form.set("threshold", threshold);
      const report = await analyzeResume(form);
      onResult(report);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card p-5">
      <div className="grid gap-4">
        <label className="grid gap-2">
          <span className="label">Resume PDF</span>
          <input className="input" type="file" accept="application/pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        </label>
        <label className="grid gap-2">
          <span className="label">Job Description</span>
          <textarea className="input min-h-[220px]" value={jd} onChange={(event) => setJd(event.target.value)} placeholder="Paste the job description, requirements, and responsibilities here." />
        </label>
        <label className="grid gap-2 sm:max-w-[220px]">
          <span className="label">Target Threshold</span>
          <input className="input" type="number" min="0" max="10" step="0.1" value={threshold} onChange={(event) => setThreshold(event.target.value)} />
        </label>
        {error ? <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div> : null}
        <button className="btn btn-primary w-fit" type="button" disabled={loading || !jd.trim()} onClick={submit}>
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
          {loading ? "Analyzing with RAG and truth checks" : "Analyze Match"}
        </button>
      </div>
    </div>
  );
}

