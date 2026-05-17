export function LogsPanel({ logs }: { logs: Array<Record<string, unknown>> }) {
  return (
    <div className="card overflow-hidden">
      <div className="border-b border-line px-4 py-3 font-semibold">Logs</div>
      <div className="max-h-[420px] overflow-auto">
        {logs.length === 0 ? <p className="p-4 text-sm text-slate-500">No logs.</p> : logs.map((log, index) => (
          <div key={String(log.id ?? index)} className="border-b border-line px-4 py-3 text-sm last:border-0">
            <div className="flex flex-wrap justify-between gap-2">
              <span className="font-medium">{String(log.event_type)}</span>
              <span className="text-xs text-slate-500">{String(log.level)} · {String(log.timestamp)}</span>
            </div>
            <p className="mt-1 text-slate-600">{String(log.message)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

