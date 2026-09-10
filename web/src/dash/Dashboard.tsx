import { ArrowRight, BookOpen, FileText, Network, Server } from "lucide-react";
import { useEffect, useState } from "react";
import { AppShell, StatusBadge } from "../components/AppShell";
import { to } from "../router";

type Navigate = (route: ReturnType<typeof to.view> | ReturnType<typeof to.landing>) => void;
type Chain = { mode?: string; chain_id?: number };

export function Dashboard({ navigate }: { navigate: Navigate }) {
  const [healthy, setHealthy] = useState(false);
  const [chain, setChain] = useState<Chain>({});
  useEffect(() => {
    Promise.all([fetch("/api/health").then(r => r.json()), fetch("/api/chain").then(r => r.json())])
      .then(([health, next]) => { setHealthy(health.status === "ok"); setChain(next); })
      .catch(() => setHealthy(false));
  }, []);
  return <AppShell current="dashboard" navigate={navigate}>
    <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <header className="border-b border-border pb-7"><p className="text-sm font-extrabold uppercase text-muted-foreground">Overview</p><h1 className="mt-2 text-4xl font-extrabold leading-tight sm:text-5xl">Succession dashboard.</h1><p className="mt-3 max-w-2xl text-muted-foreground">A focused view of the hosted service and network used for verified agent-memory transfers.</p></header>
      <section className="mt-8 grid gap-4 md:grid-cols-2">
        <article className="rounded-lg border border-border bg-card p-6 shadow-panel"><div className="flex items-start justify-between"><div><p className="text-sm font-semibold text-muted-foreground">Hosted API</p><p className="mt-7 font-mono text-3xl font-bold">{healthy ? "Healthy" : "Checking"}</p></div><Server className="h-6 w-6 text-primary" /></div><div className="mt-6 border-t border-border pt-4"><StatusBadge status={healthy ? "live" : "pending"} label={healthy ? "Service available" : "Connecting"} /></div></article>
        <article className="rounded-lg border border-border bg-card p-6 shadow-panel"><div className="flex items-start justify-between"><div><p className="text-sm font-semibold text-muted-foreground">Settlement network</p><p className="mt-7 font-mono text-3xl font-bold">{chain.chain_id === 84532 ? "Base Sepolia" : "Checking"}</p></div><Network className="h-6 w-6 text-primary" /></div><div className="mt-6 border-t border-border pt-4"><StatusBadge status={chain.mode === "chain" ? "live" : "pending"} label={chain.mode === "chain" ? "Chain connected" : "Connecting"} /></div></article>
      </section>
      <section className="mt-10 rounded-lg border border-border bg-card p-6 sm:p-8"><p className="text-sm font-extrabold uppercase text-primary">Start here</p><h2 className="mt-2 text-3xl font-extrabold">Move your first memory package.</h2><p className="mt-3 max-w-2xl leading-7 text-muted-foreground">The Guide walks from CLI installation through wallet setup, seller preparation, escrow funding, independent evaluation, buyer import, and recovery. Docs contains the protocol and command reference.</p><div className="mt-7 flex flex-col gap-3 sm:flex-row"><button onClick={() => navigate(to.view("guide"))} className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-5 py-3 text-sm font-extrabold text-primary-foreground shadow-glow hover:bg-primary-hover"><BookOpen className="h-4 w-4" />Open the Guide <ArrowRight className="h-4 w-4" /></button><button onClick={() => navigate(to.view("docs"))} className="inline-flex items-center justify-center gap-2 rounded-md border border-border px-5 py-3 text-sm font-bold hover:border-primary"><FileText className="h-4 w-4" />Read the Docs</button></div></section>
    </div>
  </AppShell>;
}
