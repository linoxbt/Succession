/**
 * The console shell.
 *
 * A masthead, not application chrome. It sits directly on the paper, no
 * elevation, no tinted bar, and condenses as the page moves, so on a long
 * screen it becomes a hairline and a set of labels rather than a band
 * competing with the content beneath it.
 *
 * Navigation is typographic. The active destination is marked by a rule that
 * draws itself under the label rather than by a filled pill: a pill is a button
 * shape, and these are places, not actions.
 *
 * On narrow screens the row becomes a full-height overlay set at display scale
 * rather than a horizontally scrolling strip. Six destinations shrunk to fit
 * are six destinations nobody can hit.
 */
import { useEffect, useState, type ReactNode } from "react";

import { Wordmark } from "../brand/Logo";
import { useScrollProgress, useScrolled } from "../motion";

export type View = "market" | "listing" | "sell" | "claim" | "walkthrough" | "docs";

// "Walkthrough" reads as what it is. Naming it something like "Demo" beside
// "Marketplace" would invite exactly the confusion its banner then has to undo.
const NAV: { id: View; label: string }[] = [
  { id: "market", label: "Marketplace" },
  { id: "listing", label: "Listing" },
  { id: "sell", label: "Sell" },
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
  const scrolled = useScrolled(32);
  const progress = useScrollProgress();
  const [open, setOpen] = useState(false);

  // A menu that survives a route change is a menu covering the page you just
  // asked for.
  useEffect(() => {
    setOpen(false);
  }, [view]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  const go = (v: View) => {
    onView(v);
    setOpen(false);
  };

  return (
    <div className="min-h-screen bg-paper">
      <header
        className={`fixed inset-x-0 top-0 z-50 bg-paper/95 transition-[padding,border-color] duration-700 ease-swift ${
          scrolled ? "border-b border-rule py-3" : "border-b border-transparent py-6"
        }`}
      >
        {/* Reading position, as a hairline. The page is a document; this is how
            far through it you are. */}
        <div
          className="absolute inset-x-0 top-0 h-px origin-left bg-ink/25"
          style={{ transform: `scaleX(${progress})` }}
          aria-hidden="true"
        />

        <div className="gutter flex items-center justify-between gap-8">
          <button
            onClick={onHome}
            className="shrink-0 text-left transition-opacity duration-500 hover:opacity-60"
            aria-label="Succession, home"
          >
            <Wordmark size={scrolled ? 24 : 30} />
          </button>

          <nav className="hidden items-center gap-9 lg:flex" aria-label="Console">
            {NAV.map((item) => (
              <button
                key={item.id}
                onClick={() => go(item.id)}
                aria-current={view === item.id ? "page" : undefined}
                className={`link-underline whitespace-nowrap font-mono text-label uppercase transition-colors duration-500 ${
                  view === item.id ? "text-ink" : "text-faint hover:text-ink"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-6">
            <div className="hidden sm:block">{wallet}</div>
            <button
              onClick={() => setOpen((v) => !v)}
              className="font-mono text-label uppercase text-ink lg:hidden"
              aria-expanded={open}
              aria-controls="console-menu"
            >
              {open ? "Close" : "Menu"}
            </button>
          </div>
        </div>
      </header>

      <div
        id="console-menu"
        className={`fixed inset-0 z-40 bg-paper transition-opacity duration-500 ease-swift lg:hidden ${
          open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
        }`}
      >
        <div className="gutter flex h-full flex-col justify-center gap-1">
          {NAV.map((item, i) => (
            <button
              key={item.id}
              onClick={() => go(item.id)}
              style={{ transitionDelay: open ? `${i * 45}ms` : "0ms" }}
              className={`display-type text-left text-title transition-all duration-700 ease-enter ${
                open ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0"
              } ${view === item.id ? "text-ink" : "text-faint"}`}
            >
              {item.label}
            </button>
          ))}
          <div className="mt-12 sm:hidden">{wallet}</div>
        </div>
      </div>

      {/* The header is fixed, so the document starts clear of it. */}
      <main className="gutter min-h-[60vh] pb-chapter pt-32 sm:pt-40">{children}</main>

      <Footer onView={onView} />
    </div>
  );
}

/**
 * The footer closes the document rather than repeating the navigation as a
 * sitemap. It is the one place the console inverts to carbon while at rest,
 * which gives the end of a long scroll somewhere to land.
 */
function Footer({ onView }: { onView: (v: View) => void }) {
  return (
    <footer className="on-carbon">
      <div className="gutter py-beat">
        <div className="flex flex-col justify-between gap-16 lg:flex-row lg:items-end">
          <div>
            <p className="chapter-mark mb-6">The property layer for agent memory</p>
            <p className="display-type max-w-[15ch] text-title text-chalk">
              What an agent learned outlives the agent.
            </p>
          </div>

          <nav className="flex flex-wrap gap-x-10 gap-y-3" aria-label="Footer">
            {NAV.map((item) => (
              <button
                key={item.id}
                onClick={() => onView(item.id)}
                className="link-underline font-mono text-label uppercase text-chalkMuted transition-colors duration-500 hover:text-chalk"
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="mt-16 flex flex-col gap-3 border-t border-carbonRule pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-label uppercase text-chalkFaint">
            Settles on Base · ERC-8004 identity · Sibyl Memory
          </p>
          <a
            href="https://github.com/linoxbt/Succession"
            target="_blank"
            rel="noreferrer"
            className="link-underline font-mono text-label uppercase text-chalkMuted transition-colors duration-500 hover:text-chalk"
          >
            Source
          </a>
        </div>
      </div>
    </footer>
  );
}
