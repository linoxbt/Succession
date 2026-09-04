/**
 * Two surfaces: the landing page and the operations console.
 *
 * Routing is a single path check rather than a router dependency — there are
 * exactly two destinations and five views, and a library for that is weight
 * without benefit.
 *
 * The app holds no derived state about where the transaction has got to: the
 * listing's own `state` field is the authority, so a reload lands where the
 * transaction actually is rather than where the UI last believed it was.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type Listing, type Outcome, type Preview } from "./api";
import { Agents } from "./dash/Agents";
import { Docs } from "./dash/Docs";
import { ListingView } from "./dash/ListingView";
import { Memory } from "./dash/Memory";
import { Overview } from "./dash/Overview";
import { Shell, type View } from "./dash/Shell";
import { Transfers, type TransferRow } from "./dash/Transfers";
import { Landing } from "./landing/Landing";
import { loadRecordedRun, probeLiveApi, recordedApi, type RecordedRun } from "./recorded";
import { Badge } from "./ui";

export default function App() {
  const [route, setRoute] = useState<"landing" | "console">(
    window.location.pathname.startsWith("/app") ? "console" : "landing",
  );
  const [view, setView] = useState<View>("overview");
  const [recorded, setRecorded] = useState<RecordedRun | null>(null);
  const [listing, setListing] = useState<Listing | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [sealed, setSealed] = useState<{ sealed: boolean; at: string } | null>(null);
  const [ledger, setLedger] = useState<TransferRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const backend = useMemo(() => (recorded ? recordedApi(recorded) : api), [recorded]);

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

  const guard = useCallback(async (work: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  // Pick a backend, then recover the transaction's real position.
  useEffect(() => {
    void (async () => {
      let source: RecordedRun | null = null;
      if (!(await probeLiveApi())) {
        source = await loadRecordedRun().catch(() => null);
        setRecorded(source);
      }
      const client = source ? recordedApi(source) : api;
      if (source?.transfers) setLedger(source.transfers);

      try {
        const current = await client.listing();
        setListing(current);
        setPreview(await client.preview().catch(() => null));
        setSealed(
          await client
            .seal("tenant-seller")
            .then((s) => ({ sealed: s.sealed, at: s.record?.sealed_at ?? "" }))
            .catch(() => null),
        );
      } catch {
        setListing(null);
      }
    })();
  }, []);

  const refresh = useCallback(
    async (client: typeof api) => {
      setListing(await client.listing());
      setPreview(await client.preview().catch(() => null));
    },
    [],
  );

  const onList = (categories: string[] | null) =>
    guard(async () => {
      await backend.reset(categories ?? undefined);
      await refresh(backend as typeof api);
      setOutcome(null);
      setSealed(null);
    });

  const onBuy = () =>
    guard(async () => {
      setListing(await backend.buy());
    });

  const onSettle = () =>
    guard(async () => {
      const result = await backend.transfer();
      setOutcome(result);
      const seal = await backend.seal("tenant-seller");
      setSealed({ sealed: seal.sealed, at: seal.record?.sealed_at ?? "" });
      setListing(await backend.listing().catch(() => listing));
    });

  if (route === "landing") {
    return (
      <Landing
        onEnter={() => navigate("console")}
        onDocs={() => {
          setView("docs");
          navigate("console");
        }}
      />
    );
  }

  return (
    <Shell
      view={view}
      onNavigate={setView}
      onHome={() => navigate("landing")}
      banner={recorded ? <RecordedBanner run={recorded} /> : null}
    >
      {error ? (
        <div className="mb-5 rounded-md border border-bad/40 bg-bad/10 px-4 py-3 text-[0.8125rem] text-bad">
          {error}
        </div>
      ) : null}

      {view === "overview" ? (
        <Overview listing={listing} preview={preview} outcome={outcome} sealed={sealed} />
      ) : null}
      {view === "listing" ? (
        <ListingView
          listing={listing}
          preview={preview}
          outcome={outcome}
          busy={busy}
          onList={onList}
          onBuy={onBuy}
          onSettle={onSettle}
        />
      ) : null}
      {view === "transfers" ? <Transfers rows={ledger} current={outcome} /> : null}
      {view === "agents" ? <Agents preview={preview} /> : null}
      {view === "memory" ? <Memory backend={backend} sealed={sealed} /> : null}
      {view === "docs" ? <Docs /> : null}
    </Shell>
  );
}

/**
 * Named on every screen and not dismissible. A recorded run presented as a live
 * one is exactly the pattern this project argues against.
 */
function RecordedBanner({ run }: { run: RecordedRun }) {
  return (
    <div className="border-b border-warn/30 bg-warn/[0.07] px-5 py-2.5">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.75rem] text-warn">
        <Badge tone="warn">Recorded</Badge>
        <span className="text-secondary">
          No service running. Replaying one real transfer captured {run.recorded_at}.
          Every hash and reply is genuine output — reproduce it with{" "}
          <code className="font-mono">python -m succession.demo</code>.
        </span>
      </p>
    </div>
  );
}
