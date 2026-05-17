import Link from "next/link";
import type { RunRow } from "@/lib/types";
import { fmtScore } from "@/lib/formatting";
import { Badge } from "./Badge";

export function RunsTable({ runs }: { runs: RunRow[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-line px-4 py-3 font-semibold">Recent Runs</div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[960px] text-sm">
          <thead className="bg-panel text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Run</th>
              <th className="px-4 py-2">Resume</th>
              <th className="px-4 py-2">Initial</th>
              <th className="px-4 py-2">Projected</th>
              <th className="px-4 py-2">Threshold</th>
              <th className="px-4 py-2">Iterations</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Stop</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.run_id} className="border-t border-line">
                <td className="px-4 py-3"><Link className="text-signal underline" href={`/runs/${run.run_id}`}>{run.run_id}</Link></td>
                <td className="px-4 py-3">{run.resume_filename}</td>
                <td className="px-4 py-3">{fmtScore(run.initial_score)}</td>
                <td className="px-4 py-3">{fmtScore(run.projected_final_score)}</td>
                <td className="px-4 py-3">{fmtScore(run.threshold)}</td>
                <td className="px-4 py-3">{run.iterations_used}</td>
                <td className="px-4 py-3"><Badge>{run.status}</Badge></td>
                <td className="px-4 py-3">{run.stop_reason ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

