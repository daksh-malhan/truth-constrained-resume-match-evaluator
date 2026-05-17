import type { Citation } from "@/lib/types";

export function CitationsPanel({ citations }: { citations: Citation[] }) {
  const trimmed = citations.slice(0, 30);
  return (
    <div className="card p-4">
      <h3 className="font-semibold">Citations</h3>
      <div className="mt-3 space-y-2">
        {trimmed.length === 0 ? <p className="text-sm text-slate-500">No citations available.</p> : trimmed.map((citation, index) => (
          <div key={`${citation.chunk_id}-${index}`} className="rounded-md border border-line bg-panel p-3 text-sm">
            <div className="font-medium">{citation.source_type.replace("_", " ")} · {citation.source_location}</div>
            <div className="mt-1 text-slate-600">{citation.quote}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

