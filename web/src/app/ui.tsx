/**
 * Console primitives.
 *
 * Separate from `../ui` for one reason: two of that module's exports, `Button`
 * and `Figure`, are rendered by the marketing pages. Restructuring them to suit
 * a dense application screen would change a page that is explicitly out of
 * scope, so anything needing a different shape is built here instead. Colour is
 * not the reason — the palette is scoped by an attribute on the root element,
 * so every shared component already re-tints correctly inside the console.
 *
 * What the console was missing before this file: a panel, tabs, a disclosure,
 * a stepper, text and select inputs, a slider, and a loading state that is not
 * the string "Reading the contract."
 */
import {
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { useCursorState } from "../motion";

// --- surface -------------------------------------------------------------

/**
 * A panel. The marketing pages have no cards by design, and that discipline is
 * right for an argument read top to bottom; a console is scanned, and a scanned
 * screen needs bounded regions. The elevation is one step, never two: a panel
 * inside a panel reads as a mistake.
 */
export function Panel({
  children,
  className = "",
  as: Tag = "div",
  interactive = false,
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "article" | "section";
  interactive?: boolean;
}) {
  return (
    <Tag
      className={`rounded-sm border border-hairline bg-shade/40 ${
        interactive
          ? "transition-colors duration-200 ease-swift hover:border-rule"
          : ""
      } ${className}`}
    >
      {children}
    </Tag>
  );
}

/** A labelled region inside a panel, with the label set as annotation. */
export function Block({
  label,
  action,
  children,
  className = "",
}: {
  label: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <div className="mb-5 flex items-baseline justify-between gap-6 border-b border-hairline pb-3">
        <h3 className="font-mono text-label uppercase text-faint">{label}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

// --- navigation within a screen ------------------------------------------

export function Tabs<T extends string>({
  tabs,
  active,
  onSelect,
}: {
  tabs: { id: T; label: string; count?: number }[];
  active: T;
  onSelect: (id: T) => void;
}) {
  return (
    <div role="tablist" className="rail flex gap-8 overflow-x-auto border-b border-hairline">
      {tabs.map((tab) => {
        const on = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={on}
            onClick={() => onSelect(tab.id)}
            className={`-mb-px shrink-0 border-b-2 pb-4 font-mono text-label uppercase tracking-[0.14em] transition-colors duration-200 ${
              on
                ? "border-signal text-ink"
                : "border-transparent text-faint hover:text-muted"
            }`}
          >
            {tab.label}
            {tab.count === undefined ? null : (
              <span className="tnum ml-2 text-faint">{tab.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/**
 * A disclosure. The brief asks for cryptographic detail to be understandable
 * without overwhelming, and expandable by anyone who wants the whole thing,
 * which is exactly this: the summary is the answer, the body is the working.
 */
export function Disclose({
  summary,
  children,
  defaultOpen = false,
}: {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();
  const pointer = useCursorState("link");

  return (
    <div className="border-b border-hairline">
      <button
        {...pointer}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-6 py-4 text-left"
      >
        <span className="min-w-0">{summary}</span>
        <span
          aria-hidden
          className={`shrink-0 font-mono text-label text-faint transition-transform duration-200 ease-swift ${
            open ? "rotate-45" : ""
          }`}
        >
          +
        </span>
      </button>
      {open ? (
        <div id={id} className="pb-6">
          {children}
        </div>
      ) : null}
    </div>
  );
}

// --- process -------------------------------------------------------------

export type StepState = "done" | "active" | "waiting" | "failed";

const STEP_MARK: Record<StepState, string> = {
  done: "border-closed text-closed",
  active: "border-signal text-signal",
  waiting: "border-hairline text-faint",
  failed: "border-void text-void",
};

/**
 * A vertical stepper. Deliberately not a progress bar: these steps are not
 * uniform, several can sit unfinished for days, and one of them can fail and
 * refund. A bar would imply a duration nobody can promise.
 */
export function Steps({
  steps,
}: {
  steps: {
    index: string;
    title: string;
    state: StepState;
    detail?: ReactNode;
  }[];
}) {
  return (
    <ol className="border-t border-hairline">
      {steps.map((step) => (
        <li key={step.index} className="flex gap-6 border-b border-hairline py-5">
          <span
            aria-hidden
            className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border font-mono text-label ${
              STEP_MARK[step.state]
            }`}
          >
            {step.state === "done" ? "✓" : step.state === "failed" ? "✕" : step.index}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline gap-x-4">
              <span
                className={step.state === "waiting" ? "text-muted" : "text-ink"}
              >
                {step.title}
              </span>
              <span className="font-mono text-label uppercase tracking-[0.14em] text-faint">
                {step.state}
              </span>
            </div>
            {step.detail ? (
              <div className="mt-2 max-w-measure text-micro text-muted">
                {step.detail}
              </div>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}

// --- input ---------------------------------------------------------------

const FIELD =
  "w-full rounded-sm border border-rule bg-paper px-4 py-3 text-body text-ink " +
  "placeholder:text-faint focus:border-signal focus:outline-none";

export function TextInput({
  label,
  value,
  onChange,
  placeholder,
  hint,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  hint?: string;
  type?: "text" | "search" | "number";
}) {
  const id = useId();
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-2 block font-mono text-label uppercase tracking-[0.14em] text-faint"
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={FIELD}
      />
      {hint ? <p className="mt-2 text-micro text-faint">{hint}</p> : null}
    </div>
  );
}

export function Select<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
}) {
  const id = useId();
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-2 block font-mono text-label uppercase tracking-[0.14em] text-faint"
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className={`${FIELD} appearance-none`}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function Slider({
  label,
  value,
  onChange,
  max = 100,
  suffix = "%",
  disabled = false,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  max?: number;
  suffix?: string;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <div className={disabled ? "opacity-40" : ""}>
      <label htmlFor={id} className="flex items-baseline justify-between gap-4">
        <span className="font-mono text-label uppercase tracking-[0.14em] text-faint">
          {label}
        </span>
        <span className="tnum text-body text-ink">
          {value}
          {suffix}
        </span>
      </label>
      <input
        id={id}
        type="range"
        min={0}
        max={max}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-3 h-px w-full cursor-pointer appearance-none bg-rule accent-signal"
      />
    </div>
  );
}

// --- waiting -------------------------------------------------------------

/**
 * A placeholder with the shape of the thing it is waiting for. It appears only
 * after a beat: a skeleton that flashes for 80ms reads as a glitch, and most
 * of these reads return faster than that.
 */
export function Skeleton({
  rows = 3,
  className = "",
}: {
  rows?: number;
  className?: string;
}) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => setShow(true), 180);
    return () => window.clearTimeout(timer);
  }, []);
  if (!show) return null;

  return (
    <div className={`space-y-3 ${className}`} aria-hidden>
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="h-4 animate-pulse rounded-sm bg-shade"
          style={{ width: `${100 - i * 12}%` }}
        />
      ))}
    </div>
  );
}

/** A live region for asynchronous status, so screen readers hear the change. */
export function Status({ children }: { children: ReactNode }) {
  return (
    <p role="status" aria-live="polite" className="text-micro text-muted">
      {children}
    </p>
  );
}

// --- copy ----------------------------------------------------------------

/** A one-line value that can be taken away, for hashes and addresses. */
export function CopyLine({ value, label }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | null>(null);
  const pointer = useCursorState("link");

  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
    },
    [],
  );

  return (
    <button
      {...pointer}
      onClick={() => {
        void navigator.clipboard?.writeText(value).then(() => {
          setCopied(true);
          if (timer.current) window.clearTimeout(timer.current);
          timer.current = window.setTimeout(() => setCopied(false), 1600);
        });
      }}
      className="group flex w-full items-baseline gap-4 text-left"
      title={value}
    >
      {label ? (
        <span className="shrink-0 font-mono text-label uppercase text-faint">
          {label}
        </span>
      ) : null}
      <span className="evidence-type min-w-0 flex-1 truncate text-micro text-ink">
        {value}
      </span>
      <span className="shrink-0 font-mono text-label uppercase text-faint opacity-0 transition-opacity group-hover:opacity-100">
        {copied ? "copied" : "copy"}
      </span>
    </button>
  );
}
