/**
 * The two chart forms this product actually needs.
 *
 * Deliberately two and not a library. With a handful of listings, most chart
 * types would be decoration over a table that already reads better — the honest
 * forms here are a stat tile (a number is the right form for a single
 * magnitude) and a horizontal bar for the one place there is genuinely a
 * distribution to see: a listing's five valuation factors.
 *
 * Specs are fixed: bars cap at 24px and carry a 4px rounded data-end square at
 * the baseline, gridlines are hairline and recessive, and text never wears the
 * data colour — identity comes from the mark beside the label, never from
 * colouring the label itself.
 */
import type { ReactNode } from "react";

/** Compact a magnitude the way a KPI should read: 1,284 · 12.9K · $4.2M. */
export function compact(value: number, prefix = ""): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${prefix}${(value / 1_000_000).toFixed(1)}M`;
  if (abs >= 10_000) return `${prefix}${(value / 1_000).toFixed(1)}K`;
  return `${prefix}${value.toLocaleString("en-US")}`;
}

/**
 * The single number a view leads with. Exactly one per view.
 */
export function Hero({
  label,
  value,
  sub,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
}) {
  return (
    <div className="px-6 py-6">
      <p className="text-[0.8125rem] text-secondary">{label}</p>
      <p className="tnum mt-2 text-[3rem] font-semibold leading-none tracking-tight">
        {value}
      </p>
      {sub ? <p className="mt-3 text-[0.8125rem] text-faint">{sub}</p> : null}
    </div>
  );
}

/**
 * A KPI tile: label, value, and an optional delta against a named period.
 *
 * The delta's colour is direction × whether up is good, which is why
 * `upIsGood` is explicit rather than assumed — for "stale listings", up is bad.
 */
export function Tile({
  label,
  value,
  delta,
  period,
  upIsGood = true,
  sub,
}: {
  label: string;
  value: ReactNode;
  delta?: number;
  period?: string;
  upIsGood?: boolean;
  sub?: string;
}) {
  const good = delta === undefined ? null : delta === 0 ? null : delta > 0 === upIsGood;
  return (
    <div className="px-5 py-4">
      <p className="text-[0.8125rem] text-secondary">{label}</p>
      <p className="tnum mt-2 text-[1.625rem] font-semibold leading-none tracking-tight">
        {value}
      </p>
      <div className="mt-2 flex items-baseline gap-2 text-xs">
        {delta !== undefined ? (
          <span
            className={
              good === null ? "text-faint" : good ? "text-good" : "text-bad"
            }
          >
            {delta > 0 ? "+" : ""}
            {delta}
            {period ? <span className="text-faint"> vs {period}</span> : null}
          </span>
        ) : sub ? (
          <span className="text-faint">{sub}</span>
        ) : null}
      </div>
    </div>
  );
}

export interface BarDatum {
  label: string;
  value: number;
  note?: string;
}

/**
 * Horizontal bars, one series, single hue.
 *
 * One series needs no legend — the title already names what is plotted. Values
 * ride the bar ends rather than sitting on a second axis, and the reference
 * line at 1.0 is what makes a multiplier readable: it is the difference between
 * a factor that adds value and one that subtracts it.
 */
export function FactorBars({
  data,
  reference,
  max,
}: {
  data: BarDatum[];
  reference?: number;
  max?: number;
}) {
  const ceiling = max ?? Math.max(...data.map((d) => d.value), reference ?? 0) * 1.12;
  const pct = (v: number) => `${Math.max((v / ceiling) * 100, 0.6)}%`;

  return (
    <div className="px-5 py-4">
      <div className="relative space-y-2.5">
        {reference !== undefined ? (
          <div
            className="pointer-events-none absolute inset-y-0 z-10 border-l border-dashed border-line"
            style={{ left: `calc(11rem + ${(reference / ceiling) * 100}% * 0.62)` }}
            aria-hidden
          />
        ) : null}
        {data.map((d) => (
          <div key={d.label} className="group flex items-center gap-3" title={d.note}>
            <span className="w-44 shrink-0 truncate font-mono text-[0.75rem] text-secondary">
              {d.label}
            </span>
            <span className="relative h-4 flex-1 rounded-sm bg-hairline/60">
              <span
                className="absolute inset-y-0 left-0 rounded-r-[4px] bg-accent transition-[width] duration-700 group-hover:bg-accent/80"
                style={{ width: pct(d.value) }}
              />
            </span>
            <span className="tnum w-12 shrink-0 text-right text-[0.75rem] text-primary">
              {d.value.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
      {reference !== undefined ? (
        <p className="mt-4 text-xs text-faint">
          Dashed line marks {reference.toFixed(1)} — factors left of it reduce the
          valuation, right of it raise it.
        </p>
      ) : null}
    </div>
  );
}

/**
 * Counts by category, as a proportion strip.
 *
 * A pie would be worse at exactly the job this does: comparing a handful of
 * unequal parts. Segments are separated by a 2px surface gap rather than a
 * stroke, so neighbours read as distinct without extra ink.
 */
export function Distribution({
  data,
  total,
}: {
  data: { label: string; value: number }[];
  total: number;
}) {
  const shades = ["bg-accent", "bg-accent/75", "bg-accent/55", "bg-accent/40", "bg-accent/28", "bg-accent/18"];
  return (
    <div className="px-5 py-4">
      <div className="flex h-3 w-full gap-[2px] overflow-hidden rounded-sm">
        {data.map((d, i) => (
          <span
            key={d.label}
            className={`${shades[i % shades.length]} h-full`}
            style={{ width: `${(d.value / total) * 100}%` }}
            title={`${d.label}: ${d.value}`}
          />
        ))}
      </div>
      <ul className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1.5 sm:grid-cols-3">
        {data.map((d, i) => (
          <li key={d.label} className="flex items-center gap-2 text-xs">
            <span className={`h-2 w-2 shrink-0 rounded-sm ${shades[i % shades.length]}`} aria-hidden />
            <span className="truncate text-secondary">{d.label}</span>
            <span className="tnum ml-auto text-faint">{d.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
