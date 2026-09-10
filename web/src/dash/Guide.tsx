import { CheckCircle2, KeyRound, PackageCheck, ShieldCheck } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { CommandBlock } from "../components/CommandBlock";
import { to } from "../router";

type Navigate = (route: ReturnType<typeof to.view> | ReturnType<typeof to.landing>) => void;
const evaluator = "0x518477058d12e60D74E42b799F5ad0f5c4FFf31b";
const steps = [
  { Icon: PackageCheck, role: "Seller", title: "Prove and list the memory", text: "Inventory consent-filtered records, prove the isolated round trip, then commit the signed root.", command: `.venv/bin/succession inventory --db seller.db --tenant seller-agent\n.venv/bin/succession prove --db seller.db --tenant seller-agent \\\n  --agent erc8004:84532:YOUR_AGENT_ID\n.venv/bin/succession list --db seller.db --tenant seller-agent \\\n  --agent erc8004:84532:YOUR_AGENT_ID --price 1000000` },
  { Icon: ShieldCheck, role: "Evaluator", title: "Verify in an isolated store", text: "Use a separately held key and database. The evaluator re-derives the destination root before approving settlement.", command: `.venv/bin/succession evaluate --listing listing-YOUR_ID \\\n  --db evaluator.db --tenant isolated --yes` },
  { Icon: KeyRound, role: "Buyer", title: "Fund, claim, and verify", text: "Review the commitment, fund escrow, then claim only after the evaluator has accepted the package.", command: `.venv/bin/succession buy --listing listing-YOUR_ID --yes\n.venv/bin/succession claim --listing listing-YOUR_ID \\\n  --db buyer.db --tenant successor\n.venv/bin/succession inventory --db buyer.db --tenant successor` },
];

export function Guide({ navigate }: { navigate: Navigate }) {
  return <AppShell current="guide" navigate={navigate} evaluator={evaluator}><div className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
    <header className="border-b border-border pb-7"><p className="text-sm font-extrabold uppercase text-muted-foreground">Operator guide</p><h1 className="mt-2 text-4xl font-extrabold sm:text-5xl">Run Succession from your terminal.</h1><p className="mt-3 max-w-3xl text-muted-foreground">Prepare each role in a separate terminal and keep seller, evaluator, and buyer wallet keys in separate custody.</p></header>
    <div className="mt-8 grid gap-6 xl:grid-cols-[1fr_18rem]"><div className="space-y-4">{steps.map(({Icon,role,title,text,command},index) => <article key={role} className="rounded-lg border border-border bg-card p-6 shadow-panel"><div className="flex items-start gap-4"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground"><Icon className="h-5 w-5" /></span><div><p className="font-mono text-xs font-bold uppercase text-primary">Step {index + 1} · {role}</p><h2 className="mt-1 text-2xl font-bold">{title}</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">{text}</p></div></div><CommandBlock>{command}</CommandBlock></article>)}</div>
      <aside className="space-y-4"><div className="rounded-lg border border-border bg-card p-5"><p className="text-sm font-extrabold uppercase text-muted-foreground">Preflight</p><div className="mt-4 space-y-3">{["Base Sepolia ETH for gas", "Test USDC in buyer wallet", "Agent owned by seller", "Three distinct role terminals"].map(item => <p key={item} className="flex gap-2 text-sm"><CheckCircle2 className="h-4 w-4 shrink-0 text-success" />{item}</p>)}</div></div><div className="rounded-lg border border-primary/30 bg-primary/10 p-5"><p className="font-bold">Start with the local audit</p><p className="mt-2 text-sm leading-6 text-muted-foreground">It proves the deterministic export, import, and hash path before any transaction spends gas.</p><CommandBlock>.venv/bin/succession audit</CommandBlock></div></aside>
    </div>
  </div></AppShell>;
}
