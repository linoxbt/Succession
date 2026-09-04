/**
 * The shared vocabulary of the console.
 *
 * Dense tables, hairline dividers, one accent reserved for state. There is no
 * Card component and no shadow anywhere: depth is what a marketing page uses to
 * make a list feel important, and this surface is for people who already know
 * what they are looking at.
 */
import type { ReactNode } from "react";

export function Rule({ className = "" }: { className?: string }) {
  return <div className={`h-px w-full bg-line ${className}`} />;
}

export function Mono({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <span className={`font-mono text-[0.8125rem] tnum ${className}`}>{children}</span>;
}

/** A hash or reference, shortened, with the full value on hover.
 *
 * Only re-prefixes `0x` on something that is actually hex. A settlement
 * reference from the local backend looks like `local:9f3a…`, and rendering
 * that as `0xlocal:9f3a…` invents a hex string that never existed. */
export function Hash({ value, chars = 8 }: { value: string; chars?: number }) {
  if (!value) return <span className="text-faint">—</span>;
  const hex = /^0x[0-9a-fA-F]+$/.test(value);
  const body = hex ? value.slice(2) : value;
  const short =
    body.length > chars * 2 ? `${body.slice(0, chars)}…${body.slice(-chars)}` : body;
  return (
    <span className="font-mono text-[0.8125rem] tnum" title={value}>
      {hex ? `0x${short}` : short}
    </span>
  );
}

export type Tone = "neutral" | "accent" | "good" | "bad" | "warn";

const TONES: Record<Tone, string> = {
  neutral: "border-line text-secondary",
  accent: "border-accent/40 bg-accent/10 text-accent",
  good: "border-good/40 bg-good/10 text-good",
  bad: "border-bad/40 bg-bad/10 text-bad",
  warn: "border-warn/40 bg-warn/10 text-warn",
};

/** Colour never carries state alone — every badge also says what it means. */
export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[0.6875rem] font-medium uppercase tracking-[0.06em] ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

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
  variant?: "primary" | "ghost" | "danger";
  size?: "sm" | "md";
  type?: "button" | "submit";
}) {
  const variants = {
    primary: "bg-primary text-base hover:bg-white",
    ghost: "border border-line text-primary hover:border-secondary",
    danger: "border border-bad/50 text-bad hover:bg-bad/10",
  };
  const sizes = { sm: "px-3 py-1.5 text-[0.8125rem]", md: "px-4 py-2 text-sm" };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${variants[variant]} ${sizes[size]}`}
    >
      {children}
    </button>
  );
}

/** A KPI. The number leads; the label explains it afterwards, not before. */
export function Stat({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: Tone;
}) {
  const accent = {
    neutral: "text-primary",
    accent: "text-accent",
    good: "text-good",
    bad: "text-bad",
    warn: "text-warn",
  }[tone];
  return (
    <div className="px-5 py-4">
      <div className={`tnum text-[1.75rem] font-semibold leading-none tracking-tight ${accent}`}>
        {value}
      </div>
      <div className="mt-2 text-[0.8125rem] text-secondary">{label}</div>
      {sub ? <div className="mt-0.5 text-xs text-faint">{sub}</div> : null}
    </div>
  );
}

export function StatRow({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-2 divide-x divide-line border-y border-line md:grid-cols-4">
      {children}
    </div>
  );
}

export function Panel({
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
    <section className={`rounded-lg border border-line bg-panel ${className}`}>
      {title ? (
        <header className="flex items-center justify-between gap-4 border-b border-line px-5 py-3">
          <h2 className="text-[0.8125rem] font-semibold tracking-tight text-primary">{title}</h2>
          {action}
        </header>
      ) : null}
      {children}
    </section>
  );
}

export function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[42rem] border-collapse text-left">
        <thead>
          <tr className="border-b border-line">
            {head.map((h) => (
              <th
                key={h}
                className="px-5 py-2.5 text-[0.6875rem] font-medium uppercase tracking-[0.08em] text-faint"
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
  return <td className={`px-5 py-3 text-[0.8125rem] ${className}`}>{children}</td>;
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-b border-hairline px-5 py-3 sm:flex-row sm:items-baseline sm:gap-6">
      <dt className="w-56 shrink-0 text-[0.8125rem] text-secondary">{label}</dt>
      <dd className="min-w-0 break-words text-[0.8125rem] text-primary">{children}</dd>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="px-5 py-10 text-center text-[0.8125rem] text-faint">{children}</div>;
}

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: T; label: string; count?: number }[];
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="flex gap-1 border-b border-line px-2" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={`relative px-3 py-2.5 text-[0.8125rem] font-medium transition-colors ${
            active === tab.id ? "text-primary" : "text-faint hover:text-secondary"
          }`}
        >
          {tab.label}
          {tab.count !== undefined ? (
            <span className="ml-1.5 tnum text-faint">{tab.count}</span>
          ) : null}
          {active === tab.id ? (
            <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-accent" />
          ) : null}
        </button>
      ))}
    </div>
  );
}
