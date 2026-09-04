/**
 * Listing, escrow, and settlement — the three key screens of Part 9's brief.
 *
 * The listing reads like a one-page teaser in a data room: agent identity,
 * tenure, and aggregate stats as a definition list, then a clearly separated
 * "verified on-chain" strip carrying the hash commitment and a link to the
 * contract. That strip is set apart with a hairline border and never a shadow,
 * because it is the element that should feel most official.
 *
 * The post-purchase screen is intentionally anticlimactic — a confirmation
 * line, a hash-match checkmark, and the certificate. The real climax happens
 * inside the agent's own conversation view, not in the chrome around it. What
 * it does *not* do is hide the hash comparison behind a generic success
 * banner: the comparison is the product's credibility, so it renders as two
 * full monospace blocks a person can read against each other.
 */
import { useEffect, useRef, useState } from "react";
import type { Listing, Outcome, Preview } from "../api";
import { formatAmount } from "../api";
import {
  Badge,
  Button,
  Evidence,
  Field,
  FieldList,
  FullHash,
  Hash,
  Note,
  Section,
  Table,
  Td,
  VerifyMark,
} from "../ui";

const CATEGORIES: { id: string; description: string }[] = [
  { id: "identity", description: "The agent's own registration record" },
  { id: "relationships", description: "Counterparties and the edges between them" },
  { id: "preferences", description: "Learned settings and operating limits" },
  { id: "history", description: "The journal, archived records, ACP job history" },
  { id: "commitments", description: "Open quotes, agreed terms, live working state" },
  { id: "learned-behaviors", description: "Adapted patterns and encoded playbooks" },
];

/** Basescan, when the settlement reference is a real transaction hash. */
function explorerFor(reference: string): string | null {
  return /^0x[0-9a-fA-F]{64}$/.test(reference)
    ? `https://sepolia.basescan.org/tx/${reference}`
    : null;
}

export function ListingView({
  listing,
  preview,
  outcome,
  busy,
  onList,
  onBuy,
  onSettle,
}: {
  listing: Listing | null;
  preview: Preview | null;
  outcome: Outcome | null;
  busy: boolean;
  onList: (categories: string[] | null) => void;
  onBuy: () => void;
  onSettle: () => void;
}) {
  if (!listing) {
    return <ScopeSelector preview={preview} busy={busy} onList={onList} />;
  }

  return (
    <div className="space-y-10">
      {preview ? <DataRoom preview={preview} listing={listing} /> : null}
      {listing.state === "open" ? <OpenEscrow listing={listing} busy={busy} onBuy={onBuy} /> : null}
      {listing.state === "escrowed" ? (
        <EscrowHeld listing={listing} busy={busy} onSettle={onSettle} />
      ) : null}
      {outcome ? <Settlement outcome={outcome} /> : null}
    </div>
  );
}

/* -- 1. scope ----------------------------------------------------------- */

/**
 * The partial-succession selector.
 *
 * Categories the seller marked non-transferable are greyed out and genuinely
 * unselectable — disabled, not merely unchecked — exactly as the brief
 * specifies. The distinction matters: an unchecked box invites a click, and
 * the answer to that click would have to be a refusal.
 *
 * This sits *before* the listing rather than between listing and escrow,
 * because a partial sale commits its own root over exactly what is sold. The
 * scope has to be settled before there is a hash to commit to.
 */
