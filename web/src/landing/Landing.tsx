/**
 * The landing page, in the same register as the console.
 *
 * The brief's rule about motion is absolute — "exactly one animated moment
 * beyond focus states", and that moment is the hash-match checkmark on the
 * confirmation screen. So there is no scroll reveal here, no counting-up
 * figures, and no hover lift: a page whose numbers animate into place is asking
 * to be admired, and this one is asking to be checked.
 *
 * What replaces motion is typography. Spectral carries the claims at the scale
 * a closing document gives its headings; everything else is quiet. The two
 * diagrams draw the actual mechanism rather than decorating around it, which is
 * why they survive the cut where the animation did not.
 */
import type { ReactNode } from "react";
import { Mark, Wordmark } from "../brand/Logo";
import { HashVerification, TransferDiagram } from "./visuals";

const MECHANISM: [string, string][] = [
  ["Export", "The agent's whole memory becomes one signed, portable package."],
  ["Commit", "A Merkle root goes on Base before a buyer exists."],
  ["Settle", "Payment, identity and the seal move in one transaction."],
  ["Verify", "The buyer re-hashes their own store. Mismatch refunds."],
];

const STACKS: [string, string][] = [
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

export function Landing({ onEnter, onDocs }: { onEnter: () => void; onDocs: () => void }) {
  return (
    <div className="min-h-screen bg-vellum">
      <Header onEnter={onEnter} onDocs={onDocs} />
      <Hero onEnter={onEnter} onDocs={onDocs} />
      <Thesis />
      <Mechanism />
      <Verification />
      <Stacks />
      <Lifecycle />
      <Close onEnter={onEnter} />
      <Footer onDocs={onDocs} />
    </div>
  );
}

function Header({ onEnter, onDocs }: { onEnter: () => void; onDocs: () => void }) {
  return (
    <header className="border-b border-rule">
      <div className="mx-auto flex max-w-document items-center justify-between px-6 py-5">
        <Wordmark size={22} />
        <nav className="flex items-center gap-5">
          <button onClick={onDocs} className="text-[0.875rem] text-muted hover:text-ink">
            Docs
          </button>
          <a
            href="https://github.com/linoxbt/Succession"
            className="hidden text-[0.875rem] text-muted hover:text-ink sm:block"
          >
            GitHub
          </a>
          <button
            onClick={onEnter}
            className="bg-ink px-4 py-2 text-[0.875rem] font-medium text-vellum transition-colors hover:bg-black"
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
    <section>
      <div className="mx-auto max-w-document px-6 pb-20 pt-16 sm:pt-24">
        <p className="mb-6 text-[0.8125rem] uppercase tracking-[0.14em] text-muted">
          The property layer for agent memory
        </p>
        <h1 className="max-w-[17ch] font-serif text-document text-ink">
          The code is replaceable. The memory is not.
        </h1>
        <p className="mt-7 max-w-column text-[1.0625rem] leading-relaxed text-muted">
          Succession turns an agent's accumulated memory into an asset that can be
          sold, verified, and settled on chain.
        </p>
        <div className="mt-9 flex flex-wrap items-center gap-4">
          <button
            onClick={onEnter}
            className="bg-ink px-5 py-2.5 text-[0.875rem] font-medium text-vellum transition-colors hover:bg-black"
          >
            Open console
          </button>
          <button
            onClick={onDocs}
            className="border border-rule px-5 py-2.5 text-[0.875rem] font-medium text-ink transition-colors hover:border-ink"
          >
            Read the docs
          </button>
        </div>
      </div>
    </section>
  );
}

function Thesis() {
  return (
    <Band>
      <h2 className="max-w-[24ch] font-serif text-heading text-ink">
        The model is the employee. The memory is the customer book.
      </h2>
      <p className="mt-5 max-w-column text-[1.0625rem] leading-relaxed text-muted">
        Succession does not sell the employee.
      </p>
    </Band>
  );
}

function Mechanism() {
  return (
    <Band label="The mechanism">
      <TransferDiagram />
      <dl className="mt-12 border-t border-hairline">
        {MECHANISM.map(([step, line], i) => (
          <div
            key={step}
            className="flex flex-col gap-1 border-b border-hairline py-4 sm:flex-row sm:gap-6"
          >
            <dt className="flex w-full shrink-0 items-baseline gap-3 sm:w-64">
              <span className="tnum text-[0.75rem] text-faint">0{i + 1}</span>
              <span className="font-serif text-[1.0625rem] text-ink">{step}</span>
            </dt>
            <dd className="text-[0.9375rem] leading-relaxed text-muted">{line}</dd>
          </div>
        ))}
      </dl>
    </Band>
  );
}

function Verification() {
  return (
    <Band label="Proof">
      <h2 className="max-w-[22ch] font-serif text-heading text-ink">
        Anyone can claim a transfer happened.
      </h2>
      <p className="mt-5 max-w-column text-[1.0625rem] leading-relaxed text-muted">
        The buyer re-hashes their own store and compares it to a root committed
        before they existed. Escrow releases on a match and refunds on anything
        else.
      </p>
      <div className="mt-10">
        <HashVerification />
      </div>
    </Band>
  );
}

function Stacks() {
  return (
    <Band label="Built on">
      <dl className="border-t border-hairline">
        {STACKS.map(([name, line]) => (
          <div
            key={name}
            className="flex flex-col gap-1 border-b border-hairline py-4 sm:flex-row sm:gap-6"
          >
            <dt className="w-full shrink-0 font-serif text-[1.0625rem] text-ink sm:w-64">
              {name}
            </dt>
            <dd className="text-[0.9375rem] leading-relaxed text-muted">{line}</dd>
          </div>
        ))}
      </dl>
    </Band>
  );
}

function Lifecycle() {
  return (
    <Band label="The lifecycle">
      <h2 className="max-w-[26ch] font-serif text-heading text-ink">
        Selling outright is one mode of seven.
      </h2>
      <dl className="mt-10 border-t border-hairline">
        {LIFECYCLE.map(([name, line, status]) => (
          <div
            key={name}
            className="flex flex-wrap items-baseline gap-x-6 gap-y-1 border-b border-hairline py-3"
          >
            <dt className="w-24 shrink-0 font-serif text-[1.0625rem] text-ink">{name}</dt>
            <dd className="min-w-0 flex-1 text-[0.9375rem] text-muted">{line}</dd>
            {/* Colour is paired with the word, never standing in for it. */}
            <span
              className={`border px-2 py-0.5 text-[0.75rem] ${
                status === "built" ? "border-closed/35 text-closed" : "border-rule text-faint"
              }`}
            >
              {status}
            </span>
          </div>
        ))}
      </dl>
    </Band>
  );
}

function Close({ onEnter }: { onEnter: () => void }) {
  return (
    <Band>
      <div className="flex flex-col items-start gap-8">
        <Mark size={40} />
        <h2 className="max-w-[19ch] font-serif text-heading text-ink">
          Continuity, with an owner.
        </h2>
        <button
          onClick={onEnter}
          className="bg-ink px-5 py-2.5 text-[0.875rem] font-medium text-vellum transition-colors hover:bg-black"
        >
          Open console
        </button>
      </div>
    </Band>
  );
}

function Footer({ onDocs }: { onDocs: () => void }) {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto flex max-w-document flex-col gap-4 px-6 py-10 sm:flex-row sm:items-center sm:justify-between">
        <Wordmark size={18} />
        <div className="flex flex-wrap gap-5 text-[0.8125rem] text-faint">
          <button onClick={onDocs} className="hover:text-muted">
            Docs
          </button>
          <a href="https://github.com/linoxbt/Succession" className="hover:text-muted">
            GitHub
          </a>
          <span>All counterparties in the seeded memory are invented.</span>
        </div>
      </div>
    </footer>
  );
}

function Band({ label, children }: { label?: string; children: ReactNode }) {
  return (
    <section className="border-t border-rule">
      <div className="mx-auto max-w-document px-6 py-16 sm:py-20">
        {label ? (
          <p className="mb-10 text-[0.8125rem] uppercase tracking-[0.12em] text-faint">{label}</p>
        ) : null}
        {children}
      </div>
    </section>
  );
}
