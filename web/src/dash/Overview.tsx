/**
 * The operations overview: state of the current sale, at a glance.
 */
import type { Listing, Outcome, Preview } from "../api";
import { formatAmount } from "../api";
import { Badge, Empty, Field, Hash, Panel, Stat, StatRow } from "../ui";

const STATE_TONE = {
  open: "neutral",
  escrowed: "accent",
  confirmed: "good",
  refunded: "bad",
} as const;

const STATE_LABEL = {
  open: "Listed",
  escrowed: "Escrow funded",
  confirmed: "Settled",
  refunded: "Refunded",
} as const;

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
      <Panel title="No listing">
        <Empty>Post a listing from the Listing tab to begin.</Empty>
      </Panel>
    );
  }

  const acp = preview.acp;

  return (
    <div className="space-y-6">
      <Panel>
        <StatRow>
          <Stat
            label="Asking price"
            value={formatAmount(listing.price, listing.currency).replace(" USDC", "")}
            sub={listing.currency}
          />
          <Stat
            label="Reference valuation"
            value={preview.valuation ? `$${preview.valuation.amount}` : "—"}
            sub="Not enforced by the contract"
          />
          <Stat label="Records in transfer" value={preview.counts.total_records ?? 0} />
          <Stat
            label="Verified ACP jobs"
            value={acp?.completed_jobs ?? "—"}
            sub={acp ? "On-chain job ids" : "No ACP history"}
            tone={acp?.completed_jobs ? "good" : "neutral"}
          />
        </StatRow>
      </Panel>

      <Panel title="Transaction">
        <dl>
          <Field label="State">
            <Badge tone={STATE_TONE[listing.state]}>{STATE_LABEL[listing.state]}</Badge>
          </Field>
          <Field label="Agent">
            <span className="font-mono text-[0.8125rem]">{listing.agent_id}</span>
          </Field>
          <Field label="Committed hash">
            <Hash value={listing.hash_commitment} chars={10} />
          </Field>
          {outcome ? (
            <Field label="Delivered hash">
              <span className="flex flex-wrap items-center gap-2">
                <Hash value={outcome.delivered_root} chars={10} />
                <Badge tone={outcome.outcome === "verified" ? "good" : "bad"}>
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
                <Badge tone="good">Sealed</Badge>
                <span className="text-secondary">{sealed.at}</span>
              </span>
            ) : (
              <Badge>Live</Badge>
            )}
          </Field>
        </dl>
      </Panel>

      <Panel title="Where each figure comes from">
        <dl>
          <Field label="Independently verifiable">
            {acp?.registered ? (
              <span className="flex flex-wrap items-center gap-2">
                <Badge tone="good">Virtuals ACP</Badge>
                <span className="text-secondary">
                  {acp.completed_jobs} completed · {acp.gross_volume} gross
                </span>
              </span>
            ) : (
              <span className="text-faint">None — agent not registered on ACP</span>
            )}
          </Field>
          <Field label="Self-reported">
            <span className="text-secondary">
              Record counts, memory size, tenure — computed from the seller's own store
            </span>
          </Field>
        </dl>
      </Panel>
    </div>
  );
}
