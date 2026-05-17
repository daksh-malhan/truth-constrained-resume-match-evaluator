import { fmtScore } from "@/lib/formatting";

export function ScoreCard({ label, score, caption }: { label: string; score: number; caption?: string }) {
  return (
    <div className="card p-5">
      <div className="text-sm font-medium text-slate-600">{label}</div>
      <div className="mt-2 text-4xl font-semibold tracking-normal text-ink">{fmtScore(score)}</div>
      {caption ? <div className="mt-2 text-sm text-slate-500">{caption}</div> : null}
    </div>
  );
}

