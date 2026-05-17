import type { ATSRecommendation, ATSScoreBreakdown, ATSRankingReadiness } from "@/lib/types";
import { fmtScore } from "@/lib/formatting";
import { Badge } from "./Badge";

const scoreRows: [keyof ATSScoreBreakdown, string, number][] = [
  ["parseability_score", "Parseability", 15],
  ["section_structure_score", "Section Structure", 10],
  ["contact_extraction_score", "Contact Extraction", 8],
  ["keyword_alignment_score", "Keyword Alignment", 18],
  ["required_skills_coverage_score", "Required Skills Coverage", 18],
  ["evidence_backing_score", "Evidence Backing", 12],
  ["formatting_safety_score", "Formatting Safety", 8],
  ["communication_quality_score", "Communication Quality", 7],
  ["role_targeting_score", "Role Targeting", 4],
];

const categoryLabels: Record<ATSRecommendation["category"], string> = {
  fix_immediately: "Fix Immediately",
  improve_wording: "Improve Wording",
  add_if_true: "Add If True",
  learn_before_applying: "Learn Before Applying",
  formatting_improvement: "Formatting Improvements",
};

function RecommendationGroup({ title, items }: { title: string; items: ATSRecommendation[] }) {
  return (
    <div className="rounded-md border border-line p-3">
      <h4 className="font-medium">{title}</h4>
      {items.length === 0 ? <p className="mt-2 text-sm text-slate-500">No items.</p> : null}
      <div className="mt-2 space-y-3">
        {items.map((item, index) => (
          <div key={`${item.category}-${index}`} className="text-sm">
            <div className="flex flex-wrap gap-2">
              <Badge>{item.priority}</Badge>
              <Badge>{item.truth_status}</Badge>
            </div>
            <p className="mt-2 font-medium text-ink">{item.recommendation_text}</p>
            <p className="mt-1 text-slate-600">{item.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ATSReadinessPanel({ breakdown, ranking }: { breakdown: ATSScoreBreakdown; ranking: ATSRankingReadiness }) {
  // Keep the report scannable by grouping actions by the same categories returned by
  // the backend truth-constrained ATS service.
  const grouped = breakdown.recommendations.reduce<Record<string, ATSRecommendation[]>>((acc, item) => {
    acc[item.category] = [...(acc[item.category] || []), item];
    return acc;
  }, {});
  const missingKeywords = breakdown.keyword_matches.filter((item) => item.match_status === "missing");
  const matchedKeywords = breakdown.keyword_matches.filter((item) => item.match_status !== "missing");

  return (
    <section className="space-y-4">
      <div className="card p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">ATS Readiness</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
              ATS-style simulation based only on the original resume PDF and pasted job description. This does not guarantee ATS passage, selection, or interviews.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge>{breakdown.ats_band}</Badge>
            <Badge>{ranking.ranking_readiness_band}</Badge>
          </div>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-md border border-line p-4">
            <div className="text-sm font-medium text-slate-600">ATS Readiness Score</div>
            <div className="mt-2 text-4xl font-semibold">{fmtScore(breakdown.final_ats_score)} / 100</div>
            <div className="mt-2 text-sm text-slate-500">{breakdown.ats_band}</div>
          </div>
          <div className="rounded-md border border-line p-4">
            <div className="text-sm font-medium text-slate-600">Ranking Readiness</div>
            <div className="mt-2 text-4xl font-semibold">{fmtScore(ranking.ranking_readiness_score)} / 100</div>
            <div className="mt-2 text-sm text-slate-500">{ranking.ranking_readiness_band}</div>
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-slate-700">{ranking.explanation}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card overflow-hidden">
          <div className="border-b border-line px-4 py-3 font-semibold">ATS Score Breakdown</div>
          <table className="w-full text-sm">
            <tbody>
              {scoreRows.map(([key, label, max]) => (
                <tr key={key} className="border-t border-line first:border-t-0">
                  <td className="px-4 py-2">{label}</td>
                  <td className="px-4 py-2 text-right">{fmtScore(Number(breakdown[key]))} / {max}</td>
                </tr>
              ))}
              <tr className="border-t border-line text-rose-700">
                <td className="px-4 py-2">Penalties</td>
                <td className="px-4 py-2 text-right">-{fmtScore(breakdown.penalties)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="card p-4">
          <h3 className="font-semibold">Ranking Factors</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div>
              <div className="text-sm font-medium text-emerald-700">Helping</div>
              <ul className="mt-2 space-y-1 text-sm text-slate-700">{ranking.top_factors_helping.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <div>
              <div className="text-sm font-medium text-rose-700">Hurting</div>
              <ul className="mt-2 space-y-1 text-sm text-slate-700">{ranking.top_factors_hurting.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
        </div>
      </div>

      {breakdown.warnings.length ? (
        <div className="card p-4">
          <h3 className="font-semibold">ATS Warnings</h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">{breakdown.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
        </div>
      ) : null}

      <div className="card overflow-hidden">
        <div className="border-b border-line px-4 py-3 font-semibold">ATS Keywords</div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[780px] text-sm">
            <thead className="bg-panel text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Keyword</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right">Score</th>
                <th className="px-4 py-2">Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {[...matchedKeywords, ...missingKeywords].slice(0, 16).map((item, index) => (
                <tr key={`${item.keyword}-${item.match_status}-${index}`} className="border-t border-line align-top">
                  <td className="px-4 py-3">{item.keyword}</td>
                  <td className="px-4 py-3">{item.keyword_type}</td>
                  <td className="px-4 py-3"><Badge>{item.match_status}</Badge></td>
                  <td className="px-4 py-3 text-right">{fmtScore(item.score)}</td>
                  <td className="max-w-[360px] px-4 py-3 text-slate-600">{item.recommendation || "Covered by source evidence."}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="border-b border-line px-4 py-3 font-semibold">Required Skill Coverage</div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="bg-panel text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Skill</th>
                <th className="px-4 py-2">Importance</th>
                <th className="px-4 py-2">Coverage</th>
                <th className="px-4 py-2">Evidence</th>
                <th className="px-4 py-2">Guidance</th>
              </tr>
            </thead>
            <tbody>
              {breakdown.skill_coverage.slice(0, 16).map((item) => (
                <tr key={item.skill} className="border-t border-line align-top">
                  <td className="px-4 py-3">{item.skill}</td>
                  <td className="px-4 py-3">{item.required_importance}</td>
                  <td className="px-4 py-3"><Badge>{item.coverage_status}</Badge></td>
                  <td className="px-4 py-3"><Badge>{item.evidence_backing}</Badge></td>
                  <td className="max-w-[360px] px-4 py-3 text-slate-600">{item.recommendation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {breakdown.penalty_items.length ? (
        <div className="card overflow-hidden">
          <div className="border-b border-line px-4 py-3 font-semibold">ATS Penalties</div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="bg-panel text-left text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Severity</th>
                  <th className="px-4 py-2 text-right">Points</th>
                  <th className="px-4 py-2">Explanation</th>
                </tr>
              </thead>
              <tbody>
                {breakdown.penalty_items.map((item) => (
                  <tr key={item.penalty_type} className="border-t border-line align-top">
                    <td className="px-4 py-3">{item.penalty_type}</td>
                    <td className="px-4 py-3"><Badge>{item.severity}</Badge></td>
                    <td className="px-4 py-3 text-right">-{fmtScore(item.points_deducted)}</td>
                    <td className="max-w-[420px] px-4 py-3 text-slate-600">{item.explanation} {item.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {Object.entries(categoryLabels).map(([key, title]) => (
          <RecommendationGroup key={key} title={title} items={grouped[key] || []} />
        ))}
      </div>
    </section>
  );
}
