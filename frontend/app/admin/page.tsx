"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AdminConfigForm } from "@/components/AdminConfigForm";
import { RunsTable } from "@/components/RunsTable";
import { LogsPanel } from "@/components/LogsPanel";
import { getAdminRuns } from "@/lib/api";
import type { RunRow } from "@/lib/types";

export default function AdminPage() {
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [metrics, setMetrics] = useState<Record<string, unknown>>({});
  const [error, setError] = useState("");

  useEffect(() => {
    getAdminRuns()
      .then((data) => {
        setRuns(data.runs);
        setMetrics(data.metrics);
        setError("");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load admin dashboard."));
  }, []);

  const recentLogs = runs.slice(0, 5).map((run) => ({
    id: run.run_id,
    event_type: run.status,
    level: run.status === "failed" ? "error" : "info",
    timestamp: run.created_at,
    message: `${run.resume_filename} scored ${run.projected_final_score ?? "pending"} with ${run.iterations_used} projected iterations.`
  }));

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-normal">Admin Dashboard</h1>
          <p className="mt-2 text-slate-600">Tune scoring, loop, RAG, and evidence parameters. Review run history and operational metrics.</p>
        </div>
        <Link className="btn btn-secondary" href="/">Analyze</Link>
      </header>
      <div className="mb-5 grid gap-4 md:grid-cols-4">
        {Object.entries(metrics).map(([key, value]) => (
          <div className="card p-4" key={key}>
            <div className="text-xs uppercase text-slate-500">{key.replaceAll("_", " ")}</div>
            <div className="mt-1 text-xl font-semibold">{String(value)}</div>
          </div>
        ))}
      </div>
      {error ? <div className="mb-5 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div> : null}
      <div className="space-y-5">
        <AdminConfigForm />
        <RunsTable runs={runs} />
        <LogsPanel logs={recentLogs} />
      </div>
    </main>
  );
}
