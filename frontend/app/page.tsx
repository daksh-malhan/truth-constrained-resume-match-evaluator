"use client";

import Link from "next/link";
import { useState } from "react";
import { UploadForm } from "@/components/UploadForm";
import { ScoreCard } from "@/components/ScoreCard";
import { ScoreBreakdownTable } from "@/components/ScoreBreakdownTable";
import { IterationTimeline } from "@/components/IterationTimeline";
import { RequirementsTable } from "@/components/RequirementsTable";
import { SuggestionsPanel } from "@/components/SuggestionsPanel";
import { SkillsToLearnPanel } from "@/components/SkillsToLearnPanel";
import { CitationsPanel } from "@/components/CitationsPanel";
import { Badge } from "@/components/Badge";
import { ATSReadinessPanel } from "@/components/ATSReadinessPanel";
import type { FinalReport } from "@/lib/types";

export default function HomePage() {
  const [report, setReport] = useState<FinalReport | null>(null);
  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-normal">Truth-Constrained Resume Match Evaluator</h1>
          <p className="mt-2 max-w-3xl text-slate-600">Upload a resume PDF, paste a job description, and get citation-backed RAG scoring with projected improvement recommendations that do not fabricate resume content.</p>
        </div>
        <Link className="btn btn-secondary" href="/admin">Admin</Link>
      </header>

      <UploadForm onResult={setReport} />

      {report ? (
        <section className="mt-8 space-y-5">
          <div className="flex flex-wrap items-center gap-3">
            <Badge>{report.threshold_reached_projected ? "projected threshold reached" : "threshold not safely reachable"}</Badge>
            {report.stop_reason ? <Badge>{report.stop_reason}</Badge> : null}
            <Link className="text-sm font-medium text-signal underline" href={`/runs/${report.run_id}`}>Open run details</Link>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <ScoreCard label="Initial Score" score={report.initial_score} caption={report.score_breakdown.score_band} />
            <ScoreCard label="Projected Final Score" score={report.projected_final_score} caption={`Threshold ${report.threshold}`} />
            <ScoreCard label="ATS Readiness" score={report.ats_score} caption={`${report.ats_score_breakdown.ats_band} / 100`} />
            <ScoreCard label="Ranking Readiness" score={report.ats_ranking_readiness.ranking_readiness_score} caption={`${report.ats_ranking_readiness.ranking_readiness_band} / 100`} />
            <div className="card p-5">
              <div className="text-sm font-medium text-slate-600">Final Review</div>
              <p className="mt-2 text-sm leading-6 text-slate-700">{report.final_review}</p>
            </div>
          </div>
          <ScoreBreakdownTable breakdown={report.score_breakdown} />
          <ATSReadinessPanel breakdown={report.ats_score_breakdown} ranking={report.ats_ranking_readiness} />
          <IterationTimeline iterations={report.iterations} />
          <RequirementsTable title="Matched Requirements" rows={report.matched_requirements} />
          <RequirementsTable title="Partial Matches" rows={report.partial_matches} />
          <RequirementsTable title="Missing Requirements" rows={report.missing_requirements} />
          <div className="grid gap-4 lg:grid-cols-2">
            <SuggestionsPanel title="Suggested Improvements" suggestions={report.safe_improvements_to_add} />
            <SkillsToLearnPanel skills={report.skills_to_learn} />
            <SuggestionsPanel title="Needs User Confirmation" suggestions={report.needs_confirmation_suggestions} />
            <SuggestionsPanel title="Unsupported Claims Rejected" suggestions={report.unsafe_rejected_suggestions} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="card p-4">
              <h3 className="font-semibold">Interview Keywords</h3>
              <div className="mt-3 flex flex-wrap gap-2">{report.interview_keywords.map((keyword) => <Badge key={keyword}>{keyword}</Badge>)}</div>
            </div>
            <div className="card p-4">
              <h3 className="font-semibold">Interview Preparation Notes</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-700">{report.interview_preparation_notes.map((note, index) => <li key={index}>{note}</li>)}</ul>
            </div>
          </div>
          <CitationsPanel citations={report.citations} />
        </section>
      ) : null}
    </main>
  );
}
