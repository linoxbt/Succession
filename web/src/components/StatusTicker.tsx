import { useEffect, useState } from "react";
import { motion } from "framer-motion";

type State = "loading" | "ok" | "error";
type Chain = { mode?: string; chain_id?: number; deployment?: { listing_contract?: string; arbiter?: string } };

export function StatusTicker() {
  const [state, setState] = useState<State>("loading");
  const [chain, setChain] = useState<Chain | null>(null);
  useEffect(() => {
    Promise.all([
      fetch("/api/health").then((r) => { if (!r.ok) throw new Error(); return r.json(); }),
      fetch("/api/chain").then((r) => { if (!r.ok) throw new Error(); return r.json() as Promise<Chain>; }),
    ]).then(([, result]) => { setChain(result); setState("ok"); }).catch(() => setState("error"));
  }, []);
  const deployment = chain?.deployment;
  const pills = state === "loading" ? ["SUCCESSION · CHECKING STATUS…"]
    : state === "error" ? ["SUCCESSION · BACKEND UNREACHABLE"]
    : [
      "API · configured",
      `BASE SEPOLIA · ${chain?.mode === "chain" ? "configured" : "not configured"}`,
      `LISTING CONTRACT · ${deployment?.listing_contract ? "configured" : "not configured"}`,
      `EVALUATOR · ${deployment?.arbiter ? "configured" : "not configured"}`,
      "FINALITY · 3 confirmations",
    ];
  const loop = [...pills, ...pills];
  return (
    <div className="overflow-hidden border-b border-line bg-surface py-2" aria-hidden="true">
      <motion.div className="flex w-max gap-8 whitespace-nowrap" animate={{ x: ["0%", "-50%"] }} transition={{ duration: 20, repeat: Infinity, ease: "linear" }}>
        {loop.map((pill, index) => {
          const positive = pill.includes("configured") && !pill.includes("not configured");
          const unreachable = pill.includes("UNREACHABLE");
          return <span key={`${pill}-${index}`} className={`font-mono text-[11px] uppercase tracking-widest ${positive ? "text-pass" : unreachable ? "text-fail" : "text-accent"}`}>{pill}</span>;
        })}
      </motion.div>
    </div>
  );
}
