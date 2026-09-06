/**
 * The console.
 *
 * Two surfaces that must never be confused. **Market** shows listings that
 * exist because a seller ran `succession list` against their own Sibyl store
 * and paid gas to commit its root, the contract is the source of truth and an
 * empty market is a true answer. **Walkthrough** is a scripted sale on a sample
 * agent that settles in-process and touches no chain; it lives behind its own
 * banner and its own client, and no code path connects the two.
 *
 * Selling is not in the browser, and cannot be. Sibyl 0.8.0 is local-only,
 * `MemoryClient.local(path)` is its sole constructor, so a seller's memory is a
 * file on their own disk that no web page can read. The honest interface hands
 * them the command instead of pretending otherwise, which is what `Sell` does.
 */
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from "wagmi";

import { config as wagmiConfig } from "./chain/config";
import { WalletBar, useChainStatus } from "./chain/Wallet";
import { type MarketRow } from "./api";
// Views reach the backend through this seam rather than through `api.ts`, so a
// screen can be built against a shape the service does not serve yet.
import { service } from "./services";
import { Landing } from "./landing/Landing";
import { to, useNavigation } from "./router";
import Shell from "./dash/Shell";
import Dashboard from "./dash/Overview";
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
            between the landing document and the console, a page that changes
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
  const { route, navigate } = useNavigation();
  const view = route.kind === "app" ? route.view : "overview";
  const listingId = route.kind === "app" ? route.listingId : null;

  const [rows, setRows] = useState<MarketRow[]>([]);
  const [demo, setDemo] = useState<MarketRow[]>([]);
  const [fetched, setFetched] = useState<MarketRow | null>(null);
  const [onChain, setOnChain] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const chainStatus = useChainStatus();

  // The console's palette is scoped by an attribute on the root element rather
  // than by a wrapper class, because the body background, the native
  // `color-scheme`, the fixed cursor layer, the focus ring and ::selection all
  // live outside the app's own tree. `main.tsx` sets the same attribute before
  // the first paint so a direct load of /app never flashes the light ground.
  useLayoutEffect(() => {
    const root = document.documentElement;
    if (route.kind === "app") root.dataset.surface = "app";
    else delete root.dataset.surface;
  }, [route.kind]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const body = await service.listings();
      setRows(body.real);
      setDemo(body.demo);
      setOnChain(body.chain);
      setError(null);
    } catch (e) {
      // A marketplace that cannot reach its service shows nothing and says so.
      // Filling the screen from a cached recording is the pattern this project
      // argues against, so there is deliberately no fallback here.
      setRows([]);
      setDemo([]);
      setOnChain(false);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // A listing is now addressed by URL, so the row is resolved from the address
  // rather than carried in state by whoever clicked. That is what makes
  // /app/listing/listing-672 work in a fresh tab.
  const selected = useMemo(() => {
    if (!listingId) return null;
    const known = [...rows, ...demo].find(
      (r) => r.listing.listing_id === listingId,
    );
    if (known) return known;
    return fetched?.listing.listing_id === listingId ? fetched : null;
  }, [listingId, rows, demo, fetched]);

  // Fetch the single listing only when the market has not already loaded it.
  // The ref records which id was attempted so a listing the service cannot
  // resolve is asked for once, not on every render of a failed lookup.
  const attempted = useRef<string | null>(null);
  useEffect(() => {
    if (!listingId) return;
    if ([...rows, ...demo].some((r) => r.listing.listing_id === listingId)) return;
    if (attempted.current === listingId) return;
    attempted.current = listingId;

    let live = true;
    void service
      .listing(listingId)
      .then((row) => live && setFetched(row))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [listingId, rows, demo]);

  const open = useCallback(
    (row: MarketRow) => navigate(to.listing(row.listing.listing_id)),
    [navigate],
  );
  const openById = useCallback(
    (id: string) => navigate(to.listing(id)),
    [navigate],
  );

  if (route.kind === "landing") {
    return (
      <>
        {/* The curtain owns the first paint and lifts itself. The landing is
            mounted underneath it from the start, so the hero's own entrance is
            already running as the curtain clears rather than starting after. */}
        <Preloader onDone={() => undefined} />
        <Landing
          onEnter={() => navigate(to.view("overview"))}
          onDocs={() => navigate(to.view("docs"))}
        />
      </>
    );
  }

  return (
    <Shell
      view={view}
      onView={(next) => navigate(to.view(next))}
      onHome={() => navigate(to.landing())}
      wallet={<WalletBar status={chainStatus} />}
    >
      {error && view === "market" ? (
        <Note>
          The marketplace service is unreachable ({error}). Listings are read
          from the contract through it, so nothing is shown rather than
          something invented.
        </Note>
      ) : null}

      {/* Keyed on the address, not just the view, so moving between two
          listings animates as a navigation rather than swapping content
          underneath a stationary page. */}
      <Transition routeKey={`${view}:${listingId ?? ""}`}>
      {view === "overview" ? <Dashboard onOpenListing={openById} /> : null}
      {view === "market" ? (
        <Marketplace
          rows={rows}
          demo={demo}
          onChain={onChain}
          loading={loading}
          onOpen={open}
          onSell={() => navigate(to.view("sell"))}
          onRefresh={load}
        />
      ) : null}
      {view === "listing" ? (
        <ListingView
          row={selected}
          chainStatus={chainStatus}
          onBack={() => navigate(to.view("market"))}
          onClaim={() => navigate(to.view("claim"))}
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
