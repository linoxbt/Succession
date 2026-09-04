/**
 * Listing, escrow, and settlement — one workflow, one screen.
 *
 * The hash comparison is not tucked behind a success banner. It is the product's
 * credibility, so it renders as two monospace blocks a person can actually read
 * against each other.
 */
import { useState } from "react";
import type { Listing, Outcome, Preview } from "../api";
import { formatAmount } from "../api";
import { Badge, Button, Field, Hash, Panel, Rule, Table, Td } from "../ui";

const CATEGORIES: { id: string; description: string }[] = [
  { id: "identity", description: "The agent's own registration record" },
  { id: "relationships", description: "Counterparties and the edges between them" },
  { id: "preferences", description: "Learned settings and operating limits" },
  { id: "history", description: "The journal, archived records, ACP job history" },
  { id: "commitments", description: "Open quotes, agreed terms, live working state" },
  { id: "learned-behaviors", description: "Adapted patterns and encoded playbooks" },
];

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
  const [selected, setSelected] = useState<string[]>(CATEGORIES.map((c) => c.id));
  const all = selected.length === CATEGORIES.length;

  if (!listing) {
    return (
      <Panel title="Scope of transfer" action={<span className="text-xs text-faint">Step 1 of 3</span>}>
        <div className="divide-y divide-hairline">
          {CATEGORIES.map(({ id, description }) => (
            <label key={id} className="flex cursor-pointer items-start gap-3 px-5 py-3">
              <input
                type="checkbox"
                checked={selected.includes(id)}
                onChange={() =>
                  setSelected((c) =>
                    c.includes(id) ? c.filter((x) => x !== id) : [...c, id],
                  )
                }
                className="mt-0.5 h-4 w-4 accent-accent"
              />
              <span>
                <span className="block text-[0.8125rem] font-medium">{id}</span>
                <span className="block text-[0.8125rem] text-secondary">{description}</span>
              </span>
            </label>
          ))}
        </div>
        <Rule />
        <div className="flex flex-wrap items-center gap-3 px-5 py-4">
          <Button onClick={() => onList(all ? null : selected)} disabled={busy || !selected.length}>
            {busy ? "Posting…" : all ? "Post full succession" : `Post ${selected.length} categories`}
          </Button>
          <span className="text-xs text-faint">
            A partial sale commits its own hash, over exactly what is sold.
          </span>
        </div>
      </Panel>
    );
  }

  return (
    <div className="space-y-6">
      {preview ? <DataRoom preview={preview} listing={listing} /> : null}

      {listing.state === "open" ? (
        <Panel title="Escrow" action={<span className="text-xs text-faint">Step 2 of 3</span>}>
          <div className="flex flex-wrap items-center gap-3 px-5 py-4">
            <Button onClick={onBuy} disabled={busy}>
              {busy ? "Funding…" : `Fund escrow — ${formatAmount(listing.price, listing.currency)}`}
            </Button>
            <span className="text-xs text-faint">
              The content key is released only against funded escrow.
            </span>
          </div>
        </Panel>
      ) : null}

      {listing.state === "escrowed" ? (
        <Panel title="Escrow funded" action={<Badge tone="accent">Funds held</Badge>}>
          <dl>
            <Field label="Held">{formatAmount(listing.escrow_balance, listing.currency)}</Field>
            <Field label="Buyer">
              <Hash value={listing.buyer} chars={8} />
            </Field>
            <Field label="Released on">A delivered hash matching the commitment.</Field>
          </dl>
          <div className="flex flex-wrap items-center gap-3 px-5 py-4">
            <Button onClick={onSettle} disabled={busy}>
              {busy ? "Settling…" : "Deliver and settle"}
            </Button>
            <span className="text-xs text-faint">
              Payment, identity and the seal move together, or not at all.
            </span>
          </div>
        </Panel>
      ) : null}

      {outcome ? <Settlement outcome={outcome} /> : null}
    </div>
  );
}

function DataRoom({ preview, listing }: { preview: Preview; listing: Listing }) {
  const acp = preview.acp;
  return (
    <Panel
      title="Data room"
      action={<span className="text-xs text-faint">Aggregate only until settlement</span>}
    >
      <dl>
        <Field label="Agent">
          <span className="font-mono text-[0.8125rem]">{listing.agent_id}</span>
        </Field>
        <Field label="Categories in transfer">{listing.categories.join(", ")}</Field>
        <Field label="Records">{preview.counts.total_records}</Field>
        <Field label="Journal events">{preview.counts.journal_events}</Field>
        <Field label="Counterparties">{preview.category_breakdown.relationship ?? 0}</Field>
        <Field label="Memory size">{(preview.memory_size_bytes / 1024).toFixed(1)} KB</Field>
        <Field label="Withheld as non-transferable">
          {preview.withheld_non_transferable} — excluded before hashing
        </Field>
        {acp?.registered ? (
          <Field label="ACP job history">
            <span className="flex flex-wrap items-center gap-2">
              <Badge tone="good">Verifiable</Badge>
              <span className="text-secondary">
                {acp.completed_jobs} completed, {acp.failed_jobs} failed, {acp.gross_volume} gross
              </span>
            </span>
          </Field>
        ) : null}
        <Field label="Committed hash">
          <Hash value={listing.hash_commitment} chars={12} />
        </Field>
        <Field label="Seller signature">
          <Hash value={listing.seller_signature} chars={10} />
        </Field>
      </dl>
      {preview.valuation ? <Valuation valuation={preview.valuation} /> : null}
    </Panel>
  );
}

