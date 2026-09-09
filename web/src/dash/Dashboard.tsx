import { useEffect, useState } from "react";

type Health = { status?: string };
type Deployment = {
  listing_contract?: string;
  identity_registry?: string;
  payment_token?: string;
  evaluator?: string;
  arbiter?: string;
};
type Chain = {
  mode?: string;
  chain_id?: number | null;
  head_block?: number;
  explanation?: string;
  deployment?: Deployment | null;
};

const API = import.meta.env.VITE_API_URL ?? "";

function short(value?: string) {
  if (!value) return "Not reported";
  return value.length > 18 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value;
}

function StatusCard({ label, value, detail, healthy = true }: { label: string; value: string; detail: string; healthy?: boolean }) {
  return (
    <article className="rounded-card border border-rule bg-paper p-5 shadow-card">
      <p className="text-label font-semibold uppercase text-faint">{label}</p>
      <div className="mt-3 flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${healthy ? "bg-closed" : "bg-void"}`} aria-hidden="true" />
        <p className="evidence-type text-heading font-semibold text-ink">{value}</p>
      </div>
      <p className="mt-2 text-micro text-muted">{detail}</p>
    </article>
  );
}

export default function Dashboard({ onGuide }: { onGuide: () => void }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [chain, setChain] = useState<Chain | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetch(`${API}/api/health`).then((r) => { if (!r.ok) throw new Error(); return r.json() as Promise<Health>; }),
      fetch(`${API}/api/chain`).then((r) => { if (!r.ok) throw new Error(); return r.json() as Promise<Chain>; }),
    ]).then(([nextHealth, nextChain]) => {
      if (!active) return;
      setHealth(nextHealth);
      setChain(nextChain);
    }).catch(() => active && setFailed(true));
    return () => { active = false; };
  }, []);

  const deployment = chain?.deployment;
  const evaluator = deployment?.evaluator ?? deployment?.arbiter;
  const loading = !failed && (!health || !chain);
  const chainReady = chain?.mode === "chain";

  return (
    <div className="mx-auto max-w-wide">
      <header className="max-w-reading">
        <p className="chapter-mark">Operator dashboard</p>
        <h1 className="display-type mt-4 text-display font-bold text-ink">Succession is ready to verify.</h1>
        <p className="mt-5 text-lede text-muted">
          Check the live service and contract, then run each role from its own terminal. Private keys stay in the operator environments that use them.
        </p>
      </header>

      {loading ? <p className="mt-10 text-micro text-muted" role="status">Checking the live deployment…</p> : null}
      {failed ? (
        <div className="mt-10 rounded-card border border-void/40 bg-void/5 p-5">
          <p className="font-semibold text-void">The service could not be reached.</p>
          <p className="mt-2 text-body text-muted">The guide remains available for local operation and diagnostics.</p>
        </div>
      ) : null}

      {!loading && !failed ? (
        <section className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Deployment status">
          <StatusCard label="API" value={health?.status === "ok" ? "Healthy" : "Degraded"} detail="Railway service health" healthy={health?.status === "ok"} />
          <StatusCard label="Network" value={chain?.chain_id === 84532 ? "Base Sepolia" : `Chain ${chain?.chain_id ?? "—"}`} detail={`Head block ${chain?.head_block?.toLocaleString() ?? "unavailable"}`} healthy={chainReady} />
          <StatusCard label="Settlement" value={chainReady ? "On chain" : "Unavailable"} detail={chain?.explanation ?? "No chain response"} healthy={chainReady} />
          <StatusCard label="Finality" value="3 blocks" detail="Base Sepolia receipt policy" healthy={chainReady} />
        </section>
      ) : null}

      <section className="mt-16 grid gap-10 lg:grid-cols-[1.1fr_.9fr]">
        <div>
          <p className="chapter-mark">Live configuration</p>
          <h2 className="display-type mt-3 text-title font-bold">Deployment evidence</h2>
          <dl className="mt-6 divide-y divide-hairline border-y border-hairline">
            {[
              ["Listing contract", deployment?.listing_contract],
              ["ERC-8004 registry", deployment?.identity_registry],
              ["Payment token", deployment?.payment_token],
              ["Independent evaluator", evaluator],
            ].map(([label, value]) => (
              <div key={label} className="grid gap-1 py-4 sm:grid-cols-[11rem_1fr] sm:items-baseline">
                <dt className="text-micro text-faint">{label}</dt>
                <dd className="evidence-type break-all text-micro text-ink" title={value}>{short(value)}</dd>
              </div>
            ))}
          </dl>
        </div>

        <aside className="rounded-panel bg-carbon p-7 text-chalk">
          <p className="text-label font-semibold uppercase text-chalkFaint">Run the protocol</p>
          <h2 className="display-type mt-3 text-title font-bold">Three roles. Three terminals.</h2>
          <ol className="mt-6 space-y-5 text-body text-chalkMuted">
            <li><span className="mr-3 text-signal">01</span>Seller inventories, proves, lists, and fulfils.</li>
            <li><span className="mr-3 text-signal">02</span>Evaluator imports independently and settles its verdict.</li>
            <li><span className="mr-3 text-signal">03</span>Buyer claims and re-hashes the destination store.</li>
          </ol>
          <button onClick={onGuide} className="mt-8 rounded-control bg-signal px-4 py-2.5 text-micro font-semibold text-white transition hover:bg-press">
            Open the guide
          </button>
        </aside>
      </section>

      <section className="mt-16 border-t border-rule pt-8">
        <p className="chapter-mark">Custody boundary</p>
        <div className="mt-5 grid gap-5 md:grid-cols-3">
          {[
            ["Seller key", "Signs the package and listing transactions. Kept only by the seller host."],
            ["Evaluator key", "Receives the content key and signs the independent on-chain verdict."],
            ["Buyer key", "Funds escrow and authorizes collection after evaluator settlement."],
          ].map(([title, copy]) => (
            <div key={title} className="border-l border-rule pl-5">
              <h3 className="font-semibold text-ink">{title}</h3>
              <p className="mt-2 text-body text-muted">{copy}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
