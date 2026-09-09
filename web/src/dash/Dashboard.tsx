import { useEffect, useState } from "react";
import { to } from "../router";

type Deployment = { listing_contract?: string; identity_registry?: string; payment_token?: string; arbiter?: string; deployment_tx?: string };
type Chain = { mode?: string; chain_id?: number; head_block?: number; explanation?: string; deployment?: Deployment | null };
type LoadState = "loading" | "ready" | "error";
const short = (value?: string, head = 8, tail = 6) => !value ? "—" : value.length > head + tail + 3 ? `${value.slice(0, head)}…${value.slice(-tail)}` : value;

export default function Dashboard({ navigate }: { navigate: (route: ReturnType<typeof to.view>) => void }) {
  const [chain, setChain] = useState<Chain | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  useEffect(() => {
    Promise.all([fetch("/api/health"), fetch("/api/chain")]).then(async ([health, chainResponse]) => {
      if (!health.ok || !chainResponse.ok) throw new Error("unreachable");
      setChain(await chainResponse.json() as Chain); setState("ready");
    }).catch(() => setState("error"));
  }, []);
  const deployment = chain?.deployment;
  const rows = [
    ["Listing contract", short(deployment?.listing_contract), "Base Sepolia", "Commitment and escrow"],
    ["ERC-8004 registry", short(deployment?.identity_registry), "Live registry", "Identity transfer"],
    ["Payment token", short(deployment?.payment_token), "Circle USDC", "Escrow payment"],
    ["Evaluator", short(deployment?.arbiter), "Separate custody", "Independent verdict"],
  ];
  return (
    <div className="max-w-5xl">
      <p className="mb-3 font-mono text-xs uppercase tracking-widest text-accent">Operator dashboard</p>
      <h1 className="font-display text-2xl font-bold">What Succession is connected to</h1>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink/75">Live deployment state only — real configuration, no demo data or browser wallet session.</p>

      {state === "loading" && <div className="mt-8 rounded-sm border border-line bg-surface px-6 py-10 text-center"><p className="font-mono text-xs uppercase tracking-widest text-muted">Loading deployment…</p></div>}
      {state === "error" && <div className="mt-8 rounded-sm border border-fail/40 bg-fail/10 px-6 py-6 text-center"><p className="font-display text-lg font-bold text-fail">Couldn&apos;t load deployment</p><p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink/70">Check the Railway service and its <code className="font-mono text-accent">/api/health</code> endpoint.</p></div>}
      {state === "ready" && <>
        <div className="mt-8 grid gap-4 sm:grid-cols-4">
          {[
            ["API", "Healthy"],
            ["Network", chain?.chain_id === 84532 ? "Base Sepolia" : `Chain ${chain?.chain_id ?? "—"}`],
            ["Head block", chain?.head_block?.toLocaleString() ?? "—"],
            ["Finality", "3 blocks"],
          ].map(([label, value]) => <div key={label} className="rounded-sm border border-line bg-surface p-4"><p className="font-mono text-[11px] uppercase tracking-wide text-muted">{label}</p><p className="mt-1 font-display text-2xl font-bold">{value}</p></div>)}
        </div>

        <div className="mt-8 overflow-x-auto rounded-sm border border-line">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead><tr className="border-b border-line bg-surface font-mono text-[11px] uppercase tracking-wide text-muted"><th className="px-4 py-3">Component</th><th className="px-4 py-3">Address</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Purpose</th></tr></thead>
            <tbody className="divide-y divide-line">{rows.map(([component, address, status, purpose]) => <tr key={component} className="hover:bg-surface/60"><td className="px-4 py-3 font-medium">{component}</td><td className="px-4 py-3 font-mono text-xs">{address}</td><td className="px-4 py-3 font-mono text-xs uppercase text-pass">{status}</td><td className="px-4 py-3 text-xs text-muted">{purpose}</td></tr>)}</tbody>
          </table>
        </div>

        <div className="mt-8 rounded-sm border border-line bg-surface px-6 py-6"><p className="font-display text-lg font-bold">Run the role-separated workflow</p><p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink/70">Seller, evaluator, and buyer commands execute from separate terminal environments. Keys never enter this frontend.</p><div className="mt-4 flex gap-4 font-mono text-xs"><button onClick={() => navigate(to.view("guide"))} className="text-accent hover:underline">Operator guide →</button><button onClick={() => navigate(to.view("terminal"))} className="text-accent hover:underline">Video runbook →</button></div></div>
      </>}
    </div>
  );
}
