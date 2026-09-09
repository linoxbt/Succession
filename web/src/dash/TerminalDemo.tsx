import { CopyableCodeBlock } from "../components/CopyableCodeBlock";
import { GuideStep } from "../components/GuideStep";
import { SiteHeader } from "../components/SiteHeader";
import { to } from "../router";

type Navigate = (route: ReturnType<typeof to.view> | ReturnType<typeof to.landing>) => void;
export default function TerminalDemo({ navigate }: { navigate: Navigate }) {
  return <div><SiteHeader navigate={navigate} /><div className="mx-auto max-w-3xl px-6 pb-24">
    <header className="py-12"><p className="mb-3 font-mono text-xs uppercase tracking-widest text-accent">Video runbook · 6–8 minutes</p><h1 className="text-balance font-display text-3xl font-bold">Test Succession while you record.</h1><p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-ink/80">Prepare four tabs named STATUS, SELLER, EVALUATOR, and BUYER. Set keys before recording, clear each terminal, and never display an environment file.</p></header>
    <GuideStep n={1} title="Preflight"><p className="text-sm text-ink/75">Show the release commit and the local audit.</p><CopyableCodeBlock>{`git status --short\ngit log -1 --oneline\n.venv/bin/succession status\n.venv/bin/succession audit`}</CopyableCodeBlock></GuideStep>
    <GuideStep n={2} title="Live deployment"><p className="text-sm text-ink/75">Prove the dashboard comes from the hosted service.</p><CopyableCodeBlock>{`curl -s https://succession-production-7320.up.railway.app/api/health\ncurl -s https://succession-production-7320.up.railway.app/api/chain | python3 -m json.tool`}</CopyableCodeBlock></GuideStep>
    <GuideStep n={3} title="Seller proof"><CopyableCodeBlock>{`.venv/bin/succession inventory --db seller.db --tenant seller-agent\n.venv/bin/succession prove --db seller.db --tenant seller-agent \\\n  --agent erc8004:84532:YOUR_AGENT_ID`}</CopyableCodeBlock></GuideStep>
    <GuideStep n={4} title="Fund and evaluate"><CopyableCodeBlock>{`# BUYER\n.venv/bin/succession buy --listing listing-YOUR_ID --yes\n\n# SELLER\n.venv/bin/succession fulfil --listing listing-YOUR_ID --once\n\n# EVALUATOR\n.venv/bin/succession evaluate --listing listing-YOUR_ID \\\n  --db evaluator.db --tenant isolated --yes`}</CopyableCodeBlock></GuideStep>
    <GuideStep n={5} title="Claim and recover"><CopyableCodeBlock>{`# BUYER\n.venv/bin/succession claim --listing listing-YOUR_ID \\\n  --db buyer.db --tenant successor\n\n# REPLAY AFTER RESTART\n.venv/bin/succession fulfil --listing listing-YOUR_ID --once\n.venv/bin/succession claim --listing listing-YOUR_ID \\\n  --db buyer.db --tenant successor`}</CopyableCodeBlock></GuideStep>
    <GuideStep n={6} title="Close on evidence"><CopyableCodeBlock>{`.venv/bin/succession audit --check-chain`}</CopyableCodeBlock><p className="text-sm leading-relaxed text-ink/80">Expected: seven passed, zero failed, zero skipped. The full narration is in <code className="font-mono text-accent">docs/VIDEO_DEMO_SCRIPT.md</code>.</p><button onClick={() => navigate(to.view("dashboard"))} className="font-mono text-sm text-accent hover:underline">Open the dashboard →</button></GuideStep>
  </div></div>;
}
