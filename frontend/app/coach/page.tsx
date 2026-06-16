"use client";

import Link from "next/link";
import { useState } from "react";
import { coachResume } from "@/lib/api";
import type { CoachResponse } from "@/lib/types";

const SAMPLE_RESUME = `PROJECTS
Built a FastAPI service in Python with pytest coverage and a SQLite backend.
Created a Dockerized REST API that processes JSON records and logs progress.

SKILLS
Python, FastAPI, Docker, SQL, Git`;

const SAMPLE_JOB = `Backend Engineer Intern
Required: strong Python and REST API development. Must have Docker and SQL.
Preferred: Kubernetes orchestration and AWS deployment.`;

export default function CoachPage() {
  const [resume, setResume] = useState(SAMPLE_RESUME);
  const [jobDescription, setJobDescription] = useState(SAMPLE_JOB);
  const [targetRole, setTargetRole] = useState("Backend Engineer Intern");
  const [result, setResult] = useState<CoachResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await coachResume({ resume, job_description: jobDescription, target_role: targetRole });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Coaching failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-normal">Resume Coach Agent</h1>
          <p className="mt-2 text-slate-600">
            A tool-calling agent (LangGraph + local Ollama) coaches your resume toward a target job — and never asserts a claim your resume doesn&apos;t support.
          </p>
        </div>
        <Link className="btn btn-secondary" href="/">Analyze</Link>
      </header>

      <form onSubmit={onSubmit} className="card space-y-4 p-5">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Resume (plain text)</span>
            <textarea className="mt-1 h-56 w-full rounded-md border border-slate-300 p-2 font-mono text-xs" value={resume} onChange={(e) => setResume(e.target.value)} />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Job description</span>
            <textarea className="mt-1 h-56 w-full rounded-md border border-slate-300 p-2 font-mono text-xs" value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} />
          </label>
        </div>
        <label className="block max-w-md">
          <span className="text-sm font-medium text-slate-700">Target role</span>
          <input className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm" value={targetRole} onChange={(e) => setTargetRole(e.target.value)} />
        </label>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Coaching… (local LLM)" : "Coach my resume"}
        </button>
      </form>

      {error ? <div className="mt-5 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div> : null}

      {result ? (
        <section className="mt-6 space-y-5">
          <div className="card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs uppercase text-slate-500">Match score</div>
                <div className="text-3xl font-semibold">{result.initial_score ?? "—"}<span className="text-base text-slate-400">/10</span></div>
                <div className="text-sm text-slate-500">{result.score_breakdown?.score_band}</div>
              </div>
              <div className="text-right text-xs text-slate-500">
                <div>{result.iterations} iterations · stop: {result.stop_reason}</div>
                <div>{result.llm_provider} · {result.model}</div>
              </div>
            </div>
            {result.final_summary ? <p className="mt-3 text-sm text-slate-700">{result.final_summary}</p> : null}
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <div className="card p-5">
              <h2 className="mb-2 text-lg font-semibold">Missing requirements</h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                {result.gaps?.missing_requirements.length ? result.gaps.missing_requirements.map((m, i) => <li key={i}>{m}</li>) : <li className="list-none text-slate-400">None detected</li>}
              </ul>
              <h3 className="mb-1 mt-4 text-sm font-semibold text-slate-600">Buried keywords</h3>
              <div className="flex flex-wrap gap-1">
                {result.gaps?.buried_keywords.length ? result.gaps.buried_keywords.map((k, i) => <span key={i} className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">{k}</span>) : <span className="text-xs text-slate-400">None</span>}
              </div>
            </div>

            <div className="card p-5">
              <h2 className="mb-2 text-lg font-semibold">Bullet rewrites</h2>
              {result.bullet_rewrites.length ? (
                <ul className="space-y-3">
                  {result.bullet_rewrites.map((r, i) => (
                    <li key={i} className="rounded-md border border-slate-200 p-3 text-sm">
                      <div className="font-medium text-slate-800">{r.rewrite}</div>
                      <div className="mt-1 text-xs text-slate-500">{r.rationale}</div>
                      {r.flagged ? (
                        <div className="mt-2 rounded bg-rose-50 px-2 py-1 text-xs text-rose-700">
                          ⚠ Flagged — not asserted: {r.unsupported_claims.join("; ")}
                        </div>
                      ) : (
                        <div className="mt-2 text-xs text-emerald-700">✓ Truth-supported</div>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">No rewrites suggested.</p>
              )}
            </div>
          </div>

          {result.truth_constraint_notes.length ? (
            <div className="card border-rose-200 p-5">
              <h2 className="mb-2 text-lg font-semibold text-rose-700">Truth-constraint notes</h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-rose-700">
                {result.truth_constraint_notes.map((n, i) => <li key={i}>{n}</li>)}
              </ul>
            </div>
          ) : null}

          <div className="card p-5">
            <h2 className="mb-3 text-lg font-semibold">Tool-call trace</h2>
            <ol className="space-y-2">
              {result.tool_call_trace.map((t, i) => (
                <li key={i} className="rounded-md bg-slate-50 p-2 text-xs">
                  <span className="font-mono font-semibold">#{t.step} {t.tool}</span>
                  <span className="text-slate-500"> · {t.duration_ms} ms{t.error ? ` · error: ${t.error}` : ""}</span>
                  <pre className="mt-1 overflow-x-auto whitespace-pre-wrap text-[11px] text-slate-600">{JSON.stringify(t.args)}</pre>
                </li>
              ))}
              {result.tool_call_trace.length === 0 ? <li className="text-xs text-slate-400">No tool calls recorded.</li> : null}
            </ol>
          </div>
        </section>
      ) : null}
    </main>
  );
}
