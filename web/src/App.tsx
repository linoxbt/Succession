/**
 * The transaction, as a sequence of four screens.
 *
 * Step order follows Part 3's workflow, and the app holds no derived state of
 * its own: the listing's state field is the authority on where the transaction
 * has got to, so a reload lands in the right place rather than in whatever the
 * UI last believed.
 */
import { useCallback, useEffect, useState } from "react";
import { api, type Listing as ListingType, type Outcome, type Preview } from "./api";
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
  const [listing, setListing] = useState<ListingType | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [sealed, setSealed] = useState<{ sealed: boolean; at: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  // Recover the transaction's real position on load, rather than assuming one.
  useEffect(() => {
    void (async () => {
      try {
        const current = await api.listing();
        setListing(current);
        setPreview(await api.preview().catch(() => null));
        setScreen(
          current.state === "open"
            ? "listing"
            : current.state === "escrowed"
              ? "escrow"
              : "cutover",
        );
        setSealed(
          await api
            .seal("tenant-seller")
            .then((s) => ({ sealed: s.sealed, at: s.record?.sealed_at ?? "" }))
            .catch(() => null),
        );
      } catch {
        setScreen("scope");
      }
    })();
  }, []);

  const start = (categories: string[] | null) =>
    guard(async () => {
      await api.reset(categories ?? undefined);
      setListing(await api.listing());
      setPreview(await api.preview());
      setOutcome(null);
      setSealed(null);
      setScreen("listing");
    });

  const requestTransfer = () =>
    guard(async () => {
      setListing(await api.buy());
      setScreen("escrow");
    });

  const execute = () =>
    guard(async () => {
      const result = await api.transfer();
      setOutcome(result);
      setListing(await api.listing());
      const seal = await api.seal("tenant-seller");
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
          <Cutover sealed={sealed} />
        ) : (
          <p className="font-sans text-sm text-ink/50">Loading…</p>
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
