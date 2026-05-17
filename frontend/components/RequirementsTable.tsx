import type { RequirementMatch } from "@/lib/types";
import { Badge } from "./Badge";
import { fmtScore } from "@/lib/formatting";

export function RequirementsTable({ title, rows }: { title: string; rows: RequirementMatch[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-line px-4 py-3 font-semibold">{title}</div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead className="bg-panel text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Requirement</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Match</th>
              <th className="px-4 py-2 text-right">Strength</th>
              <th className="px-4 py-2">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td className="px-4 py-5 text-slate-500" colSpan={5}>No rows.</td></tr>
            ) : rows.map((row) => (
              <tr key={row.requirement_id} className="border-t border-line align-top">
                <td className="max-w-[380px] px-4 py-3">{row.requirement_text}</td>
                <td className="px-4 py-3"><Badge>{row.status}</Badge></td>
                <td className="px-4 py-3">{row.match_type}</td>
                <td className="px-4 py-3 text-right">{fmtScore(row.evidence_strength)}</td>
                <td className="max-w-[320px] px-4 py-3 text-slate-600">{row.explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

