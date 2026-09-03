/**
 * The shared vocabulary of the interface.
 *
 * The reference point is a private M&A data room and an escrow closing
 * statement, so the primitives are a definition list, a hairline rule, and a
 * monospaced evidence field — not cards, badges-as-decoration, or shadows.
 * There is deliberately no Card component: giving the layout one would make
 * reaching for a product grid the path of least resistance.
 */
import type { ReactNode } from "react";

export function Rule({ className = "" }: { className?: string }) {
  // A hairline, never a shadow. Depth belongs to shopping carts.
  return <hr className={`border-0 border-t border-rule ${className}`} />;
}

export function Section({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={className}>
      {title ? (
        <h2 className="mb-4 font-sans text-xs font-semibold uppercase tracking-[0.14em] text-ink/55">
          {title}
        </h2>
      ) : null}
      {children}
    </section>
  );
}

/**
 * Label above value, stacked — the data-room teaser shape. On wider screens the
 * label sits in a fixed column; on narrow ones it stacks, which is how the
 * definition-list structure survives mobile rather than collapsing into prose.
 */
export function DefinitionList({ children }: { children: ReactNode }) {
  return <dl className="divide-y divide-rule/60">{children}</dl>;
}

export function Definition({
  label,
  children,
  mono = false,
  hint,
}: {
  label: string;
  children: ReactNode;
  mono?: boolean;
  hint?: string;
}) {
  return (
    <div className="grid gap-1 py-3 sm:grid-cols-[15rem_1fr] sm:gap-6">
      <dt className="font-sans text-sm text-ink/60">
        {label}
        {hint ? <span className="mt-0.5 block text-xs text-ink/45">{hint}</span> : null}
      </dt>
      <dd
        className={
          mono
            ? "break-all font-mono text-[0.8125rem] leading-relaxed text-ink"
            : "font-sans text-[0.9375rem] text-ink"
        }
      >
        {children}
      </dd>
    </div>
  );
}

/** A headline figure: serif, because this is the register of a stock certificate. */
export function Figure({ children }: { children: ReactNode }) {
  return <span className="font-serif text-2xl leading-none">{children}</span>;
}

export type StateTone = "neutral" | "escrow" | "closed" | "void";

const TONE: Record<StateTone, string> = {
  neutral: "border-ink/25 text-ink/70",
  escrow: "border-escrow text-escrow",
  closed: "border-closed text-closed",
  void: "border-void text-void",
};

/**
 * Colour encodes transaction state and is never the only signal carrying it —
 * every badge states its meaning in words. "Escrow: funds held", not a blue dot.
 */
export function StateBadge({ tone, children }: { tone: StateTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-2 border px-2.5 py-1 font-sans text-xs font-medium uppercase tracking-[0.08em] ${TONE[tone]}`}
    >
      {children}
    </span>
  );
}

export function Button({
  children,
  onClick,
  disabled,
  tone = "primary",
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  tone?: "primary" | "quiet";
  type?: "button" | "submit";
}) {
  const base =
    "inline-flex items-center justify-center border px-5 py-2.5 font-sans text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40";
  const tones = {
    primary: "border-ink bg-ink text-vellum hover:bg-ink/85",
    quiet: "border-ink/30 bg-transparent text-ink hover:border-ink",
  };
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`${base} ${tones[tone]}`}>
      {children}
    </button>
  );
}

/**
 * The evidence strip: the hash commitment and the on-chain references. The one
 * element that should feel most official, set apart with a hairline border and
 * never a shadow.
 */
export function EvidenceStrip({ children }: { children: ReactNode }) {
  return (
    <div className="border-y border-rule py-1">
      <DefinitionList>{children}</DefinitionList>
    </div>
  );
}

export function Notice({ children, tone = "neutral" }: { children: ReactNode; tone?: StateTone }) {
  const border = { neutral: "border-rule", escrow: "border-escrow", closed: "border-closed", void: "border-void" };
  return (
    <p className={`border-l-2 ${border[tone]} py-1 pl-4 font-sans text-sm text-ink/70`}>
      {children}
    </p>
  );
}
