import type { SkillToLearn } from "@/lib/types";
import { Badge } from "./Badge";

export function SkillsToLearnPanel({ skills }: { skills: SkillToLearn[] }) {
  return (
    <div className="card p-4">
      <h3 className="font-semibold">Skills To Learn</h3>
      <div className="mt-3 space-y-3">
        {skills.length === 0 ? <p className="text-sm text-slate-500">No missing skills identified.</p> : skills.map((skill, index) => (
          <div key={`${skill.skill}-${index}`} className="rounded-md border border-line p-3">
            <div className="mb-2"><Badge>{skill.priority}</Badge></div>
            <p className="text-sm font-medium">{skill.skill}</p>
            <p className="mt-1 text-sm text-slate-600">{skill.reason}</p>
            <p className="mt-1 text-sm text-slate-600">{skill.suggested_learning_focus}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

