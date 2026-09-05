/**
 * The shared vocabulary.
 *
 * Every export here keeps the exact name, props and behaviour it had before —
 * these are consumed across the wallet flow, the listing screens and the
 * walkthrough, and a rename would be a functional change dressed as a visual
 * one. What changed is entirely presentational.
 *
 * Two things the redesign did *not* discard, because they are semantic:
 *
 *   `Field` is still a definition-list row, label then value. A listing's
 *   figures are a schedule, and a schedule is a definition list. Turning them
 *   into cards would make each figure look like a product for sale.
 *
 *   `Hash` is still mono and still never anything else. A hash is evidence;
 *   it should read as a fingerprint, distinct from every other numeral.
 *
 * There is no `Card`, and no shadow in this file. Regions are separated by
 * hairlines and by space. Depth is what a marketing page uses to make a list
 * feel important; this page uses scale.
 */
import { useState } from "react";
import type { ReactNode } from "react";

import { MaskLine, Reveal, useMagnetic, useReveal } from "../motion";

/* -- structure ---------------------------------------------------------- */

export function Rule({ className = "" }: { className?: string }) {
  return <div className={`h-px w-full bg-hairline ${className}`} />;
}

/**
 * A titled region.
 *
 * The title is display type at section scale with a rule beneath it running
 * the full width — the masthead device of a broadsheet, where a heading owns
 * its column rather than floating above a box.
 */
export function Section({
  title,
  action,
  children,
  className = "",
  index,
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  /** Chapter number, rendered as an editorial marker beside the title. */
  index?: string;
}) {
  const ref = useReveal<HTMLElement>();
  return (
    <section ref={ref} className={`reveal ${className}`}>
      {title ? (
        <header className="mb-8 flex flex-wrap items-end justify-between gap-x-8 gap-y-4 border-b border-rule pb-4">
          <div className="flex items-baseline gap-5">
            {index ? <span className="chapter-mark">{index}</span> : null}
            <h2 className="display-type text-title text-ink">{title}</h2>
          </div>
          {action}
        </header>
      ) : null}
      {children}
    </section>
  );
}

/** One row of a schedule: label, then value. */
export function Field({
  label,
  children,
  emphasis = false,
}: {
  label: string;
  children: ReactNode;
  emphasis?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1 border-b border-hairline py-4 sm:flex-row sm:items-baseline sm:gap-10">
      <dt className="w-full shrink-0 font-mono text-label uppercase text-faint sm:w-72">
        {label}
      </dt>
      <dd
        className={`min-w-0 break-words ${
          emphasis ? "display-type text-figure text-ink" : "text-body text-ink"
        }`}
      >
        {children}
      </dd>
    </div>
  );
}

