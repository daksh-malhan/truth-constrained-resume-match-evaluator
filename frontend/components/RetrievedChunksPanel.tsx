export function RetrievedChunksPanel({ chunks }: { chunks: Array<Record<string, unknown>> }) {
  return (
    <div className="card p-4">
      <h3 className="font-semibold">Retrieved / Indexed Chunks</h3>
      <div className="mt-3 space-y-2">
        {chunks.slice(0, 50).map((chunk) => (
          <div key={String(chunk.id)} className="rounded-md border border-line bg-panel p-3 text-sm">
            <div className="font-medium">{String(chunk.source_type)} · {String(chunk.section_name ?? chunk.paragraph_index ?? "")}</div>
            <p className="mt-1 text-slate-600">{String(chunk.text).slice(0, 400)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