function Valuation({ valuation }: { valuation: NonNullable<Preview["valuation"]> }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Rule />
      <div className="flex items-center justify-between gap-4 px-5 py-3">
        <span className="text-[0.8125rem] text-secondary">Reference valuation</span>
        <span className="flex items-center gap-4">
          <span className="tnum text-lg font-semibold">${valuation.amount}</span>
          <button
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="text-[0.8125rem] text-accent hover:underline"
          >
            {open ? "Hide" : "Derivation"}
          </button>
        </span>
      </div>
      {open ? (
        <>
          <Table head={["Factor", "Value", "Basis"]}>
            {valuation.factors.map((f) => (
              <tr key={f.name}>
                <Td className="font-mono text-faint">{f.name}</Td>
                <Td className="tnum">× {f.value}</Td>
                <Td className="text-secondary">{f.explanation}</Td>
              </tr>
            ))}
          </Table>
          <p className="border-t border-hairline px-5 py-3 text-xs text-faint">
            Not included: {Object.keys(valuation.excluded).join(", ")}. A single
            listing has no marketplace to compute them from.
          </p>
        </>
      ) : null}
    </>
  );
}

function Settlement({ outcome }: { outcome: Outcome }) {
  const verified = outcome.outcome === "verified";
  return (
    <Panel
      title={verified ? "Hash verified" : "Hash mismatch"}
      action={
        <Badge tone={verified ? "good" : "bad"}>
          {verified ? "Escrow released" : "Escrow refunded"}
        </Badge>
      }
    >
      <div className="grid gap-px bg-line sm:grid-cols-2">
        <HashBlock label="Committed at listing" value={outcome.committed_root} />
        <HashBlock
          label="Re-hashed on the buyer's store"
          value={outcome.delivered_root}
          tone={verified ? "good" : "bad"}
        />
      </div>

      {outcome.receipt ? (
        <dl className="border-t border-line">
          <Field label="Paid to">
            <Hash value={outcome.receipt.paid_to} chars={8} />
          </Field>
          {verified ? (
            <Field label="Identity transferred to">
              <Hash value={outcome.receipt.identity_transferred_to} chars={8} />
            </Field>
          ) : null}
          <Field label="Transaction">
            <Hash value={outcome.receipt.reference} chars={12} />
          </Field>
        </dl>
      ) : null}

      {outcome.certificate ? <Certificate outcome={outcome} /> : null}
    </Panel>
  );
}

function HashBlock({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "good" | "bad";
}) {
  const colour = { neutral: "text-primary", good: "text-good", bad: "text-bad" }[tone];
  return (
    <div className="bg-panel p-5">
      <p className="mb-3 text-[0.6875rem] uppercase tracking-[0.08em] text-faint">{label}</p>
      <p className={`break-all font-mono text-[0.8125rem] leading-relaxed ${colour}`}>
        {value.replace(/^0x/, "").match(/.{1,8}/g)?.join(" ") ?? value}
      </p>
    </div>
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
    <>
      <Rule />
      <Table head={["Certificate", ""]}>
        <tr>
          <Td className="text-secondary">Memory asset</Td>
          <Td>{cert.memory_asset}</Td>
        </tr>
        <tr>
          <Td className="text-secondary">Origin → successor</Td>
          <Td className="font-mono">
            {cert.origin_agent} → {cert.successor_agent}
          </Td>
        </tr>
        <tr>
          <Td className="text-secondary">Records transferred</Td>
          <Td className="tnum">{cert.records_transferred.toLocaleString()}</Td>
        </tr>
        <tr>
          <Td className="text-secondary">Memory version</Td>
          <Td className="tnum">{cert.memory_version}</Td>
        </tr>
        <tr>
          <Td className="text-secondary">Status</Td>
          <Td>
            <Badge tone={cert.transfer_status === "VERIFIED" ? "good" : "bad"}>
              {cert.transfer_status}
            </Badge>
          </Td>
        </tr>
      </Table>
      <div className="px-5 py-4">
        <Button variant="ghost" size="sm" onClick={download}>
          Download certificate
        </Button>
      </div>
    </>
  );
}
