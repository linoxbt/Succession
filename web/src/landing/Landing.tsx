import { FadeIn } from "../components/FadeIn";
import { PipelineMotion } from "../components/PipelineMotion";
import { SiteHeader } from "../components/SiteHeader";
import { StatusTicker } from "../components/StatusTicker";
import { to } from "../router";

type Navigate = (route: ReturnType<typeof to.view> | ReturnType<typeof to.landing>) => void;

export function Landing({ navigate }: { navigate: Navigate }) {
  return (
    <div>
      <StatusTicker />
      <div className="mx-auto max-w-5xl px-6">
        <SiteHeader navigate={navigate} />

        <header className="grid gap-10 py-20 md:grid-cols-[1.2fr,1fr] md:items-center">
          <FadeIn>
            <p className="mb-4 font-mono text-xs uppercase tracking-widest text-accent">&gt; the property layer for agent memory</p>
            <h1 className="text-balance font-display text-4xl font-bold leading-[1.1] md:text-5xl">The code is replaceable. The memory is not.</h1>
            <p className="mt-6 max-w-xl text-[15px] leading-relaxed text-ink/80">Succession packages an agent&apos;s accumulated memory, verifies it in an isolated store, and settles payment with ERC-8004 identity on Base.</p>
            <div className="mt-8 flex items-center gap-4">
              <button onClick={() => navigate(to.view("dashboard"))} className="rounded-sm bg-accent px-5 py-2.5 font-mono text-sm font-medium text-bg hover:opacity-90">Open Dashboard</button>
              <button onClick={() => navigate(to.view("guide"))} className="font-mono text-sm text-muted hover:text-ink">Read the guide →</button>
            </div>
          </FadeIn>
          <FadeIn delay={.15}><PipelineMotion /></FadeIn>
        </header>

        <section id="pipeline" className="border-t border-line py-16">
          <FadeIn>
            <p className="mb-3 font-mono text-xs uppercase tracking-widest text-muted">How it works</p>
            <h2 className="max-w-2xl text-balance font-display text-2xl font-bold">Three checks, one atomic handover.</h2>
            <div className="mt-10 grid gap-6 md:grid-cols-3">
              {[
                ["01 — Package", "Commit before delivery", "The seller filters consent, signs the full provenance header, encrypts locally, and commits the Merkle root before a buyer receives plaintext."],
                ["02 — Verify", "Re-hash the destination", "The independent evaluator imports into a separate store and derives the root again. A matching courier package alone is not enough."],
                ["03 — Settle", "Atomic on Base", "One contract transaction releases USDC, transfers ERC-8004 identity, and seals the sale after the evaluator approves."],
              ].map(([eyebrow, title, copy]) => (
                <div key={title} className="rounded-sm border border-line p-6" style={{ background: "radial-gradient(circle at 20% 20%, var(--accent-dim) 0%, transparent 60%)" }}>
                  <span className="font-mono text-xs tracking-widest text-accent">{eyebrow}</span>
                  <h3 className="mt-2 font-display text-lg font-bold">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-ink/75">{copy}</p>
                </div>
              ))}
            </div>
          </FadeIn>
        </section>

        <section id="surfaces" className="border-t border-line py-16">
          <FadeIn>
            <p className="mb-3 font-mono text-xs uppercase tracking-widest text-muted">Operate and verify</p>
            <h2 className="max-w-2xl text-balance font-display text-2xl font-bold">Each role runs beside its own wallet and local memory store.</h2>
            <div className="mt-10 grid gap-6 md:grid-cols-2">
              <button onClick={() => navigate(to.view("guide"))} className="block rounded-sm border border-line bg-surface p-6 text-left transition hover:border-accent/50">
                <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-accent">Operator guide</p>
                <h3 className="font-display text-lg font-bold">Seller · evaluator · buyer</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink/75">Install, inspect, commit, fund, independently evaluate, claim, and recover.</p>
                <span className="mt-4 inline-block font-mono text-xs text-accent">Open the guide →</span>
              </button>
              <button onClick={() => navigate(to.view("terminal"))} className="block rounded-sm border border-line bg-surface p-6 text-left transition hover:border-accent/50">
                <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-accent">Video runbook</p>
                <h3 className="font-display text-lg font-bold">Record verifiable evidence</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink/75">A timed script with safe, copyable commands and the expected result of every terminal scene.</p>
                <span className="mt-4 inline-block font-mono text-xs text-accent">Open the runbook →</span>
              </button>
            </div>
          </FadeIn>
        </section>

        <footer className="flex items-center justify-between border-t border-line py-10 font-mono text-xs text-muted"><span>© {new Date().getFullYear()} Succession</span><span>Built on Sibyl Memory, Base, and ERC-8004</span></footer>
      </div>
    </div>
  );
}
