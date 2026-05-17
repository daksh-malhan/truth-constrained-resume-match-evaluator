import type { ScoreBreakdown } from "@/lib/types";
import { fmtScore } from "@/lib/formatting";

const rows: [keyof ScoreBreakdown, string][] = [
  ["core_technical_skills_score", "Core technical skills"],
  ["experience_seniority_score", "Experience and seniority"],
  ["project_work_evidence_score", "Project/work evidence"],
  ["responsibility_match_score", "Responsibility match"],
  ["domain_context_score", "Domain/context"],
  ["education_certification_score", "Education/certifications"],
  ["ats_keyword_score", "ATS/keyword alignment"],
  ["resume_communication_score", "Resume communication"],
  ["interview_readiness_score", "Interview readiness"],
  ["risk_penalty", "Risk/truthfulness penalty"],
  ["final_score", "Final score"]
];

export function ScoreBreakdownTable({ breakdown }: { breakdown: ScoreBreakdown }) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-line px-4 py-3 font-semibold">Score Breakdown</div>
      <table className="w-full text-sm">
        <tbody>
          {rows.map(([key, label]) => (
            <tr key={key} className="border-b border-line last:border-0">
              <td className="px-4 py-2 text-slate-600">{label}</td>
              <td className="px-4 py-2 text-right font-medium">{fmtScore(Number(breakdown[key]))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

