import { CirclePlay, Clock3 } from "lucide-react";
import { AppShell } from "../components/AppShell";
import { CommandBlock } from "../components/CommandBlock";
import { to } from "../router";

type Navigate = (route: ReturnType<typeof to.view> | ReturnType<typeof to.landing>) => void;
const evaluator = "0x518477058d12e60D74E42b799F5ad0f5c4FFf31b";
const scenes = [
  ["00:00", "Open the dashboard", "Show API health, Base Sepolia, the head block, finality policy, and the four deployment addresses.", `curl -s https://succession-production-7320.up.railway.app/api/health\ncurl -s https://succession-production-7320.up.railway.app/api/chain | python3 -m json.tool`],
  ["00:45", "Run preflight", "Prove the repository state and the local seven-claim data path before spending gas.", `git status --short\ngit log -1 --oneline\n.venv/bin/succession status\n.venv/bin/succession audit`],
  ["01:30", "Prove and commit", "Inventory the seller store, reproduce the root in isolation, and create the on-chain listing.", `.venv/bin/succession prove --db seller.db --tenant seller-agent \\\n  --agent erc8004:84532:YOUR_AGENT_ID\n.venv/bin/succession list --db seller.db --tenant seller-agent \\\n  --agent erc8004:84532:YOUR_AGENT_ID --price 1000000`],
  ["03:00", "Fund and evaluate", "Fund escrow from BUYER, release once from SELLER, and settle with the separately held EVALUATOR key.", `.venv/bin/succession buy --listing listing-YOUR_ID --yes\n.venv/bin/succession fulfil --listing listing-YOUR_ID --once\n.venv/bin/succession evaluate --listing listing-YOUR_ID \\\n  --db evaluator.db --tenant isolated --yes`],
  ["05:00", "Claim and recover", "Import into the buyer store, repeat both host operations, then finish with the live-chain audit.", `.venv/bin/succession claim --listing listing-YOUR_ID \\\n  --db buyer.db --tenant successor\n.venv/bin/succession fulfil --listing listing-YOUR_ID --once\n.venv/bin/succession audit --check-chain`],
];

export function TerminalDemo({ navigate }: { navigate: Navigate }) {
  return <AppShell current="terminal" navigate={navigate} evaluator={evaluator}><div className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
    <header className="flex flex-col gap-5 border-b border-border pb-7 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-sm font-extrabold uppercase text-muted-foreground">6–8 minute recording</p><h1 className="mt-2 text-4xl font-extrabold sm:text-5xl">Test Succession while you record.</h1><p className="mt-3 max-w-3xl text-muted-foreground">Prepare four terminal tabs named STATUS, SELLER, EVALUATOR, and BUYER. Replace placeholders before recording.</p></div><span className="inline-flex w-fit items-center gap-2 rounded-full border border-primary/30 bg-card px-4 py-2 text-sm font-bold shadow-panel"><CirclePlay className="h-4 w-4 text-primary" /> Live transaction walkthrough</span></header>
    <section className="mt-8 space-y-4">{scenes.map(([time,title,body,command],index) => <article key={time} className="grid gap-5 rounded-lg border border-border bg-card p-6 shadow-panel md:grid-cols-[8rem_1fr]"><div><span className="inline-flex items-center gap-2 font-mono text-sm font-bold text-primary"><Clock3 className="h-4 w-4" />{time}</span><p className="mt-2 text-xs font-extrabold uppercase text-muted-foreground">Scene {index + 1}</p></div><div><h2 className="text-2xl font-bold">{title}</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p><CommandBlock>{String(command)}</CommandBlock></div></article>)}</section>
    <div className="mt-6 rounded-lg border border-warning/40 bg-warning/10 p-5 text-sm"><strong>Recording hygiene:</strong> load wallet keys before recording, clear each terminal, and never display <code className="font-mono">.env</code> or run <code className="font-mono">env</code> on camera.</div>
  </div></AppShell>;
}