function ScopeSelector({
  preview,
  busy,
  onList,
}: {
  preview: Preview | null;
  busy: boolean;
  onList: (categories: string[] | null) => void;
}) {
  const transferability = preview?.category_transferability ?? {};
  const locked = (id: string) => {
    const row = transferability[id];
    return row !== undefined && row.sellable === 0;
  };
  const selectable = CATEGORIES.filter((c) => !locked(c.id)).map((c) => c.id);
  const [selected, setSelected] = useState<string[]>(selectable);

  // Keep the selection honest if the preview arrives after first paint.
  useEffect(() => {
    setSelected((current) => current.filter((id) => !locked(id)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preview]);

  const all = selected.length === selectable.length && selectable.length === CATEGORIES.length;

  return (
    <Section title="Scope of transfer">
      <FieldList className="mt-4">
        {CATEGORIES.map(({ id, description }) => {
          const isLocked = locked(id);
          const row = transferability[id];
          return (
            <label
              key={id}
              className={`flex items-start gap-3 border-b border-hairline py-3 ${
                isLocked ? "cursor-not-allowed opacity-45" : "cursor-pointer"
              }`}
            >
              <input
                type="checkbox"
                disabled={isLocked}
                checked={!isLocked && selected.includes(id)}
                onChange={() =>
                  setSelected((c) =>
                    c.includes(id) ? c.filter((x) => x !== id) : [...c, id],
                  )
                }
                className="mt-1 h-4 w-4 accent-escrow disabled:cursor-not-allowed"
              />
              <span className="min-w-0">
                <span className="block text-[0.9375rem] text-ink">{id}</span>
                <span className="block text-[0.8125rem] text-muted">{description}</span>
                {isLocked ? (
                  <span className="mt-1 block text-[0.8125rem] text-void">
                    Marked non-transferable. Not available in any sale.
                  </span>
                ) : row ? (
                  <span className="mt-1 block text-[0.8125rem] text-faint tnum">
                    {row.sellable} records
                    {row.withheld > 0 ? ` · ${row.withheld} withheld as non-transferable` : ""}
                  </span>
                ) : null}
              </span>
            </label>
          );
        })}
      </FieldList>

      <div className="mt-6 flex flex-wrap items-center gap-5">
        <Button onClick={() => onList(all ? null : selected)} disabled={busy || !selected.length}>
          {busy ? "Posting…" : all ? "Post full succession" : `Post ${selected.length} categories`}
        </Button>
        <Note>A partial sale commits its own hash, over exactly what is sold.</Note>
      </div>
    </Section>
  );
}

/* -- 2. the data-room teaser -------------------------------------------- */

function DataRoom({ preview, listing }: { preview: Preview; listing: Listing }) {
  const acp = preview.acp;
  const counterparties = preview.category_breakdown.relationship ?? 0;

  return (
    <Section>
      <header className="border-b border-rule pb-3">
        <h1 className="font-serif text-document text-ink">
          Agent {listing.agent_id.split(":").pop()}
        </h1>
        <p className="mt-1 text-[0.875rem] text-muted">
          <span className="font-mono text-[0.8125rem]">{listing.agent_id}</span>
          {" · registered "}
          <span className="tnum">{preview.tenure_days}</span> days
        </p>
      </header>

      <FieldList className="mt-6">
        <Field label="Records in transfer">
          <span className="tnum">{(preview.counts.total_records ?? 0).toLocaleString()}</span>
        </Field>
        <Field label="Journal events">
          <span className="tnum">{(preview.counts.journal_events ?? 0).toLocaleString()}</span>
        </Field>
        <Field label="Counterparties">
          <span className="tnum">{counterparties}</span>
        </Field>
        <Field label="Memory size">
          <span className="tnum">{(preview.memory_size_bytes / 1024).toFixed(1)} KB</span>
        </Field>
        {acp ? (
          <Field label="Completed jobs (ACP)">
            {acp.registered ? (
              <span className="flex flex-wrap items-baseline gap-3">
                <span className="tnum">{acp.completed_jobs}</span>
                <Badge tone="closed">Independently verifiable</Badge>
              </span>
            ) : (
              <span className="text-muted">
                Not registered on the ACP service registry — figures self-reported.
              </span>
            )}
          </Field>
        ) : null}
        {acp?.registered && acp.success_rate ? (
          <Field label="Success rate (verified)">
            <span className="tnum">{acp.success_rate}</span>
          </Field>
        ) : null}
        <Field label="Categories in transfer">{listing.categories.join(", ")}</Field>
        <Field label="Withheld as non-transferable">
          <span className="tnum">{preview.withheld_non_transferable}</span>
          <span className="text-muted"> — excluded before hashing</span>
        </Field>
        {preview.valuation ? (
          <Field label="Valuation (reference)" emphasis>
            ${preview.valuation.amount}
          </Field>
        ) : null}
        <Field label="Asking price" emphasis>
          {formatAmount(listing.price, listing.currency)}
        </Field>
      </FieldList>

      <Evidence>
        <dl className="space-y-2">
          <EvidenceRow label="Committed hash" value={listing.hash_commitment} />
          <EvidenceRow label="Seller signature" value={listing.seller_signature} />
          <EvidenceRow label="Listing contract" value={listing.listing_id} />
        </dl>
      </Evidence>

      <p className="mt-3 text-[0.8125rem] text-muted">{preview.disclosure}</p>

      {preview.valuation ? <Valuation valuation={preview.valuation} /> : null}
    </Section>
  );
}

function EvidenceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-6">
      <dt className="w-full shrink-0 text-[0.8125rem] text-muted sm:w-64">{label}</dt>
      <dd className="min-w-0">
        <Hash value={value} chars={10} />
      </dd>
    </div>
  );
}

