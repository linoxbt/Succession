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

export type View = "market" | "listing" | "sell" | "claim" | "walkthrough" | "docs";

// "Walkthrough" sits last and reads as what it is. It is the one destination
// here that is not live data, and putting it beside "Marketplace" under a name
// like "Demo agent" would invite exactly the confusion the banner then has to
// undo.
const NAV: { id: View; label: string }[] = [
  { id: "market", label: "Marketplace" },
  { id: "listing", label: "Listing" },
  { id: "sell", label: "Sell your agent" },
  { id: "claim", label: "Claim" },
  { id: "walkthrough", label: "Walkthrough" },
  { id: "docs", label: "Docs" },
];

export default function Shell({
  view,
  onView,
  onHome,
  wallet,
  children,
}: {
  view: View;
  onView: (v: View) => void;
  onHome: () => void;
  wallet?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-vellum">
      <header className="border-b border-rule">
        <div className="mx-auto flex max-w-document items-center justify-between gap-6 px-6 py-5">
          <button onClick={onHome} className="text-left" aria-label="Succession home">
            <Wordmark size={20} />
          </button>
          {wallet}
        </div>
        {/* Horizontal, scrollable on narrow screens rather than hidden behind a
            hamburger: seven destinations do not need to be concealed. */}
        <nav className="mx-auto max-w-document overflow-x-auto px-6">
          <div className="flex gap-6">
            {NAV.map((item) => (
              <button
                key={item.id}
                onClick={() => onView(item.id)}
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

      <main className="mx-auto max-w-document px-6 py-10">{children}</main>
    </div>
  );
}
