/**
 * The transaction, as a sequence of four screens.
 *
 * Step order follows Part 3's workflow, and the app holds no derived state of
 * its own: the listing's state field is the authority on where the transaction
 * has got to, so a reload lands in the right place rather than in whatever the
 * UI last believed.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type Listing as ListingType, type Outcome, type Preview } from "./api";
import { loadRecordedRun, probeLiveApi, recordedApi, type RecordedRun } from "./recorded";
import { CategorySelector } from "./components/CategorySelector";
import { Confirmation } from "./components/Confirmation";
import { Cutover } from "./components/Cutover";
import { Escrow } from "./components/Escrow";
import { Listing } from "./components/Listing";
import { Notice, Rule } from "./components/primitives";

type Screen = "scope" | "listing" | "escrow" | "confirmation" | "cutover";

const STEPS: { id: Screen; label: string }[] = [
  { id: "scope", label: "Scope" },
  { id: "listing", label: "Listing" },
  { id: "escrow", label: "Escrow" },
  { id: "confirmation", label: "Confirmation" },
  { id: "cutover", label: "Cutover" },
];

export default function App() {
  const [screen, setScreen] = useState<Screen>("scope");
  const [recorded, setRecorded] = useState<RecordedRun | null>(null);
  const [ready, setReady] = useState(false);
  const [listing, setListing] = useState<ListingType | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [sealed, setSealed] = useState<{ sealed: boolean; at: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // One backend, chosen once. Everything below calls `backend`, so no screen
  // needs to know whether it is driving the live service or the recording.
  const backend = useMemo(
    () => (recorded ? recordedApi(recorded) : api),
    [recorded],
  );

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

  // Pick a backend, then recover the transaction's real position rather than
  // assuming one — a reload lands where the transaction actually is.
  useEffect(() => {
    void (async () => {
      let source: RecordedRun | null = null;
      if (!(await probeLiveApi())) {
        source = await loadRecordedRun().catch(() => null);
        setRecorded(source);
      }
      const client = source ? recordedApi(source) : api;

      try {
        const current = await client.listing();
        setListing(current);
        setPreview(await client.preview().catch(() => null));
        setScreen(
          current.state === "open"
            ? "listing"
            : current.state === "escrowed"
              ? "escrow"
              : "cutover",
        );
        setSealed(
          await client
            .seal("tenant-seller")
            .then((s) => ({ sealed: s.sealed, at: s.record?.sealed_at ?? "" }))
            .catch(() => null),
        );
      } catch {
        setScreen("scope");
      } finally {
        setReady(true);
      }
    })();
  }, []);

  const start = (categories: string[] | null) =>
    guard(async () => {
      await backend.reset(categories ?? undefined);
      setListing(await backend.listing());
      setPreview(await backend.preview());
      setOutcome(null);
      setSealed(null);
      setScreen("listing");
    });

  const requestTransfer = () =>
    guard(async () => {
      setListing(await backend.buy());
      setScreen("escrow");
    });

  const execute = () =>
    guard(async () => {
      const result = await backend.transfer();
      setOutcome(result);
      const seal = await backend.seal("tenant-seller");
      setSealed({ sealed: seal.sealed, at: seal.record?.sealed_at ?? "" });
      setScreen("confirmation");
    });

  return (
    <div className="min-h-screen">
      <header className="border-b border-rule">
        <div className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-5 sm:flex-row sm:items-baseline sm:justify-between">
          <p className="font-serif text-lg">Succession</p>
          <nav aria-label="Transaction progress">
            <ol className="flex flex-wrap gap-x-5 gap-y-1 font-sans text-xs uppercase tracking-[0.1em]">
              {STEPS.map((step) => (
                <li
                  key={step.id}
                  aria-current={screen === step.id ? "step" : undefined}
                  className={screen === step.id ? "text-ink" : "text-ink/35"}
                >
                  {step.label}
                </li>
              ))}
            </ol>
          </nav>
        </div>
      </header>

      {recorded ? <RecordedBanner run={recorded} /> : null}

      <main className="mx-auto max-w-3xl px-6 py-12">
        {error ? (
          <div className="mb-8">
            <Notice tone="void">{error}</Notice>
          </div>
        ) : null}

        {screen === "scope" ? (
          <CategorySelector onConfirm={start} busy={busy} />
        ) : screen === "listing" && listing && preview ? (
          <Listing
            listing={listing}
            preview={preview}
            onRequestTransfer={requestTransfer}
            busy={busy}
          />
        ) : screen === "escrow" && listing ? (
          <Escrow listing={listing} onExecute={execute} busy={busy} />
        ) : screen === "confirmation" && outcome ? (
          <Confirmation
            outcome={outcome}
            onContinue={() =>
              setScreen(outcome.outcome === "verified" ? "cutover" : "scope")
            }
          />
        ) : screen === "cutover" ? (
          <Cutover sealed={sealed} backend={backend} />
        ) : (
          <p className="font-sans text-sm text-ink/50">
            {ready ? "Loading…" : "Checking for a running service…"}
          </p>
        )}
      </main>

      <footer className="mx-auto max-w-3xl px-6 pb-12">
        <Rule className="mb-5" />
        <p className="font-sans text-xs leading-relaxed text-ink/45">
          Demo identities and settlement run locally. All counterparties in the
          seeded memory are invented.
        </p>
      </footer>
    </div>
  );
}


/**
 * Named on every screen, not dismissible.
 *
 * A recorded run presented as a live one is precisely the pattern this project
 * exists to argue against, so the mode is stated permanently and the banner
 * says how to reproduce the numbers rather than asking to be trusted.
 */
function RecordedBanner({ run }: { run: RecordedRun }) {
  return (
    <div className="border-b border-escrow/40 bg-escrow/[0.06]">
      <div className="mx-auto max-w-3xl px-6 py-3">
        <p className="font-sans text-xs leading-relaxed text-escrow">
          <span className="font-semibold uppercase tracking-[0.08em]">
            Recorded run
          </span>{" "}
          — no service is running, so this replays one real end-to-end transfer
          captured on {run.recorded_at}. Every hash, signature and agent reply
          below is genuine output, not a mock-up. Reproduce it with{" "}
          <code className="font-mono">python -m succession.demo</code>: the
          export is deterministic, so it prints the same root.
        </p>
      </div>
    </div>
  );
}