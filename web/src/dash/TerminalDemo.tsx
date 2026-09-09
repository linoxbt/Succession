import { Command } from "./Guide";

const beats = [
  ["Preflight", "Show the checkout, current commit, CLI connection, and a passing local audit.", `git status --short\ngit log -1 --oneline\n.venv/bin/succession status\n.venv/bin/succession audit`],
  ["Live deployment", "Prove the hosted API and Base Sepolia contract are responding.", `curl -s https://succession-production-7320.up.railway.app/api/health\ncurl -s https://succession-production-7320.up.railway.app/api/chain | python3 -m json.tool`],
  ["Seller proof", "Show what can transfer, then verify a local round-trip before money moves.", `.venv/bin/succession inventory --db seller.db --tenant seller-agent\n.venv/bin/succession prove --db seller.db --tenant seller-agent \\\n  --agent erc8004:84532:YOUR_AGENT_ID`],
  ["Role-separated flow", "Use three terminal tabs. Keep every private-key export above the visible recording area.", `# Seller\n.venv/bin/succession fulfil\n\n# Evaluator\n.venv/bin/succession evaluate --listing listing-YOUR_ID \\\n  --db evaluator.db --tenant isolated --yes\n\n# Buyer\n.venv/bin/succession claim --listing listing-YOUR_ID \\\n  --db buyer.db --tenant successor`],
  ["Recovery and evidence", "Restart both hosts. The seller republishes from its durable vault; the buyer repeats claim against the same destination journal.", `.venv/bin/succession fulfil --listing listing-YOUR_ID --once\n.venv/bin/succession claim --listing listing-YOUR_ID \\\n+  --db buyer.db --tenant successor\n.venv/bin/succession audit --check-chain`],
] as const;

export default function TerminalDemo() {
  return (
    <div className="mx-auto max-w-reading">
      <header className="pb-12">
        <p className="chapter-mark">Video runbook</p>
        <h1 className="display-type mt-4 text-display font-bold text-ink">What to test while recording.</h1>
        <p className="mt-5 text-lede text-muted">Record the result of each command. Use placeholder labels on screen, keep key exports hidden, and show transaction hashes only after broadcasts complete.</p>
      </header>
      {beats.map(([title, narration, command], index) => (
        <section key={title} className="border-t border-rule py-9">
          <p className="chapter-mark">{String(index + 1).padStart(2, "0")} / {title}</p>
          <p className="mt-3 text-body text-muted">{narration}</p>
          <Command>{command}</Command>
        </section>
      ))}
      <aside className="mt-4 rounded-card border border-rule bg-shade p-6">
        <h2 className="font-semibold text-ink">Before you press record</h2>
        <p className="mt-2 text-body text-muted">Use a clean shell history, disable notifications, enlarge terminal text, prepare three named tabs, and confirm that no <code>.env</code> file or private key can appear in autocomplete.</p>
      </aside>
    </div>
  );
}