function Valuation({ valuation }: { valuation: NonNullable<Preview["valuation"]> }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-8">
      <div className="flex items-baseline justify-between gap-4 border-b border-rule pb-2">
        <h3 className="font-serif text-heading text-ink">Reference valuation</h3>
        <button
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="text-[0.8125rem] text-muted underline underline-offset-4 hover:text-ink"
        >
          {open ? "Hide derivation" : "Show derivation"}
        </button>
      </div>
      {open ? (
        <div className="mt-4">
          <Table head={["Factor", "Value", "Basis"]}>
            {valuation.factors.map((f) => (
              <tr key={f.name}>
                <Td className="text-muted">{f.name}</Td>
                <Td className="tnum">× {f.value}</Td>
                <Td className="text-muted">{f.explanation}</Td>
              </tr>
            ))}
          </Table>
          <p className="mt-3 text-[0.8125rem] text-faint">
            Not included: {Object.keys(valuation.excluded).join(", ")}. A single
            listing has no marketplace to compute them from.
          </p>
        </div>
      ) : null}
    </div>
  );
}

/* -- 3. escrow ---------------------------------------------------------- */

function OpenEscrow({
  listing,
  busy,
  onBuy,
}: {
  listing: Listing;
  busy: boolean;
  onBuy: () => void;
}) {
  return (
    <Section title="Request transfer">
      <div className="mt-4 flex flex-wrap items-center gap-5">
        <Button onClick={onBuy} disabled={busy}>
          {busy ? "Funding…" : `Fund escrow — ${formatAmount(listing.price, listing.currency)}`}
        </Button>
        <Note>The content key is released only against funded escrow.</Note>
      </div>
    </Section>
  );
}

function EscrowHeld({
  listing,
  busy,
  onSettle,
}: {
  listing: Listing;
  busy: boolean;
  onSettle: () => void;
}) {
  return (
    <Section
      title="Escrow in progress"
      action={<Badge tone="escrow">Escrow: funds held</Badge>}
    >
      <FieldList className="mt-4">
        <Field label="Held in escrow" emphasis>
          {formatAmount(listing.escrow_balance, listing.currency)}
        </Field>
        <Field label="Buyer">
          <Hash value={listing.buyer} chars={8} />
        </Field>
        <Field label="Hash commitment">
          <Hash value={listing.hash_commitment} chars={10} />
          <span className="text-muted"> — fixed at listing, unchangeable</span>
        </Field>
        <Field label="Released on">A delivered hash matching that commitment.</Field>
      </FieldList>
      <div className="mt-6 flex flex-wrap items-center gap-5">
        <Button onClick={onSettle} disabled={busy}>
          {busy ? "Settling…" : "Deliver and settle"}
        </Button>
        <Note>Payment, identity and the seal move together, or not at all.</Note>
      </div>
    </Section>
  );
}

/* -- 4. transfer confirmation ------------------------------------------- */

