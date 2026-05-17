import { badgeClass } from "@/lib/formatting";

export function Badge({ children }: { children: string }) {
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${badgeClass(children)}`}>{children.replaceAll("_", " ")}</span>;
}

