/**
 * The console.
 *
 * Two surfaces that must never be confused. **Market** shows listings that
 * exist because a seller ran `succession list` against their own Sibyl store
 * and paid gas to commit its root — the contract is the source of truth and an
 * empty market is a true answer. **Walkthrough** is a scripted sale on a sample
 * agent that settles in-process and touches no chain; it lives behind its own
 * banner and its own client, and no code path connects the two.
 *
 * Selling is not in the browser, and cannot be. Sibyl 0.8.0 is local-only —
 * `MemoryClient.local(path)` is its sole constructor — so a seller's memory is a
 * file on their own disk that no web page can read. The honest interface hands
 * them the command instead of pretending otherwise, which is what `Sell` does.
 */
import { useCallback, useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from "wagmi";

import { config as wagmiConfig } from "./chain/config";
import { WalletBar, useChainStatus } from "./chain/Wallet";
import { market, type MarketRow } from "./api";
import { Landing } from "./landing/Landing";
import Shell, { type View } from "./dash/Shell";
import Marketplace from "./dash/Marketplace";
import ListingView from "./dash/ListingView";
import Sell from "./dash/Sell";
import Claim from "./dash/Claim";
import Walkthrough from "./dash/Walkthrough";
import { Docs } from "./dash/Docs";
import { Note } from "./ui";
import { CursorProvider, SmoothScroll } from "./motion";
import Cursor from "./chrome/Cursor";
import Preloader from "./chrome/Preloader";
import Transition from "./chrome/Transition";

export default function App() {
  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        {/* Lenis wraps the whole app so the interpolated scroll survives moving
            between the landing document and the console — a page that changes
            its scroll physics mid-session feels broken rather than varied. */}
        <SmoothScroll>
          <CursorProvider>
            <Cursor />
            <Surface />
          </CursorProvider>
        </SmoothScroll>
      </QueryClientProvider>
    </WagmiProvider>
  );
}

const queryClient = new QueryClient();

function Surface() {
  const [route, setRoute] = useState<"landing" | "console">(
    window.location.pathname.startsWith("/app") ? "console" : "landing",
  );
  const [view, setView] = useState<View>("market");
  const [rows, setRows] = useState<MarketRow[]>([]);
  const [selected, setSelected] = useState<MarketRow | null>(null);
  const [onChain, setOnChain] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  const chainStatus = useChainStatus();

  const navigate = useCallback((next: "landing" | "console") => {
    window.history.pushState({}, "", next === "console" ? "/app" : "/");
    setRoute(next);
  }, []);

  useEffect(() => {
    const onPop = () =>
      setRoute(window.location.pathname.startsWith("/app") ? "console" : "landing");
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const load = useCallback(async () => {
    try {
      const body = await market.listings();
      setRows(body.listings);
      setOnChain(body.chain);
      setError(null);
    } catch (e) {
      // A marketplace that cannot reach its service shows nothing and says so.
      // Filling the screen from a cached recording is the pattern this project
      // argues against, so there is deliberately no fallback here.
      setRows([]);
      setOnChain(false);
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const open = useCallback((row: MarketRow) => {
    setSelected(row);
    setView("listing");
  }, []);

  if (route === "landing") {
    return (
      <>
        {/* The curtain owns the first paint and lifts itself. The landing is
            mounted underneath it from the start, so the hero's own entrance is
            already running as the curtain clears rather than starting after. */}
        <Preloader onDone={() => undefined} />
        <Landing
          onEnter={() => navigate("console")}
          onDocs={() => {
            setView("docs");
            navigate("console");
          }}
        />
      </>
    );
  }

  return (
    <Shell
      view={view}
      onView={setView}
      onHome={() => navigate("landing")}
      wallet={<WalletBar status={chainStatus} />}
    >
      {error && view === "market" ? (
        <Note>
          The marketplace service is unreachable ({error}). Listings are read
          from the contract through it, so nothing is shown rather than
          something invented.
        </Note>
      ) : null}

      <Transition routeKey={view}>
      {view === "market" ? (
        <Marketplace
          rows={rows}
          onChain={onChain}
          onOpen={open}
          onSell={() => setView("sell")}
          onRefresh={load}
        />
      ) : null}
      {view === "listing" ? (
        <ListingView
          row={selected}
          chainStatus={chainStatus}
          onBack={() => setView("market")}
          onClaim={() => setView("claim")}
          onRefresh={load}
        />
      ) : null}
      {view === "sell" ? <Sell chainStatus={chainStatus} /> : null}
      {view === "claim" ? <Claim listingId={selected?.listing.listing_id ?? ""} /> : null}
      {view === "walkthrough" ? <Walkthrough /> : null}
      {view === "docs" ? <Docs /> : null}
      </Transition>
    </Shell>
  );
}