function Settlement({ outcome }: { outcome: Outcome }) {
  const verified = outcome.outcome === "verified";

  // The pulse fires once, when verification completes — not on every re-render
  // of an already-settled transaction. An animation that replays on reload is
  // decoration, and this product has exactly one animated moment.
  const seen = useRef<string | null>(null);
  const [pulse, setPulse] = useState(false);
  useEffect(() => {
    const key = `${outcome.listing_id}:${outcome.outcome}`;
    if (seen.current !== key) {
      seen.current = key;
      setPulse(true);
      const t = window.setTimeout(() => setPulse(false), 500);
      return () => window.clearTimeout(t);
    }
  }, [outcome.listing_id, outcome.outcome]);

  const short = outcome.committed_root.slice(0, 6) + "…" + outcome.committed_root.slice(-4);

  return (
    <Section>
      <header className="flex flex-wrap items-center gap-3 border-b border-rule pb-3">
        <VerifyMark matched={verified} pulse={pulse} />
        <h2 className="font-serif text-heading text-ink">
          {verified ? "Transfer confirmed" : "Hash mismatch"}
        </h2>
        <Badge tone={verified ? "closed" : "void"}>
          {verified ? "Escrow released to seller" : "Escrow refunded to buyer"}
        </Badge>
      </header>

      {/* Copy voice: formal and precise, like a closing document. Errors state
          exactly what happened and what it means for the money. */}
      <p className="mt-4 max-w-document text-[0.9375rem] leading-relaxed text-ink">
        {verified ? (
          <>
            Hash verified: <span className="font-mono text-[0.875rem]">{short}</span>.
            Funds released to seller.
          </>
        ) : (
          <>
            Delivered memory does not match the committed hash. Escrow
            automatically refunded to buyer.
          </>
        )}
      </p>

      <div className="mt-6 grid gap-6 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-[0.75rem] uppercase tracking-[0.06em] text-faint">
            Committed at listing
          </p>
          <FullHash value={outcome.committed_root} />
        </div>
        <div>
          <p className="mb-2 text-[0.75rem] uppercase tracking-[0.06em] text-faint">
            Re-hashed on the buyer's store
          </p>
          <FullHash value={outcome.delivered_root} tone={verified ? "closed" : "void"} />
        </div>
      </div>

      {outcome.failure_reason ? (
        <p className="mt-4 max-w-document text-[0.875rem] text-void">
          {outcome.failure_reason}
        </p>
      ) : null}

      {outcome.receipt ? (
        <FieldList className="mt-8">
          <Field label="Paid to">
            <Hash value={outcome.receipt.paid_to} chars={8} />
          </Field>
          {verified ? (
            <Field label="Identity transferred to">
              <Hash value={outcome.receipt.identity_transferred_to} chars={8} />
            </Field>
          ) : null}
          <Field label="Confirmed by">
            {outcome.receipt.confirmed_by === "arbiter" ? (
              <span className="flex flex-wrap items-baseline gap-2">
                <span>Evaluator (arbiter)</span>
                <Badge tone="closed">Independently re-derived</Badge>
              </span>
            ) : (
              <span>
                Buyer <span className="text-muted">— self-reported delivery hash</span>
              </span>
            )}
          </Field>
          <Field label="Settlement">
            {explorerFor(outcome.receipt.reference) ? (
              <a
                className="underline underline-offset-4 hover:text-escrow"
                href={explorerFor(outcome.receipt.reference)!}
                target="_blank"
                rel="noreferrer"
              >
                <Hash value={outcome.receipt.reference} chars={10} />
              </a>
            ) : (
              <Hash value={outcome.receipt.reference} chars={10} />
            )}
          </Field>
        </FieldList>
      ) : null}

      {outcome.certificate ? <Certificate outcome={outcome} /> : null}
    </Section>
  );
}

function Certificate({ outcome }: { outcome: Outcome }) {
  const cert = outcome.certificate!;
  function download() {
    const body = outcome.certificate_text || `${JSON.stringify(cert, null, 2)}\n`;
    const url = URL.createObjectURL(new Blob([body], { type: "text/plain;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `succession-certificate-${cert.memory_asset.replace("#", "")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="mt-10">
      <h3 className="border-b border-rule pb-2 font-serif text-heading text-ink">
        Succession Certificate
      </h3>
      <FieldList className="mt-4">
        <Field label="Memory asset">{cert.memory_asset}</Field>
        <Field label="Origin agent">
          <span className="font-mono text-[0.8125rem]">{cert.origin_agent}</span>
        </Field>
        <Field label="Successor agent">
          <span className="font-mono text-[0.8125rem]">{cert.successor_agent}</span>
        </Field>
        <Field label="Memory version">
          <span className="tnum">{cert.memory_version}</span>
        </Field>
        <Field label="Records transferred">
          <span className="tnum">{cert.records_transferred.toLocaleString()}</span>
        </Field>
        <Field label="Integrity hash">
          <Hash value={cert.integrity_hash} chars={10} />
        </Field>
        <Field label="Transfer date">{cert.transfer_date}</Field>
        <Field label="Transfer status">
          <Badge tone={cert.transfer_status === "VERIFIED" ? "closed" : "void"}>
            {cert.transfer_status}
          </Badge>
        </Field>
      </FieldList>
      <div className="mt-5">
        <Button variant="ghost" size="sm" onClick={download}>
          Download certificate
        </Button>
      </div>
    </div>
  );
}
