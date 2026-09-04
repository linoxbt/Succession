/**
 * The console shell: left rail, dense content, no chrome that does not work.
 */
import type { ReactNode } from "react";
import { Wordmark } from "../brand/Logo";

export type View = "overview" | "listing" | "transfers" | "agents" | "memory" | "docs";

const NAV: { id: View; label: string }[] = [
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
    <div className="min-h-screen bg-base">
      <div className="flex">
        {/* Left rail. Collapses to a horizontal strip rather than a hamburger:
            five destinations do not need to be hidden behind a tap. */}
        <aside className="sticky top-0 hidden h-screen w-56 shrink-0 border-r border-line bg-panel md:block">
          <button
            onClick={onHome}
            className="flex w-full items-center px-5 py-5 text-left transition-colors hover:text-white"
            aria-label="Succession home"
          >
            <Wordmark size={20} />
          </button>
          <nav className="px-2">
            {NAV.map((item) => (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                aria-current={view === item.id ? "page" : undefined}
                className={`mb-0.5 flex w-full items-center rounded-md px-3 py-2 text-left text-[0.8125rem] font-medium transition-colors ${
                  view === item.id
                    ? "bg-raised text-primary"
                    : "text-secondary hover:bg-raised/60 hover:text-primary"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-10 border-b border-line bg-base/85 backdrop-blur">
            <div className="flex items-center justify-between gap-4 px-5 py-3.5">
              <h1 className="text-[0.9375rem] font-semibold capitalize tracking-tight">
                {view}
              </h1>
              <button
                onClick={onHome}
                className="text-[0.8125rem] text-secondary hover:text-primary md:hidden"
              >
                Succession
              </button>
            </div>
            <nav className="flex gap-1 overflow-x-auto px-3 pb-2 md:hidden">
              {NAV.map((item) => (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={`whitespace-nowrap rounded-md px-3 py-1.5 text-[0.8125rem] font-medium ${
                    view === item.id ? "bg-raised text-primary" : "text-secondary"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </nav>
          </header>

          {banner}

          <main className="mx-auto max-w-5xl px-5 py-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