export function FieldList({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <dl className={`border-t border-hairline ${className}`}>{children}</dl>;
}

/* -- evidence ----------------------------------------------------------- */

/**
 * A hash or on-chain identifier.
 *
 * Only re-prefixes `0x` on something that is actually hex: a settlement
 * reference from the local backend looks like `local:9f3a…`, and rendering
 * that as `0xlocal:9f3a…` would invent a hex string that never existed.
 */
export function Hash({ value, chars = 6 }: { value: string; chars?: number }) {
  if (!value) return <span className="text-faint">—</span>;
  const hex = /^0x[0-9a-fA-F]+$/.test(value);
  const body = hex ? value.slice(2) : value;
  const short =
    body.length > chars * 2 ? `${body.slice(0, chars)}…${body.slice(-chars)}` : body;
  return (
    <span className="font-mono text-micro tnum text-ink" title={value}>
      {hex ? `0x${short}` : short}
    </span>
  );
}

/**
 * A hash shown in full, at size.
 *
 * This is the comparison the whole product turns on, so it is set large enough
 * to actually read and compare character by character — truncating it here
 * would undercut the only claim the page is making.
 */
export function FullHash({ value, tone = "neutral" }: { value: string; tone?: Tone }) {
  const colour =
    tone === "closed" ? "text-closed" : tone === "void" ? "text-void" : "text-ink";
  return (
    <span
      className={`block break-all font-mono text-micro leading-[1.7] tnum sm:text-micro ${colour}`}
    >
      {value || "—"}
    </span>
  );
}

export function Evidence({ children }: { children: ReactNode }) {
  return <div className="evidence">{children}</div>;
}

/* -- state -------------------------------------------------------------- */

export type Tone = "neutral" | "escrow" | "closed" | "void";

const TONES: Record<Tone, string> = {
  neutral: "border-rule text-muted",
  escrow: "border-escrow/40 text-escrow",
  closed: "border-closed/40 text-closed",
  void: "border-void/40 text-void",
};

/**
 * A state badge. Colour is never the sole signal — the caller passes the words
 * and the badge renders them alongside the colour.
 */
export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: Tone;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center gap-2 border px-3 py-1 font-mono text-label uppercase ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

/**
 * The hash-match mark. The one moment in the product where something resolves,
 * so it is the one place a transition is allowed to draw attention to itself.
 */
export function VerifyMark({
  matched,
  pulse = false,
}: {
  matched: boolean;
  pulse?: boolean;
}) {
  const label = matched ? "Hash verified" : "Hash mismatch";
  return (
    <span
      role="img"
      aria-label={label}
      className={`inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full border ${
        matched ? "border-closed text-closed" : "border-void text-void"
      } ${pulse ? "verify-pulse" : ""}`}
    >
      <svg viewBox="0 0 20 20" className="h-6 w-6" fill="none" aria-hidden="true">
        {matched ? (
          <path
            d="M4.5 10.5l3.5 3.5 7.5-8"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ) : (
          <path
            d="M5.5 5.5l9 9M14.5 5.5l-9 9"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        )}
      </svg>
    </span>
  );
}

/* -- controls ----------------------------------------------------------- */

/**
 * Buttons are typographic, not chrome.
 *
 * `primary` leans toward the pointer — a small magnetic offset, enough that the
 * control feels answerable without feeling like it is dodging the cursor. The
 * effect is skipped on coarse pointers, where there is no hover to respond to.
 */
export function Button({
  children,
  onClick,
  disabled,
  variant = "primary",
  size = "md",
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "ghost" | "quiet";
  size?: "sm" | "md";
  type?: "button" | "submit";
}) {
  const magnet = useMagnetic<HTMLButtonElement>(variant === "primary" ? 0.2 : 0);

  const variants = {
    primary:
      "bg-ink text-paper hover:bg-black border border-ink",
    ghost:
      "border border-rule text-ink hover:border-ink bg-transparent",
    quiet:
      "text-muted hover:text-ink border-0 px-0 link-underline",
  };
  const sizes = {
    sm: "px-5 py-2 text-micro",
    md: "px-8 py-3.5 text-micro",
  };

  return (
    <button
      ref={magnet}
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 font-mono uppercase tracking-[0.12em] transition-[background-color,border-color,color,transform] duration-500 ease-swift disabled:cursor-not-allowed disabled:opacity-35 ${
        variants[variant]
      } ${variant === "quiet" ? "" : sizes[size]}`}
    >
      {children}
    </button>
  );
}

/* -- tabular ------------------------------------------------------------ */

/**
 * A ledger, not a grid of cards.
 *
 * Rows are separated by hairlines and given real height, so a marketplace reads
 * as a schedule of holdings. Horizontally scrollable rather than collapsed on
 * narrow screens: a figure that has been hidden to fit is a figure a buyer
 * cannot check.
 */
export function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="rail -mx-6 overflow-x-auto px-6 sm:mx-0 sm:px-0">
      <table className="w-full min-w-[46rem] border-collapse text-left">
        <thead>
          <tr className="border-b border-rule">
            {head.map((h, i) => (
              <th
                key={i}
                scope="col"
                className="pb-4 pr-8 font-mono text-label uppercase font-normal text-faint"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function Td({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <td className={`py-6 pr-8 align-middle text-body ${className}`}>{children}</td>;
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="border-y border-rule py-24 text-center">
      <p className="mx-auto max-w-measure text-lede text-muted">{children}</p>
    </div>
  );
}

/**
 * A command the reader is meant to run, with a copy button.
 *
 * Used wherever the honest answer is "this happens on your machine, not here" —
 * a seller's Sibyl store and a buyer's import are both local files. The text
 * stays selectable so copying works even if the clipboard API is refused.
 */
export function Copyable({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="group relative border border-rule bg-shade/60">
      <pre className="rail overflow-x-auto px-6 py-5 font-mono text-micro leading-[1.9] text-ink">
        <code>{text}</code>
      </pre>
      <button
        onClick={() => {
          navigator.clipboard
            ?.writeText(text)
            .then(() => {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1600);
            })
            .catch(() => {
              /* select-and-copy still works; nothing to report */
            });
        }}
        className="absolute right-0 top-0 border-b border-l border-rule px-4 py-2 font-mono text-label uppercase text-faint transition-colors duration-400 hover:text-ink"
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

/**
 * An aside in the document's own voice — a marginal note, not a callout box.
 * Set against a rule on the leading edge rather than inside a tinted panel.
 */
export function Note({ children }: { children: ReactNode }) {
  return (
    <p className="mt-6 max-w-measure border-l border-rule pl-5 text-body leading-[1.7] text-muted">
      {children}
    </p>
  );
}

/**
 * An oversized figure with its label beneath — the unit the proof section is
 * built from. Display scale, because a number that matters should be read from
 * across the room.
 */
export function Figure({
  value,
  label,
  tone = "neutral",
}: {
  value: ReactNode;
  label: string;
  tone?: Tone;
}) {
  const colour =
    tone === "closed" ? "text-closed" : tone === "void" ? "text-void" : "";
  return (
    <div className="flex flex-col gap-3">
      <span className={`display-type text-display leading-none ${colour}`}>{value}</span>
      <span className="font-mono text-label uppercase text-faint">{label}</span>
    </div>
  );
}

/**
 * The opening of a console screen.
 *
 * Each destination starts the same way — a chapter mark, a display line, and an
 * optional standfirst — so moving between them feels like turning to a new page
 * of one document rather than loading a different application. The heading is
 * masked and rises on arrival; nothing else on the screen announces itself.
 */
export function PageHead({
  index,
  title,
  lede,
  action,
}: {
  index: string;
  title: string;
  lede?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header className="mb-beat border-b border-rule pb-10">
      <MaskLine>
        <p className="chapter-mark">{index}</p>
      </MaskLine>
      <div className="mt-8 flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
        <h1 className="display-type max-w-[16ch] text-display text-ink">
          <MaskLine index={1}>{title}</MaskLine>
        </h1>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      {lede ? (
        <Reveal index={2}>
          <p className="mt-10 max-w-measure text-lede text-muted">{lede}</p>
        </Reveal>
      ) : null}
    </header>
  );
}
