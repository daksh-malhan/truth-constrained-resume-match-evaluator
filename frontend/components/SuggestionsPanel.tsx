import type { Suggestion } from "@/lib/types";
import { Badge } from "./Badge";

export function SuggestionsPanel({ title, suggestions }: { title: string; suggestions: Suggestion[] }) {
  return (
    <div className="card p-4">
      <h3 className="font-semibold">{title}</h3>
      <div className="mt-3 space-y-3">
        {suggestions.length === 0 ? <p className="text-sm text-slate-500">No suggestions in this category.</p> : suggestions.map((suggestion) => (
          <div key={suggestion.id} className="rounded-md border border-line p-3">
            <div className="mb-2"><Badge>{suggestion.category}</Badge></div>
            <p className="text-sm font-medium">{suggestion.suggested_text}</p>
            <p className="mt-1 text-sm text-slate-600">{suggestion.reason}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

