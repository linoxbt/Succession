/**
 * The landing page.
 *
 * Statements, not paragraphs. Every line is a claim the product can be held to,
 * and nothing on the page explains itself twice. Scale and motion do the
 * persuading; the illustrations draw the actual mechanism rather than
 * decorating around it.
 */
import { Mark, Wordmark } from "../brand/Logo";
import { CountUp, Reveal } from "./motion";
import { HashVerification, TransferDiagram } from "./visuals";

const MECHANISM = [
  ["Export", "The agent's whole memory becomes one signed, portable package."],
  ["Commit", "A Merkle root goes on Base before a buyer exists."],
  ["Settle", "Payment, identity and the seal move in one transaction."],
  ["Verify", "The buyer re-hashes their own store. Mismatch refunds."],
];

const STACKS = [
  ["Base", "Escrow, ERC-8004 identity transfer, and the seal — one transaction, or none of them."],
  ["Virtuals ACP", "Job history a buyer verifies by on-chain job id, not by trusting the seller."],
  ["Sibyl Memory", "Five tiers exported, re-keyed under a new tenant, and re-hashed on arrival."],
];

const LIFECYCLE: [string, string, "built" | "roadmap"][] = [
  ["Sell", "Full transfer, permanent, against payment", "built"],
  ["Partial", "A category filter before serialization", "built"],
  ["Archive", "Freeze a tenant without transferring it", "built"],
  ["Lease", "Sell, plus a re-seal timer on the buyer's copy", "roadmap"],
  ["Inherit", "The same pipeline, no payment leg", "roadmap"],
  ["Merge", "Two evolved memories, one conflict rule", "roadmap"],
  ["Split", "Partition along a category boundary", "roadmap"],
];

export function Landing({
  onEnter,
  onDocs,
}: {
  onEnter: () => void;
  onDocs: () => void;
}) {
  return (
    <div className="min-h-screen bg-base">
      <Header onEnter={onEnter} onDocs={onDocs} />
      <Hero onEnter={onEnter} onDocs={onDocs} />
      <Thesis />
      <Mechanism />
      <Verification />
      <Numbers />
      <Stacks />
      <Lifecycle />
      <Close onEnter={onEnter} />
      <Footer onDocs={onDocs} />
    </div>
  );
}

function Header({ onEnter, onDocs }: { onEnter: () => void; onDocs: () => void }) {
  return (
    <header className="sticky top-0 z-30 border-b border-line/60 bg-base/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-content items-center justify-between px-6 py-4">
        <Wordmark size={22} animate />
        <nav className="flex items-center gap-2 sm:gap-5">
          <button onClick={onDocs} className="px-2 text-[0.8125rem] text-secondary hover:text-primary">
            Docs
          </button>
          <a
            href="https://github.com/linoxbt/Succession"
            className="hidden px-2 text-[0.8125rem] text-secondary hover:text-primary sm:block"
          >
            GitHub
          </a>
          <button
            onClick={onEnter}
            className="rounded-md bg-primary px-3.5 py-1.5 text-[0.8125rem] font-medium text-base transition-colors hover:bg-white"
          >
            Open console
          </button>
        </nav>
      </div>
    </header>
  );
}

