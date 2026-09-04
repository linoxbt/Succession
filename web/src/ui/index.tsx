/**
 * The shared vocabulary, per Part 9's brief.
 *
 * The load-bearing primitive here is `Field` — a definition list row, label
 * then value. The brief is explicit that a listing's stats are "laid out as a
 * short definition list — label, then value, stacked — never as cards", and
 * that is not a stylistic preference: a card is a container that makes its
 * contents look like a product for sale, and this surface is a data room where
 * the reader already knows what they are looking at.
 *
 * So there is no `Card`, and no shadow anywhere in this file. Regions are
 * separated by hairline rules. Depth is what a marketing page uses to make a
 * list feel important.
 *
 * Colour appears only where a transaction has a state. Every coloured element
 * is paired with a text label, because colour is never the sole signal for
 * state — "Escrow: funds held", not a blue dot.
 */
import type { ReactNode } from "react";

/* -- structure ---------------------------------------------------------- */

export function Rule({ className = "" }: { className?: string }) {
  return <div className={`h-px w-full bg-hairline ${className}`} />;
}

/** A titled region. A heading and a rule — not a container with edges. */
export function Section({
  title,
  action,
  children,
  className = "",
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={className}>
      {title ? (
        <header className="flex flex-wrap items-baseline justify-between gap-3 border-b border-rule pb-2">
          <h2 className="font-serif text-heading text-ink">{title}</h2>
          {action}
        </header>
      ) : null}
      {children}
    </section>
  );
}

/**
 * One row of a definition list: label, then value.
 *
 * Collapses to a single readable column on mobile without losing the
 * label/value structure — the label sits above its value rather than being
 * dropped or truncated.
 */
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
    <div className="flex flex-col gap-0.5 border-b border-hairline py-2.5 sm:flex-row sm:items-baseline sm:gap-6">
      <dt className="w-full shrink-0 text-[0.8125rem] text-muted sm:w-64">{label}</dt>
      <dd
        className={`min-w-0 break-words ${
          emphasis ? "font-serif text-figure text-ink" : "text-[0.9375rem] text-ink"
        }`}
      >
        {children}
      </dd>
    </div>
  );
}

export function FieldList({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <dl className={`border-t border-hairline ${className}`}>{children}</dl>;
}

/* -- evidence ----------------------------------------------------------- */

/**
 * A hash or on-chain identifier. Mono, and only ever mono.
 *
 * Only re-prefixes `0x` on something that is actually hex: a settlement
 * reference from the local backend looks like `local:9f3a…`, and rendering
 * that as `0xlocal:9f3a…` invents a hex string that never existed.
 */
export function Hash({ value, chars = 6 }: { value: string; chars?: number }) {
  if (!value) return <span className="text-faint">—</span>;
  const hex = /^0x[0-9a-fA-F]+$/.test(value);
  const body = hex ? value.slice(2) : value;
  const short =
    body.length > chars * 2 ? `${body.slice(0, chars)}…${body.slice(-chars)}` : body;
  return (
    <span className="font-mono text-[0.8125rem] tnum text-ink" title={value}>
      {hex ? `0x${short}` : short}
    </span>
  );
}

/** A hash shown in full, for the comparison screen where truncation would
 *  undercut the whole point of showing it. */
export function FullHash({ value, tone = "neutral" }: { value: string; tone?: Tone }) {
  const colour =
    tone === "closed" ? "text-closed" : tone === "void" ? "text-void" : "text-ink";
  return (
    <span className={`block break-all font-mono text-[0.8125rem] leading-relaxed tnum ${colour}`}>
      {value || "—"}
    </span>
  );
}

/**
 * The "verified on-chain" strip. Hairline border, never a shadow — the single
 * element on the listing page that should feel most official.
 */
export function Evidence({ children }: { children: ReactNode }) {
  return <div className="evidence">{children}</div>;
}

/* -- state -------------------------------------------------------------- */

export type Tone = "neutral" | "escrow" | "closed" | "void";

const TONES: Record<Tone, string> = {
  neutral: "border-rule text-muted",
  escrow: "border-escrow/35 text-escrow",
  closed: "border-closed/35 text-closed",
  void: "border-void/35 text-void",
};

/**
 * A state badge. Colour is never the sole signal — the caller passes the words
 * ("Escrow: funds held"), and the badge renders them alongside the colour.
 */
export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 border px-2 py-0.5 text-[0.75rem] tracking-[0.02em] ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

/**
 * The hash-match checkmark. The one animated moment in the product.
 *
 * `pulse` is passed only at the instant verification completes, never on a
 * re-render of an already-settled transaction — an animation that replays on
 * every reload is decoration.
 */
export function VerifyMark({ matched, pulse = false }: { matched: boolean; pulse?: boolean }) {
  const label = matched ? "Hash verified" : "Hash mismatch";
  return (
    <span
      role="img"
      aria-label={label}
      className={`inline-flex h-7 w-7 items-center justify-center rounded-full border ${
        matched ? "border-closed text-closed" : "border-void text-void"
      } ${pulse ? "verify-pulse" : ""}`}
    >
      <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" aria-hidden="true">
        {matched ? (
          <path
            d="M4.5 10.5l3.5 3.5 7.5-8"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ) : (
          <path
            d="M5.5 5.5l9 9M14.5 5.5l-9 9"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        )}
      </svg>
    </span>
  );
}

/* -- controls ----------------------------------------------------------- */

/**
 * Buttons are typographic, not chrome. `primary` is the one filled control on
 * a screen, and there is at most one — a closing document has a single place
 * you sign.
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
  const variants = {
    primary: "bg-ink text-vellum hover:bg-black",
    ghost: "border border-rule text-ink hover:border-ink",
    quiet: "text-muted underline underline-offset-4 hover:text-ink",
  };
  const sizes = { sm: "px-3 py-1.5 text-[0.8125rem]", md: "px-5 py-2.5 text-[0.875rem]" };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${variants[variant]} ${sizes[size]}`}
    >
      {children}
    </button>
  );
}

/* -- tables ------------------------------------------------------------- */

export function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[40rem] border-collapse text-left">
        <thead>
          <tr className="border-b border-rule">
            {head.map((h) => (
              <th
                key={h}
                className="py-2 pr-6 text-[0.75rem] font-medium uppercase tracking-[0.06em] text-faint"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-hairline">{children}</tbody>
      </table>
    </div>
  );
}

export function Td({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <td className={`py-2.5 pr-6 text-[0.875rem] align-top ${className}`}>{children}</td>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-10 text-center text-[0.875rem] text-faint">{children}</div>;
}

/** A short note in the document's own voice — formal, precise, not a callout box. */
export function Note({ children }: { children: ReactNode }) {
  return (
    <p className="max-w-column text-[0.8125rem] leading-relaxed text-muted">{children}</p>
  );
}
