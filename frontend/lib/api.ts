import type { CoachResponse, FinalReport } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function coachResume(body: {
  resume: string;
  job_description: string;
  target_role: string;
}): Promise<CoachResponse> {
  const res = await fetch(`${API_BASE}/coach`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    const detail = errBody?.detail;
    throw new Error(detail?.error ?? (typeof detail === "string" ? detail : "Coaching failed"));
  }
  return res.json();
}

export async function analyzeResume(form: FormData): Promise<FinalReport> {
  const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body?.detail;
    throw new Error(detail?.error ?? (typeof detail === "string" ? detail : JSON.stringify(detail || "Analysis failed")));
  }
  return res.json();
}

export async function fetchRun(runId: string): Promise<FinalReport> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Run not found");
  return res.json();
}

export async function getAdminConfig() {
  const res = await fetch(`${API_BASE}/api/admin/config`, { cache: "no-store" });
  if (!res.ok) throw new Error("Could not load config");
  return res.json();
}

export async function saveAdminConfig(config: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/api/admin/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config)
  });
  if (!res.ok) throw new Error("Could not save config");
  return res.json();
}

export async function resetAdminConfig() {
  const res = await fetch(`${API_BASE}/api/admin/config/reset`, { method: "POST" });
  if (!res.ok) throw new Error("Could not reset config");
  return res.json();
}

export async function getAdminRuns() {
  const res = await fetch(`${API_BASE}/api/admin/runs`, { cache: "no-store" });
  if (!res.ok) throw new Error("Could not load runs");
  return res.json();
}

export async function getRunLogs(runId: string) {
  const res = await fetch(`${API_BASE}/api/admin/runs/${runId}/logs`, { cache: "no-store" });
  if (!res.ok) throw new Error("Could not load logs");
  return res.json();
}

export async function getRunChunks(runId: string) {
  const res = await fetch(`${API_BASE}/api/admin/runs/${runId}/chunks`, { cache: "no-store" });
  if (!res.ok) throw new Error("Could not load chunks");
  return res.json();
}
