import type { ReactNode } from "react";
export function GuideStep({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return <div className="border-t border-line py-8"><div className="flex items-baseline gap-3"><span className="font-mono text-sm text-accent">{String(n).padStart(2, "0")}</span><h2 className="font-display text-xl font-bold">{title}</h2></div><div className="mt-4 flex flex-col gap-4 pl-8">{children}</div></div>;
}
