import type { EvaluationIteration } from "@/lib/types";
import { Badge } from "./Badge";
import { fmtScore } from "@/lib/formatting";

export function IterationTimeline({ iterations }: { iterations: EvaluationIteration[] }) {
  return (
    <div className="card p-4">
      <h3 className="font-semibold">Iteration Timeline</h3>
      <div className="mt-4 space-y-3">
        {iterations.length === 0 ? <p className="text-sm text-slate-500">No projected loop was needed.</p> : iterations.map((iteration) => (
          <div key={iteration.iteration_number} className="rounded-md border border-line p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-medium">Iteration {iteration.iteration_number}</div>
              {iteration.stop_reason ? <Badge>{iteration.stop_reason}</Badge> : null}
            </div>
            <div className="mt-2 grid gap-2 text-sm sm:grid-cols-3">
              <div>Before: <strong>{fmtScore(iteration.score_before)}</strong></div>
              <div>Projected: <strong>{fmtScore(iteration.projected_score_after)}</strong></div>
              <div>Delta: <strong>{fmtScore(iteration.improvement_delta)}</strong></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

