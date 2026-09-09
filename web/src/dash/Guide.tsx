import { useState } from "react";

export function Command({ children }: { children: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(children);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };
  return (
    <div className="relative mt-4 overflow-hidden rounded-card border border-carbonRule bg-carbon p-5 pr-24 text-chalk">
      <pre className="overflow-x-auto whitespace-pre-wrap text-micro leading-6"><code>{children}</code></pre>
      <button onClick={copy} className="absolute right-3 top-3 rounded-control border border-carbonRule px-3 py-1.5 text-label text-chalkMuted hover:text-chalk">
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-rule py-9">
      <div className="flex items-baseline gap-4">
        <span className="evidence-type text-micro text-signal">{String(n).padStart(2, "0")}</span>
        <h2 className="display-type text-heading font-bold text-ink">{title}</h2>
      </div>
      <div className="ml-9 mt-4 text-body text-muted">{children}</div>
    </section>
  );
}

export default function Guide({ onTerminal }: { onTerminal: () => void }) {
  return (
    <div className="mx-auto max-w-reading">
      <header className="pb-12">
        <p className="chapter-mark">Operator guide</p>
        <h1 className="display-type mt-4 text-display font-bold text-ink">Use Succession from the terminal.</h1>
        <p className="mt-5 text-lede text-muted">The browser reports deployment health. Sale operations run beside each local Sibyl store so plaintext and signing keys remain under role-specific custody.</p>
      </header>

      <Step n={1} title="Install and inspect">
        <p>Install the CLI, identify the connected service, and run the self-audit before using any wallet.</p>
        <Command>{`pipx install "succession-cli[chain,mcp]"\nexport SUCCESSION_MARKETPLACE=https://succession-production-7320.up.railway.app\nexport BASE_SEPOLIA_RPC_URL=https://sepolia.base.org\nsuccession status\nsuccession audit --check-chain`}</Command>
      </Step>

      <Step n={2} title="Prepare the seller store">
        <p>Inventory and prove the exact tenant locally. The prove command round-trips through an isolated temporary store without publishing.</p>
        <Command>{`export SUCCESSION_SIGNING_KEY=0x…\nsuccession inventory --db seller.db --tenant seller-agent\nsuccession prove --db seller.db --tenant seller-agent \\\n  --agent erc8004:84532:YOUR_AGENT_ID`}</Command>
      </Step>

      <Step n={3} title="Commit and fulfil">
        <p>Listing commits the signed Merkle root on Base Sepolia. Fulfilment releases keys only after the configured confirmation depth.</p>
        <Command>{`succession list --db seller.db --tenant seller-agent \\\n  --agent erc8004:84532:YOUR_AGENT_ID --price 1000000\nsuccession fulfil`}</Command>
      </Step>

      <Step n={4} title="Fund from the buyer host">
        <p>Use a different wallet and machine. Review without <code>--yes</code>, then explicitly broadcast.</p>
        <Command>{`export SUCCESSION_BUYER_KEY=0x…\nsuccession show --listing listing-YOUR_ID\nsuccession buy --listing listing-YOUR_ID\nsuccession buy --listing listing-YOUR_ID --yes`}</Command>
      </Step>

      <Step n={5} title="Evaluate independently">
        <p>The evaluator needs its own key and empty store. It verifies the seller signature, imports the package, re-exports it, and compares the destination root before settlement.</p>
        <Command>{`export SUCCESSION_EVALUATOR_KEY=0x…\nsuccession evaluate --listing listing-YOUR_ID \\\n  --db evaluator.db --tenant isolated --yes`}</Command>
      </Step>

      <Step n={6} title="Claim and verify on the buyer host">
        <p>The buyer collects only after evaluator settlement. The CLI verifies the imported store against the committed root.</p>
        <Command>{`succession claim --listing listing-YOUR_ID \\\n  --db buyer.db --tenant successor\nsuccession inventory --db buyer.db --tenant successor`}</Command>
      </Step>

      <Step n={7} title="Recover after interruption">
        <p>Restart both hosts, then run recovery. Operations are replay-safe and use their durable journals to resume incomplete work.</p>
        <Command>{`succession fulfil --listing listing-YOUR_ID --once\nsuccession claim --listing listing-YOUR_ID \\\n+  --db buyer.db --tenant successor\nsuccession audit --check-chain`}</Command>
      </Step>

      <button onClick={onTerminal} className="mt-4 rounded-control bg-signal px-5 py-3 text-micro font-semibold text-white hover:bg-press">Open the recording checklist</button>
    </div>
  );
}
