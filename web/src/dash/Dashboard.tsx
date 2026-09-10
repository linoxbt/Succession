import { ArrowRight, Blocks, Database, Network, Server, ShieldCheck, WalletCards } from "lucide-react";
import { useEffect, useState } from "react";
import { AppShell, StatusBadge } from "../components/AppShell";
import { to } from "../router";

type Navigate = (route: ReturnType<typeof to.view> | ReturnType<typeof to.landing>) => void;
type Deployment = { listing_contract?: string; identity_registry?: string; payment_token?: string; arbiter?: string; deployment_tx?: string };
type Chain = { mode?: string; chain_id?: number; head_block?: number; deployment?: Deployment };
const short = (value?: string) => value ? `${value.slice(0, 8)}…${value.slice(-6)}` : "Unavailable";

export function Dashboard({ navigate }: { navigate: Navigate }) {
  const [healthy, setHealthy] = useState(false);
  const [chain, setChain] = useState<Chain>({});
  useEffect(() => {
    Promise.all([fetch("/api/health").then(r => r.json()), fetch("/api/chain").then(r => r.json())])
      .then(([health, next]) => { setHealthy(health.status === "ok"); setChain(next); })
      .catch(() => setHealthy(false));
  }, []);
  const deployment = chain.deployment ?? {};
  const stats = [
    { label: "Hosted API", value: healthy ? "Healthy" : "Checking", Icon: Server },
    { label: "Network", value: chain.chain_id === 84532 ? "Base Sepolia" : "Checking", Icon: Network },
    { label: "Head block", value: chain.head_block?.toLocaleString() ?? "—", Icon: Blocks },
    { label: "Finality policy", value: "3 blocks", Icon: ShieldCheck },
  ];
  const contracts = [
    ["Succession escrow", deployment.listing_contract], ["ERC-8004 registry", deployment.identity_registry],
    ["USDC payment token", deployment.payment_token], ["Independent evaluator", deployment.arbiter],
  ];
  return <AppShell current="dashboard" navigate={navigate} evaluator={deployment.arbiter}>
    <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <header className="flex flex-col gap-5 border-b border-border pb-7 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-sm font-extrabold uppercase text-muted-foreground">Overview</p><h1 className="mt-2 text-4xl font-extrabold leading-tight sm:text-5xl">Protocol operations.</h1><p className="mt-3 max-w-2xl text-muted-foreground">Live infrastructure, evaluator custody, and release evidence for the deployed Succession workflow.</p></div><div className="flex gap-2"><button onClick={() => navigate(to.view("guide"))} className="rounded-md border border-border bg-card px-4 py-3 text-sm font-bold hover:border-primary">Operator Guide</button><button onClick={() => navigate(to.view("terminal"))} className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-3 text-sm font-extrabold text-primary-foreground shadow-glow hover:bg-primary-hover">Video Checklist <ArrowRight className="h-4 w-4" /></button></div></header>
      <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{stats.map(({label,value,Icon}) => <article key={label} className="rounded-lg border border-border bg-card p-5 shadow-panel"><div className="flex items-start justify-between"><p className="text-sm font-semibold text-muted-foreground">{label}</p><Icon className="h-5 w-5 text-primary" /></div><p className="mt-7 font-mono text-2xl font-bold tracking-tight">{value}</p></article>)}</section>
      <section className="mt-8 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <article className="rounded-lg border border-border bg-card p-6 shadow-panel"><div className="flex items-center justify-between"><div><p className="text-sm font-extrabold uppercase text-muted-foreground">Live deployment</p><h2 className="mt-2 text-2xl font-bold">Base Sepolia contracts</h2></div><StatusBadge status={healthy && chain.mode === "chain" ? "live" : "pending"} /></div><div className="mt-6 divide-y divide-border">{contracts.map(([label,value]) => <div key={label} className="flex items-center justify-between gap-4 py-4"><span className="text-sm text-muted-foreground">{label}</span><code className="font-mono text-xs font-semibold" title={value}>{short(value)}</code></div>)}</div></article>
        <article className="rounded-lg border border-border bg-card p-6"><p className="text-sm font-extrabold uppercase text-muted-foreground">Role workflow</p><h2 className="mt-2 text-2xl font-bold">Three parties, one atomic handover</h2><div className="mt-6 space-y-3">{[
          ["01", "Seller", "Proves, signs, and commits the memory package before delivery."],
          ["02", "Evaluator", "Imports into an isolated store and independently derives the root."],
          ["03", "Buyer", "Funds escrow, then claims the key after successful settlement."],
        ].map(([step,title,body]) => <div key={title} className="grid grid-cols-[2.5rem_1fr] gap-4 rounded-md border border-border bg-background/50 p-4"><span className="font-mono text-sm font-bold text-primary">{step}</span><div><p className="font-bold">{title}</p><p className="mt-1 text-sm leading-6 text-muted-foreground">{body}</p></div></div>)}</div></article>
      </section>
      <section className="mt-12"><p className="text-sm font-extrabold uppercase text-muted-foreground">Protocol evidence</p><h2 className="mt-2 text-3xl font-extrabold">What the live release proves</h2><div className="mt-5 grid gap-4 lg:grid-cols-3">{[
        { Icon: Database, title: "Commitment", body: "Signed Merkle roots bind the disclosed package before the evaluator receives it.", meta: short(deployment.listing_contract) },
        { Icon: ShieldCheck, title: "Evaluation", body: "A separate wallet and destination store control the verdict and settlement.", meta: short(deployment.arbiter) },
        { Icon: WalletCards, title: "Recovery", body: "Durable seller and buyer journals replay interrupted work without duplicate effects.", meta: "two-host verified" },
      ].map(({Icon,title,body,meta}) => <article key={title} className="rounded-lg border border-border bg-card p-6 transition hover:-translate-y-0.5 hover:shadow-glow"><div className="flex items-center justify-between"><Icon className="h-6 w-6 text-primary" /><StatusBadge status="live" /></div><h3 className="mt-8 text-xl font-bold">{title}</h3><p className="mt-2 min-h-16 text-sm leading-6 text-muted-foreground">{body}</p><div className="mt-5 border-t border-border pt-4 font-mono text-xs font-semibold">{meta}</div></article>)}</div></section>
    </div>
  </AppShell>;
}
