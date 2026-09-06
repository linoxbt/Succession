/**
 * A listing, at a glance.
 *
 * Not a product card. What a buyer is weighing is an operating asset, so the
 * card leads with identity and settlement state and then answers the questions
 * that decide whether the listing is worth opening: how much memory, how long
 * it has been accumulating, how many counterparties it reaches, whether its
 * integrity can be checked, and what is included.
 *
 * Every figure is drawn from the published data room. A listing whose seller
 * published nothing shows a short line saying exactly that rather than a grid
 * of zeroes, because zero counterparties and no published figure are different
 * claims and only one of them is true.
 */
import {
  formatAmount,
  type MarketRow,
  type Preview,
} from "../api";
import { useCursorState } from "../motion";
import { Badge } from "../ui";
import {
  DemoMark,
  SELLABLE_DIRECTORIES,
  STATE_TONE,
} from "./domain";
import { Panel } from "./ui";

function summarise(row: MarketRow) {
  const preview = row.preview as Preview | undefined;
  const inventory = preview?.inventory ?? {};
  const directories = SELLABLE_DIRECTORIES.filter((d) => inventory[d]?.offerable);

  return {
    described: Boolean(preview?.agent_identity),
    records: Object.values(inventory).reduce((sum, e) => sum + e.sellable, 0),
    tenureDays: preview?.tenure_days ?? 0,
    counterparties: inventory.relationships?.sellable ?? 0,
    events: inventory.history?.sellable ?? 0,
    successRate: preview?.acp?.success_rate ?? null,
    scope: directories.length === SELLABLE_DIRECTORIES.length ? "full" : "partial",
    offered: directories.length,
    verified: Boolean(row.integrity?.root),
  };
}

function months(days: number): string {
  if (days <= 0) return "new";
  if (days < 60) return `${days} days`;
  const m = Math.round(days / 30);
  return m < 24 ? `${m} months` : `${(m / 12).toFixed(1)} years`;
}

export default function ListingCard({
  row,
  onOpen,
}: {
  row: MarketRow;
  onOpen: (row: MarketRow) => void;
}) {
  const pointer = useCursorState("link");
  const s = summarise(row);
  const listing = row.listing;

  const facts: { label: string; value: string }[] = s.described
    ? [
        { label: "Memory", value: `${s.records.toLocaleString()} records` },
        { label: "Age", value: months(s.tenureDays) },
        { label: "Relationships", value: s.counterparties.toLocaleString() },
        { label: "Journal", value: s.events.toLocaleString() },
      ]
    : [];

  return (
    <Panel
      as="article"
      interactive
      className="flex h-full flex-col justify-between p-7"
    >
      <div>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h3 className="truncate text-heading text-ink">
              {row.name || `Agent ${listing.agent_id}`}
            </h3>
            <p className="evidence-type mt-1 truncate text-micro text-faint">
              {row.agent_identity || listing.agent_id}
            </p>
          </div>
          {row.demo ? <DemoMark notice={row.notice} /> : null}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2">
          <Badge tone={STATE_TONE[listing.state] ?? "neutral"}>{listing.state}</Badge>
          {s.described ? (
            <Badge tone={s.scope === "full" ? "closed" : "neutral"}>
              {s.scope} succession
            </Badge>
          ) : null}
          {s.verified ? <Badge tone="closed">merkle verified</Badge> : null}
        </div>

        {s.described ? (
          <dl className="mt-7 grid grid-cols-2 gap-x-6 gap-y-4">
            {facts.map((fact) => (
              <div key={fact.label}>
                <dt className="font-mono text-label uppercase tracking-[0.14em] text-faint">
                  {fact.label}
                </dt>
                <dd className="tnum mt-1 text-body text-ink">{fact.value}</dd>
              </div>
            ))}
            {s.successRate ? (
              <div>
                <dt className="font-mono text-label uppercase tracking-[0.14em] text-faint">
                  Performance
                </dt>
                <dd className="tnum mt-1 text-body text-ink">
                  {(Number(s.successRate) * 100).toFixed(1)}%
                </dd>
              </div>
            ) : null}
            <div>
              <dt className="font-mono text-label uppercase tracking-[0.14em] text-faint">
                Directories
              </dt>
              <dd className="tnum mt-1 text-body text-ink">
                {s.offered} of {SELLABLE_DIRECTORIES.length}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="mt-7 max-w-measure text-micro text-muted">
            On chain and undescribed. This seller published no data room, so
            there are no figures to weigh. The commitment and the price still
            stand.
          </p>
        )}
      </div>

      <div className="mt-8 flex items-end justify-between gap-6 border-t border-hairline pt-6">
        <div>
          <div className="tnum text-figure text-ink">
            {formatAmount(listing.price, listing.currency)}
          </div>
          {row.valuation ? (
            <div className="tnum mt-1 text-micro text-faint">
              valued at ${row.valuation}
            </div>
          ) : null}
        </div>
        <button
          {...pointer}
          onClick={() => onOpen(row)}
          className="link-underline shrink-0 font-mono text-label uppercase tracking-[0.14em] text-ink"
        >
          View listing
        </button>
      </div>
    </Panel>
  );
}
