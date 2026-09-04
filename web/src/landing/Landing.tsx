/**
 * The landing page.
 *
 * Statements, not paragraphs. Every line here is a claim the product can be
 * held to, and nothing on the page explains itself twice. The scale does the
 * persuading: enormous type, one accent, and a great deal of air.
 */
import { Rule } from "../ui";

const MECHANISM = [
  ["Export", "The agent's whole memory becomes one signed, portable package."],
  ["Commit", "A Merkle root goes on Base before a buyer exists."],
  ["Settle", "Payment, identity and the seal move in one transaction."],
  ["Verify", "The buyer re-hashes their own store. Mismatch refunds."],
];

const NUMBERS = [
  ["5", "tiers of memory transferred"],
  ["1", "transaction settles all three effects"],
  ["0", "ways to keep operating a sold agent"],
];

export function Landing({ onEnter }: { onEnter: () => void }) {
  return (
    <div className="min-h-screen bg-base">
      <header className="mx-auto flex max-w-content items-center justify-between px-6 py-6">
        <span className="text-[0.9375rem] font-semibold tracking-tight">Succession</span>
        <nav className="flex items-center gap-6 text-[0.8125rem] text-secondary">
          <a href="https://github.com/linoxbt/Succession" className="hover:text-primary">
            GitHub
          </a>
          <button
            onClick={onEnter}
            className="rounded-md bg-primary px-3.5 py-1.5 font-medium text-base transition-colors hover:bg-white"
          >
            Open console
          </button>
        </nav>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-content px-6 pb-24 pt-16 sm:pt-28">
        <p className="mb-6 text-[0.8125rem] font-medium uppercase tracking-[0.14em] text-accent">
          The property layer for agent memory
        </p>
        <h1 className="max-w-[16ch] animate-rise text-display font-semibold">
          The code is replaceable. The memory is not.
        </h1>
        <p className="mt-8 max-w-[46ch] text-lede text-secondary">
          Succession makes an agent's accumulated memory a transferable asset —
          sold, verified, and settled on chain.
        </p>
        <div className="mt-10 flex flex-wrap items-center gap-3">
          <button
            onClick={onEnter}
            className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-base transition-colors hover:bg-white"
          >
            Open console
          </button>
          <a
            href="https://github.com/linoxbt/Succession"
            className="rounded-md border border-line px-5 py-2.5 text-sm font-medium text-primary transition-colors hover:border-secondary"
          >
            Read the spec
          </a>
        </div>
      </section>

      <Rule />

      {/* The one-sentence thesis */}
      <section className="mx-auto max-w-content px-6 py-24">
        <h2 className="max-w-[22ch] text-headline font-semibold">
          The model is the employee. The memory is the customer book.
        </h2>
        <p className="mt-6 max-w-[52ch] text-lede text-secondary">
          Succession does not sell the employee.
        </p>
      </section>

      <Rule />

      {/* Mechanism */}
      <section className="mx-auto max-w-content px-6 py-24">
        <p className="mb-12 text-[0.8125rem] font-medium uppercase tracking-[0.14em] text-faint">
          The mechanism
        </p>
        <div className="grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {MECHANISM.map(([step, line], i) => (
            <div key={step} className="bg-base p-7">
              <span className="tnum text-[0.75rem] text-faint">0{i + 1}</span>
              <h3 className="mt-4 text-lg font-semibold tracking-tight">{step}</h3>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-secondary">{line}</p>
            </div>
          ))}
        </div>
      </section>

      <Rule />

      {/* Numbers */}
      <section className="mx-auto max-w-content px-6 py-24">
        <div className="grid gap-12 sm:grid-cols-3">
          {NUMBERS.map(([n, label]) => (
            <div key={label}>
              <div className="tnum text-[3.5rem] font-semibold leading-none tracking-tight">
                {n}
              </div>
              <p className="mt-4 max-w-[24ch] text-[0.9375rem] text-secondary">{label}</p>
            </div>
          ))}
        </div>
      </section>

      <Rule />

      {/* Proof */}
      <section className="mx-auto max-w-content px-6 py-24">
        <h2 className="max-w-[20ch] text-headline font-semibold">
          Anyone can claim a transfer happened.
        </h2>
        <p className="mt-6 max-w-[54ch] text-lede text-secondary">
          The buyer re-hashes their own store and compares it to a root committed
          before they existed. Escrow releases on a match and refunds on anything
          else.
        </p>
        <div className="mt-12 grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-3">
          {[
            ["Base", "Escrow, ERC-8004 identity transfer, and the seal — one transaction."],
            ["Virtuals", "ACP job history a buyer can verify by on-chain job id."],
            ["Sibyl Memory", "Five tiers exported, re-keyed, and re-hashed on arrival."],
          ].map(([name, line]) => (
            <div key={name} className="bg-base p-7">
              <h3 className="text-[0.9375rem] font-semibold tracking-tight">{name}</h3>
              <p className="mt-2 text-[0.875rem] leading-relaxed text-secondary">{line}</p>
            </div>
          ))}
        </div>
      </section>

      <Rule />

      {/* Close */}
      <section className="mx-auto max-w-content px-6 py-28">
        <h2 className="max-w-[18ch] text-headline font-semibold">
          Continuity, with an owner.
        </h2>
        <button
          onClick={onEnter}
          className="mt-10 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-base transition-colors hover:bg-white"
        >
          Open console
        </button>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-content flex-col gap-2 px-6 py-8 text-[0.75rem] text-faint sm:flex-row sm:items-center sm:justify-between">
          <span>Succession — Sibyl Labs Hackathon, 2026.</span>
          <span>All counterparties in the seeded memory are invented.</span>
        </div>
      </footer>
    </div>
  );
}
