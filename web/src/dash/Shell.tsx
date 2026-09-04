/**
 * The console shell.
 *
 * A masthead and a rule, not an application chrome. The reference is a data
 * room's own navigation: quiet, textual, and never competing with the document
 * it frames. Nothing here is sticky-blurred or elevated — the page is flat
 * paper, and the navigation sits on it rather than floating above it.
 */
import type { ReactNode } from "react";
import { Wordmark } from "../brand/Logo";

export type View = "market" | "overview" | "listing" | "transfers" | "agents" | "memory" | "docs";

const NAV: { id: View; label: string }[] = [
  { id: "market", label: "Marketplace" },
  { id: "overview", label: "Overview" },
  { id: "listing", label: "Listing" },
  { id: "transfers", label: "Transfers" },
  { id: "agents", label: "Agents" },
  { id: "memory", label: "Memory" },
  { id: "docs", label: "Docs" },
];

export function Shell({
  view,
  onNavigate,
  onHome,
  banner,
  children,
}: {
  view: View;
  onNavigate: (v: View) => void;
  onHome: () => void;
  banner?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-vellum">
      <header className="border-b border-rule">
        <div className="mx-auto flex max-w-document items-center justify-between gap-6 px-6 py-5">
          <button onClick={onHome} className="text-left" aria-label="Succession home">
            <Wordmark size={20} />
          </button>
        </div>
        {/* Horizontal, scrollable on narrow screens rather than hidden behind a
            hamburger: seven destinations do not need to be concealed. */}
        <nav className="mx-auto max-w-document overflow-x-auto px-6">
          <div className="flex gap-6">
            {NAV.map((item) => (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                aria-current={view === item.id ? "page" : undefined}
                className={`-mb-px whitespace-nowrap border-b-2 py-2.5 text-[0.875rem] transition-colors ${
                  view === item.id
                    ? "border-ink text-ink"
                    : "border-transparent text-muted hover:text-ink"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </nav>
      </header>

      {banner}

      <main className="mx-auto max-w-document px-6 py-10">{children}</main>
    </div>
  );
}
