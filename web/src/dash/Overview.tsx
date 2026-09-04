/**
 * The operations overview: state of the current sale, at a glance.
 *
 * A definition list, not a row of stat tiles. Tiles are a dashboard idiom that
 * makes every figure look equally important and equally decorative; a closing
 * statement puts its figures in a column with their labels, where the reader
 * can compare them and see which are load-bearing.
 */
import type { Listing, Outcome, Preview } from "../api";
import { formatAmount } from "../api";
import { Badge, Empty, Field, FieldList, Hash, Section, type Tone } from "../ui";

const STATE_TONE: Record<Listing["state"], Tone> = {
  open: "neutral",
  escrowed: "escrow",
  confirmed: "closed",
  refunded: "void",
};

const STATE_LABEL: Record<Listing["state"], string> = {
  open: "Listed",
  escrowed: "Escrow: funds held",
  confirmed: "Settled",
  refunded: "Refunded",
};

export function Overview({
  listing,
  preview,
  outcome,
  sealed,
}: {
  listing: Listing | null;
  preview: Preview | null;
  outcome: Outcome | null;
  sealed: { sealed: boolean; at: string } | null;
}) {
  if (!listing || !preview) {
    return (
      <Section title="No listing">
        <Empty>Post a listing from the Listing tab to begin.</Empty>
      </Section>
    );
  }

  const acp = preview.acp;

  return (
    <div className="space-y-10">
      <Section title="Transaction">
        <FieldList className="mt-4">
          <Field label="State">
            <Badge tone={STATE_TONE[listing.state]}>{STATE_LABEL[listing.state]}</Badge>
          </Field>
          <Field label="Agent">
            <span className="font-mono text-[0.8125rem]">{listing.agent_id}</span>
          </Field>
          <Field label="Asking price" emphasis>
            {formatAmount(listing.price, listing.currency)}
          </Field>
          <Field label="Reference valuation">
            {preview.valuation ? `$${preview.valuation.amount}` : "—"}
            <span className="text-muted"> — not enforced by the contract</span>
          </Field>
          <Field label="Records in transfer">
            <span className="tnum">{preview.counts.total_records ?? 0}</span>
          </Field>
          <Field label="Committed hash">
            <Hash value={listing.hash_commitment} chars={10} />
          </Field>
          {outcome ? (
            <Field label="Delivered hash">
              <span className="flex flex-wrap items-center gap-2">
                <Hash value={outcome.delivered_root} chars={10} />
                <Badge tone={outcome.outcome === "verified" ? "closed" : "void"}>
                  {outcome.outcome === "verified" ? "Match" : "Mismatch"}
                </Badge>
              </span>
            </Field>
          ) : null}
          {outcome?.receipt ? (
            <Field label="Settlement">
              <Hash value={outcome.receipt.reference} chars={10} />
            </Field>
          ) : null}
          <Field label="Origin tenant">
            {sealed?.sealed ? (
              <span className="flex flex-wrap items-center gap-2">
                <Badge tone="closed">Sealed</Badge>
                <span className="text-muted">{sealed.at}</span>
              </span>
            ) : (
              <Badge>Live</Badge>
            )}
          </Field>
        </FieldList>
      </Section>

      <Section title="Where each figure comes from">
        <FieldList className="mt-4">
          <Field label="Independently verifiable">
            {acp?.registered ? (
              <span className="flex flex-wrap items-center gap-2">
                <Badge tone="closed">Virtuals ACP</Badge>
                <span className="text-muted">
                  {acp.completed_jobs} completed · {acp.gross_volume} gross
                </span>
              </span>
            ) : (
              <span className="text-muted">None — agent not registered on ACP</span>
            )}
          </Field>
          <Field label="Self-reported">
            <span className="text-muted">
              Record counts, memory size, tenure — computed from the seller's own store
            </span>
          </Field>
        </FieldList>
      </Section>
    </div>
  );
}
