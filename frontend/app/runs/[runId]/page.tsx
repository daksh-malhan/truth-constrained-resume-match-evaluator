"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchRun, getRunChunks, getRunLogs } from "@/lib/api";
import type { FinalReport } from "@/lib/types";
import { ScoreCard } from "@/components/ScoreCard";
import { ScoreBreakdownTable } from "@/components/ScoreBreakdownTable";
import { IterationTimeline } from "@/components/IterationTimeline";
import { RequirementsTable } from "@/components/RequirementsTable";
import { CitationsPanel } from "@/components/CitationsPanel";
import { LogsPanel } from "@/components/LogsPanel";
import { RetrievedChunksPanel } from "@/components/RetrievedChunksPanel";
import { ATSReadinessPanel } from "@/components/ATSReadinessPanel";

export default function RunDetailsPage() {
  const params = useParams<{ runId: string }>();
  const [report, setReport] = useState<FinalReport | null>(null);
  const [logs, setLogs] = useState<Array<Record<string, unknown>>>([]);
  const [chunks, setChunks] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!params.runId) return;
    Promise.all([fetchRun(params.runId), getRunLogs(params.runId), getRunChunks(params.runId)])
      .then(([reportData, logsData, chunksData]) => {
        setReport(reportData);
        setLogs(logsData.logs);
        setChunks(chunksData.chunks);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load run"));
  }, [params.runId]);

  if (error) return <main className="mx-auto max-w-5xl px-4 py-8"><div className="card p-5 text-rose-700">{error}</div></main>;
  if (!report) return <main className="mx-auto max-w-5xl px-4 py-8"><div className="card p-5">Loading run details...</div></main>;

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-normal">Run Details</h1>
          <p className="mt-2 text-slate-600">{report.run_id}</p>
        </div>
        <div className="flex gap-2">
          <Link className="btn btn-secondary" href="/">Analyze</Link>
          <Link className="btn btn-secondary" href="/admin">Admin</Link>
        </div>
      </header>
      <div className="space-y-5">
        <div className="grid gap-4 md:grid-cols-3">
          <ScoreCard label="Initial Score" score={report.initial_score} />
          <ScoreCard label="Projected Final Score" score={report.projected_final_score} />
          <ScoreCard label="ATS Readiness" score={report.ats_score} caption={`${report.ats_score_breakdown.ats_band} / 100`} />
          <ScoreCard label="Ranking Readiness" score={report.ats_ranking_readiness.ranking_readiness_score} caption={`${report.ats_ranking_readiness.ranking_readiness_band} / 100`} />
          <ScoreCard label="Threshold" score={report.threshold} caption={report.stop_reason} />
        </div>
        <div className="card p-4 text-sm leading-6 text-slate-700">{report.final_review}</div>
        <ScoreBreakdownTable breakdown={report.score_breakdown} />
        <ATSReadinessPanel breakdown={report.ats_score_breakdown} ranking={report.ats_ranking_readiness} />
        <IterationTimeline iterations={report.iterations} />
        <RequirementsTable title="Matched Requirements" rows={report.matched_requirements} />
        <RequirementsTable title="Partial Matches" rows={report.partial_matches} />
        <RequirementsTable title="Missing Requirements" rows={report.missing_requirements} />
        <RetrievedChunksPanel chunks={chunks} />
        <CitationsPanel citations={report.citations} />
        <LogsPanel logs={logs} />
        <div className="card p-4">
          <h3 className="font-semibold">Config Used</h3>
          <pre className="mt-3 max-h-[420px] overflow-auto rounded-md bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(report.config_used, null, 2)}</pre>
        </div>
      </div>
    </main>
  );
}
