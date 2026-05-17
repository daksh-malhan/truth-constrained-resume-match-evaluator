export function fmtScore(value?: number) {
  return typeof value === "number" ? value.toFixed(2) : "—";
}

export function badgeClass(status: string) {
  const normalized = status.toLowerCase();
  if (normalized.includes("strong") || normalized.includes("safe") || normalized.includes("ready") || normalized.includes("reached") || normalized.includes("covered") || normalized === "high") return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (normalized.includes("partial") || normalized.includes("confirmation") || normalized.includes("mostly") || normalized.includes("moderate") || normalized === "medium") return "bg-amber-50 text-amber-700 border-amber-200";
  if (normalized.includes("weak") || normalized.includes("optimization") || normalized.includes("adjacent") || normalized === "low") return "bg-orange-50 text-orange-700 border-orange-200";
  if (normalized.includes("unsafe") || normalized.includes("missing") || normalized.includes("risk") || normalized.includes("not") || normalized.includes("overlooked")) return "bg-rose-50 text-rose-700 border-rose-200";
  return "bg-slate-50 text-slate-700 border-slate-200";
}