function Hero({ onEnter, onDocs }: { onEnter: () => void; onDocs: () => void }) {
  return (
    <section className="relative overflow-hidden">
      <div className="grid-field pointer-events-none absolute inset-0" aria-hidden />
      <div className="relative mx-auto max-w-content px-6 pb-28 pt-20 sm:pt-32">
        <Reveal>
          <p className="mb-7 text-[0.8125rem] font-medium uppercase tracking-[0.16em] text-accent">
            The property layer for agent memory
          </p>
        </Reveal>
        <Reveal delay={90}>
          <h1 className="max-w-[15ch] text-display font-semibold">
            The code is replaceable. The memory is not.
          </h1>
        </Reveal>
        <Reveal delay={180}>
          <p className="mt-9 max-w-[48ch] text-lede text-secondary">
            Succession turns an agent's accumulated memory into an asset that can
            be sold, verified, and settled on chain.
          </p>
        </Reveal>
        <Reveal delay={260}>
          <div className="mt-11 flex flex-wrap items-center gap-3">
            <button
              onClick={onEnter}
              className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-base transition-colors hover:bg-white"
            >
              Open console
            </button>
            <button
              onClick={onDocs}
              className="rounded-md border border-line px-5 py-2.5 text-sm font-medium text-primary transition-colors hover:border-secondary"
            >
              Read the docs
            </button>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Thesis() {
  return (
    <Section>
      <Reveal>
        <h2 className="max-w-[21ch] text-headline font-semibold">
          The model is the employee. The memory is the customer book.
        </h2>
      </Reveal>
      <Reveal delay={120}>
        <p className="mt-7 max-w-[50ch] text-lede text-secondary">
          Succession does not sell the employee.
        </p>
      </Reveal>
    </Section>
  );
}

function Mechanism() {
  return (
    <Section label="The mechanism">
      <Reveal>
        <TransferDiagram />
      </Reveal>
      <div className="mt-14 grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
        {MECHANISM.map(([step, line], i) => (
          <Reveal key={step} delay={i * 90}>
            <div className="h-full bg-base p-7">
              <span className="tnum text-xs text-faint">0{i + 1}</span>
              <h3 className="mt-4 text-lg font-semibold tracking-tight">{step}</h3>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-secondary">{line}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function Verification() {
  return (
    <Section label="Proof">
      <Reveal>
        <h2 className="max-w-[19ch] text-headline font-semibold">
          Anyone can claim a transfer happened.
        </h2>
      </Reveal>
      <Reveal delay={110}>
        <p className="mt-7 max-w-[54ch] text-lede text-secondary">
          The buyer re-hashes their own store and compares it to a root committed
          before they existed. Escrow releases on a match and refunds on anything
          else.
        </p>
      </Reveal>
      <Reveal delay={200} className="mt-12">
        <HashVerification />
      </Reveal>
    </Section>
  );
}

function Numbers() {
  const items: [React.ReactNode, string][] = [
    [<CountUp key="t" to={5} />, "tiers of memory transferred, not just entities"],
    [<CountUp key="x" to={1} />, "transaction settles payment, identity and the seal"],
    [<CountUp key="s" to={0} />, "ways to keep operating a sold agent"],
    [<CountUp key="c" to={174} />, "tests, including deliberate corruption"],
  ];
  return (
    <Section>
      <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-4">
        {items.map(([value, label], i) => (
          <Reveal key={label} delay={i * 80}>
            <div className="text-[3.25rem] font-semibold leading-none tracking-tight">
              {value}
            </div>
            <p className="mt-4 max-w-[26ch] text-[0.9375rem] text-secondary">{label}</p>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function Stacks() {
  return (
    <Section label="Built on">
      <div className="grid gap-px overflow-hidden rounded-xl border border-line bg-line lg:grid-cols-3">
        {STACKS.map(([name, line], i) => (
          <Reveal key={name} delay={i * 90}>
            <div className="h-full bg-base p-8">
              <h3 className="text-[0.9375rem] font-semibold tracking-tight">{name}</h3>
              <p className="mt-3 text-[0.875rem] leading-relaxed text-secondary">{line}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function Lifecycle() {
  return (
    <Section label="The lifecycle">
      <Reveal>
        <h2 className="max-w-[24ch] text-headline font-semibold">
          Selling outright is one mode of seven.
        </h2>
      </Reveal>
      <div className="mt-12 overflow-hidden rounded-xl border border-line">
        {LIFECYCLE.map(([name, line, status], i) => (
          <Reveal key={name} delay={i * 55}>
            <div
              className={`flex flex-wrap items-baseline gap-x-5 gap-y-1 px-6 py-4 ${
                i ? "border-t border-hairline" : ""
              }`}
            >
              <span className="w-20 shrink-0 text-[0.9375rem] font-semibold">{name}</span>
              <span className="min-w-0 flex-1 text-[0.875rem] text-secondary">{line}</span>
              <span
                className={`rounded border px-2 py-0.5 text-[0.6875rem] uppercase tracking-[0.06em] ${
                  status === "built"
                    ? "border-good/40 text-good"
                    : "border-line text-faint"
                }`}
              >
                {status}
              </span>
            </div>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function Close({ onEnter }: { onEnter: () => void }) {
  return (
    <Section>
      <Reveal>
        <div className="flex flex-col items-start gap-10">
          <Mark size={44} />
          <h2 className="max-w-[17ch] text-headline font-semibold">
            Continuity, with an owner.
          </h2>
          <button
            onClick={onEnter}
            className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-base transition-colors hover:bg-white"
          >
            Open console
          </button>
        </div>
      </Reveal>
    </Section>
  );
}

function Footer({ onDocs }: { onDocs: () => void }) {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-content flex-col gap-4 px-6 py-10 sm:flex-row sm:items-center sm:justify-between">
        <Wordmark size={18} />
        <div className="flex flex-wrap gap-5 text-[0.75rem] text-faint">
          <button onClick={onDocs} className="hover:text-secondary">
            Docs
          </button>
          <a href="https://github.com/linoxbt/Succession" className="hover:text-secondary">
            GitHub
          </a>
          <span>All counterparties in the seeded memory are invented.</span>
        </div>
      </div>
    </footer>
  );
}

function Section({ label, children }: { label?: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-line/60">
      <div className="mx-auto max-w-content px-6 py-24 sm:py-28">
        {label ? (
          <Reveal>
            <p className="mb-12 text-[0.8125rem] font-medium uppercase tracking-[0.14em] text-faint">
              {label}
            </p>
          </Reveal>
        ) : null}
        {children}
      </div>
    </section>
  );
}
