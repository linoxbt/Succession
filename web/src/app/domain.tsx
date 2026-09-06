/**
 * Components that know what Succession is.
 *
 * Everything here renders one protocol concept and refuses to render it when
 * the data is absent. That refusal is the point: a memory profile that shows
 * "0 counterparties" for a listing whose seller published nothing is a lie
 * told by a default value, and this marketplace's whole argument is that a
 * figure should trace to something.
 *
 * So the rule followed throughout: **absent and zero are different**. Absent
 * says so in words. Zero is a measurement.
 */
import type { ReactNode } from "react";

import {
  formatAmount,
  type CategoryInventory,
  type IntegrityManifest,
  type Listing,
  type MarketRow,
  type Preview,
  type ProvenanceHeader,
  type Reputation,
} from "../api";
import { Badge, Hash, type Tone } from "../ui";
import { Block, Disclose, Panel } from "./ui";

// --- vocabulary ----------------------------------------------------------

/** The nine SMP directories, in the order the packager writes them. */
export const DIRECTORIES = [
  "identity",
  "relationships",
  "preferences",
  "history",
  "commitments",
  "learned-behaviors",
  "provenance",
  "permissions",
  "integrity-proof",
] as const;

/** The six that carry memory and can be sold. The last three are generated. */
export const SELLABLE_DIRECTORIES = DIRECTORIES.slice(0, 6);

export const DIRECTORY_NOTE: Record<string, string> = {
  identity: "Who the agent is, and the ERC-8004 token that says so.",
  relationships: "Counterparties it knows, and the edges between them.",
  preferences: "Standing choices it has been taught to make.",
  history: "What it did, including settled ACP jobs.",
  commitments: "Obligations still outstanding at the moment of sale.",
  "learned-behaviors": "Heuristics it adapted rather than arrived with.",
  provenance: "The chain of custody, written at build time.",
  permissions: "Consent, per record, for what may change hands.",
  "integrity-proof": "The Merkle tree a buyer re-derives to check the sale.",
};

/**
 * Settlement state, as the contract knows it. Four values, not eleven: the
 * remaining phases of a sale happen off chain and the contract cannot see them.
 */
export const STATE_TONE: Record<string, Tone> = {
  open: "neutral",
  escrowed: "escrow",
  confirmed: "closed",
  refunded: "void",
};

export const STATE_MEANING: Record<string, string> = {
  open: "Listed and committed. No buyer has funded escrow.",
  escrowed: "A buyer's funds are held by the contract. Nothing has settled.",
  confirmed: "The delivered root matched. Paid, identity moved, seller sealed.",
  refunded: "Cancelled, or the hash did not match. The buyer was made whole.",
};

// --- small parts ---------------------------------------------------------

export function DemoMark({ notice }: { notice?: string }) {
  return (
    <span
      title={notice ?? "Demonstration listing. Not on chain and not for sale."}
      className="inline-flex shrink-0 items-center border border-rule px-2 py-0.5 font-mono text-label uppercase tracking-[0.14em] text-faint"
    >
      demo
    </span>
  );
}

export function EscrowStatus({ listing }: { listing: Listing }) {
  const state = listing.state;
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Badge tone={STATE_TONE[state] ?? "neutral"}>{state}</Badge>
      {listing.sealed ? <Badge tone="closed">sealed</Badge> : null}
      {listing.escrow_balance > 0 ? (
        <span className="tnum text-micro text-muted">
          {formatAmount(listing.escrow_balance, listing.currency)} held
        </span>
      ) : null}
    </div>
  );
}

export function SealStatus({ listing }: { listing: Listing }) {
  if (!listing.sealed) {
    return (
      <p className="max-w-measure text-micro text-muted">
        The seller's copy is live. Sealing happens at settlement, not at listing.
      </p>
    );
  }
  return (
    <p className="max-w-measure text-micro text-muted">
      The seller's tenant is sealed. Its credentials were revoked and every write
      path rejects. There is deliberately no unseal.
    </p>
  );
}

export function VerificationBadge({ row }: { row: MarketRow }) {
  const manifest = row.integrity;
  const verified = Boolean(manifest?.root);
  if (!verified) {
    return (
      <span className="font-mono text-label uppercase tracking-[0.14em] text-faint">
        no manifest published
      </span>
    );
  }
  const agrees =
    manifest?.root?.toLowerCase() === row.listing.hash_commitment.toLowerCase();
  return (
    <Badge tone={agrees ? "closed" : "void"}>
      {agrees ? "merkle verified" : "root disagrees with chain"}
    </Badge>
  );
}

export function AgentIdentity({
  row,
  className = "",
}: {
  row: MarketRow;
  className?: string;
}) {
  const identity = row.agent_identity || row.listing.agent_id;
  return (
    <div className={className}>
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span className="text-title text-ink">
          {row.name || `Agent ${row.listing.agent_id}`}
        </span>
        {row.demo ? <DemoMark notice={row.notice} /> : null}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2">
        <span className="evidence-type text-micro text-muted">{identity}</span>
        <span className="font-mono text-label uppercase tracking-[0.14em] text-faint">
          ERC-8004
        </span>
        {row.vertical ? (
          <span className="text-micro text-muted">{row.vertical}</span>
        ) : null}
      </div>
    </div>
  );
}

// --- memory --------------------------------------------------------------

function statOrNull(value: number | undefined): string | null {
  return value === undefined || value === null ? null : value.toLocaleString();
}

/**
 * The figures a buyer weighs, and only the ones the seller actually published.
 * A listing with no data room renders nothing here and says why, rather than a
 * row of zeroes that looks like a worthless agent instead of an undescribed one.
 */
export function MemoryStats({ row }: { row: MarketRow }) {
  const preview = row.preview as Preview | undefined;
  if (!preview?.agent_identity) {
    return (
      <p className="max-w-measure text-micro text-muted">
        This listing is on chain and undescribed. Its seller published no data
        room, so there are no figures to show. The commitment and the price are
        still binding.
      </p>
    );
  }

  const inventory = preview.inventory ?? {};
  const sellable = Object.values(inventory).reduce(
    (sum, entry) => sum + entry.sellable,
    0,
  );
  const counterparties =
    inventory.relationships?.sellable ?? preview.category_transferability?.relationships?.sellable;
  const events = inventory.history?.sellable;
  const acp = preview.acp;

  const stats: { label: string; value: string | null; note?: string }[] = [
    {
      label: "Records for sale",
      value: sellable ? sellable.toLocaleString() : statOrNull(preview.counts?.total_records),
    },
    { label: "Tenure, days", value: statOrNull(preview.tenure_days) },
    { label: "Counterparties", value: statOrNull(counterparties) },
    { label: "Journal events", value: statOrNull(events) },
    {
      label: "Task performance",
      value: acp?.success_rate ? `${(Number(acp.success_rate) * 100).toFixed(1)}%` : null,
      note:
        acp && !acp.success_rate
          ? "Fewer than five resolved outcomes, so no rate is claimed."
          : undefined,
    },
    {
      label: "Memory size",
      value: preview.memory_size_bytes
        ? `${(preview.memory_size_bytes / 1024).toFixed(0)} KB`
        : null,
    },
  ];

  return (
    <div className="grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
      {stats.map((stat) => (
        <div key={stat.label}>
          <div className="tnum text-figure text-ink">
            {stat.value ?? <span className="text-faint">not published</span>}
          </div>
          <div className="mt-1 font-mono text-label uppercase tracking-[0.14em] text-faint">
            {stat.label}
          </div>
          {stat.note ? (
            <div className="mt-1 max-w-measure text-micro text-faint">{stat.note}</div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

/**
 * The package, directory by directory. All nine appear: three of them are built
 * rather than sold, and a buyer should be able to see what exists but is not on
 * offer rather than wonder what was left out.
 */
export function MemoryPackageViewer({ row }: { row: MarketRow }) {
  const preview = row.preview as Preview | undefined;
  const inventory = preview?.inventory ?? {};
  const subroots = new Map(
    (row.integrity?.categories ?? []).map((entry) => [entry.category, entry]),
  );

  return (
    <div className="border-t border-hairline">
      {DIRECTORIES.map((directory) => {
        const generated = !SELLABLE_DIRECTORIES.includes(
          directory as (typeof SELLABLE_DIRECTORIES)[number],
        );
        const entry: CategoryInventory | undefined = inventory[directory];
        const subroot = subroots.get(directory);

        return (
          <Disclose
            key={directory}
            summary={
              <span className="flex flex-wrap items-baseline gap-x-5 gap-y-1">
                <span className="evidence-type text-body text-ink">{directory}/</span>
                {generated ? (
                  <Badge>coming soon</Badge>
                ) : entry?.offerable ? (
                  <span className="tnum text-micro text-muted">
                    {entry.sellable.toLocaleString()} records
                  </span>
                ) : (
                  <span className="font-mono text-label uppercase text-faint">
                    nothing offered
                  </span>
                )}
                {subroot ? (
                  <span className="font-mono text-label uppercase tracking-[0.14em] text-closed">
                    subroot
                  </span>
                ) : null}
              </span>
            }
          >
            <div className="max-w-reading space-y-4 text-micro text-muted">
              <p>{DIRECTORY_NOTE[directory]}</p>

              {generated ? (
                <p>
                  Generated when the package is built. It describes the memory
                  rather than being part of it, so it is not a selection unit
                  and is not sold.
                </p>
              ) : entry ? (
                <dl className="grid grid-cols-2 gap-x-8 gap-y-2 sm:grid-cols-4">
                  <Stat label="Transferable" value={entry.sellable.toLocaleString()} />
                  <Stat
                    label="Withheld by seller"
                    value={entry.withheld_by_seller.toLocaleString()}
                  />
                  <Stat
                    label="No consent"
                    value={entry.withheld_without_consent.toLocaleString()}
                  />
                  <Stat label="Depth" value={entry.depth} />
                </dl>
              ) : (
                <p>The seller published no inventory for this directory.</p>
              )}

              <p>
                Preview: aggregate counts only. Record bodies are released after
                purchase and hash verification, never before.
              </p>

              {subroot ? (
                <div>
                  <span className="font-mono text-label uppercase text-faint">
                    Merkle subroot, {subroot.leaf_count} leaves
                  </span>
                  <div className="evidence-type mt-1 break-all text-micro text-ink">
                    {subroot.subroot}
                  </div>
                </div>
              ) : null}
            </div>
          </Disclose>
        );
      })}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="font-mono text-label uppercase tracking-[0.14em] text-faint">
        {label}
      </dt>
      <dd className="tnum mt-1 text-body text-ink">{value}</dd>
    </div>
  );
}

/** What the sale includes, and whether that is all of it. */
export function TransferScope({ row }: { row: MarketRow }) {
  const inventory = (row.preview as Preview | undefined)?.inventory ?? {};
  const offered = SELLABLE_DIRECTORIES.filter((d) => inventory[d]?.offerable);
  const held = SELLABLE_DIRECTORIES.filter((d) => inventory[d] && !inventory[d]?.offerable);

  if (offered.length === 0) {
    return (
      <p className="max-w-measure text-micro text-muted">
        The seller published no scope for this listing.
      </p>
    );
  }

  const full = offered.length === SELLABLE_DIRECTORIES.length;
  return (
    <div className="space-y-5">
      <Badge tone={full ? "closed" : "neutral"}>
        {full ? "full succession" : "partial succession"}
      </Badge>
      <ul className="grid gap-2 sm:grid-cols-2">
        {SELLABLE_DIRECTORIES.map((directory) => {
          const on = offered.includes(directory);
          return (
            <li key={directory} className="flex items-baseline gap-3">
              <span
                aria-hidden
                className={`font-mono text-label ${on ? "text-closed" : "text-faint"}`}
              >
                {on ? "✓" : "✕"}
              </span>
              <span className={`evidence-type text-micro ${on ? "text-ink" : "text-faint"}`}>
                {directory}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="max-w-measure text-micro text-muted">
        A directory is the unit of selection and receives its own Merkle subroot,
        so a partial succession is verifiable on its own terms rather than as a
        claim about a whole that was never delivered.
        {held.length ? " Directories with nothing on offer are held back." : ""}
      </p>
    </div>
  );
}

// --- valuation -----------------------------------------------------------

/**
 * The formula, with its working shown. Nothing here is a marketing figure: each
 * factor names the input it read, the multiplier it produced and the rule it
 * applied, so the total can be recomputed by hand from the same package.
 */
export function ValuationBreakdown({ row }: { row: MarketRow }) {
  const valuation = (row.preview as Preview | undefined)?.valuation;
  if (!valuation) {
    return (
      <p className="max-w-measure text-micro text-muted">
        No valuation was published with this listing. The asking price stands on
        its own, which is a weaker claim and is shown as one.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
        <span className="tnum text-display text-ink">
          {valuation.currency === "USD" ? "$" : ""}
          {valuation.amount}
        </span>
        <span className="font-mono text-label uppercase tracking-[0.14em] text-faint">
          computed valuation
        </span>
      </div>

      <div className="rail overflow-x-auto">
        <code className="whitespace-nowrap text-micro text-muted">
          {valuation.formula}
        </code>
      </div>

      <div className="border-t border-hairline">
        <div className="flex items-baseline justify-between gap-6 border-b border-hairline py-4">
          <span className="font-mono text-label uppercase tracking-[0.14em] text-faint">
            base price
          </span>
          <span className="tnum text-body text-ink">{valuation.base_price}</span>
        </div>
        {valuation.factors.map((factor) => (
          <Disclose
            key={factor.name}
            summary={
              <span className="flex flex-wrap items-baseline gap-x-5">
                <span className="evidence-type text-body text-ink">
                  {factor.name.replace(/_/g, " ")}
                </span>
                <span className="tnum text-micro text-signal">× {factor.value}</span>
              </span>
            }
          >
            <div className="max-w-reading space-y-3 text-micro text-muted">
              <p>{factor.explanation}</p>
              <dl className="grid grid-cols-2 gap-x-8 gap-y-2 sm:grid-cols-3">
                {Object.entries(factor.inputs ?? {}).map(([key, value]) => (
                  <Stat key={key} label={key.replace(/_/g, " ")} value={String(value)} />
                ))}
              </dl>
            </div>
          </Disclose>
        ))}
      </div>

      <div>
        <h4 className="font-mono text-label uppercase tracking-[0.14em] text-faint">
          Deliberately not in the formula
        </h4>
        <dl className="mt-3 space-y-2">
          {Object.entries(valuation.excluded).map(([key, why]) => (
            <div key={key} className="flex flex-wrap gap-x-4 text-micro">
              <dt className="evidence-type text-muted">{key.replace(/_/g, " ")}</dt>
              <dd className="text-faint">{why}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

// --- reputation ----------------------------------------------------------

export function ReputationPanel({ reputation }: { reputation: Reputation | null | undefined }) {
  if (!reputation) {
    return (
      <p className="max-w-measure text-micro text-muted">
        No reputation is claimed for this listing. The score is derived from a
        provenance chain, and an origin memory that has never changed hands has
        no chain to derive one from.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
        <span className="tnum text-display text-ink">{reputation.score}</span>
        <Badge>{reputation.grade}</Badge>
        <span className="font-mono text-label uppercase tracking-[0.14em] text-faint">
          {reputation.links} verified handover{reputation.links === 1 ? "" : "s"}
        </span>
      </div>

      <div className="border-t border-hairline">
        {reputation.factors.map((factor) => (
          <div
            key={factor.name}
            className="flex flex-wrap items-baseline gap-x-6 gap-y-1 border-b border-hairline py-4"
          >
            <span className="evidence-type w-48 shrink-0 text-micro text-ink">
              {factor.name.replace(/_/g, " ")}
            </span>
            <span className="tnum w-16 shrink-0 text-micro text-muted">
              {factor.value}
            </span>
            <span className="tnum w-16 shrink-0 text-micro text-faint">
              × {factor.weight}
            </span>
            <span className="min-w-0 flex-1 text-micro text-muted">
              {factor.explanation}
            </span>
          </div>
        ))}
      </div>

      <p className="max-w-measure text-micro text-muted">{reputation.basis}</p>
    </div>
  );
}

// --- integrity and provenance -------------------------------------------

export function MerkleRoot({
  manifest,
  committed,
}: {
  manifest: IntegrityManifest | undefined;
  committed: string;
}) {
  if (!manifest?.root) {
    return (
      <div className="space-y-4">
        <p className="max-w-measure text-micro text-muted">
          This seller published no Merkle manifest, so the per-directory subroots
          are not available before purchase. The commitment below is still on
          chain and still binding.
        </p>
        <Field label="Committed on chain" value={committed} />
      </div>
    );
  }

  const agrees = manifest.root.toLowerCase() === committed.toLowerCase();

  return (
    <div className="space-y-6">
      <p className="max-w-measure text-micro text-muted">
        Two levels over keccak256, domain separated the way RFC 6962 separates
        leaves from nodes. Records hash into a subroot per directory, and the
        subroots hash into the one root the contract holds. An odd node is
        promoted rather than duplicated, and a directory's name is bound into its
        own leaf, so a category cannot be relabelled without changing the root.
      </p>

      <div className="border-t border-hairline">
        <Field label="Global root" value={manifest.root} />
        <Field label="Committed on chain" value={committed} />
        <div className="flex items-baseline justify-between gap-6 border-b border-hairline py-4">
          <span className="font-mono text-label uppercase tracking-[0.14em] text-faint">
            Agreement
          </span>
          <Badge tone={agrees ? "closed" : "void"}>
            {agrees ? "manifest matches the chain" : "manifest disagrees with the chain"}
          </Badge>
        </div>
      </div>

      {manifest.categories?.length ? (
        <div>
          <h4 className="mb-3 font-mono text-label uppercase tracking-[0.14em] text-faint">
            Subroots, {manifest.leaf_count} leaves in total
          </h4>
          <div className="border-t border-hairline">
            {manifest.categories.map((entry) => (
              <div
                key={entry.category}
                className="flex flex-wrap items-baseline gap-x-6 gap-y-1 border-b border-hairline py-3"
              >
                <span className="evidence-type w-44 shrink-0 text-micro text-ink">
                  {entry.category}
                </span>
                <span className="tnum w-16 shrink-0 text-micro text-faint">
                  {entry.leaf_count}
                </span>
                <span className="evidence-type min-w-0 flex-1 truncate text-micro text-muted">
                  <Hash value={entry.subroot} chars={10} />
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 border-b border-hairline py-4 sm:flex-row sm:items-baseline sm:gap-8">
      <span className="w-full shrink-0 font-mono text-label uppercase tracking-[0.14em] text-faint sm:w-52">
        {label}
      </span>
      <span className="evidence-type min-w-0 break-all text-micro text-ink">
        {value}
      </span>
    </div>
  );
}

/**
 * Ownership, in order. The chain continues past acquisition: a buyer who
 * resells extends this same list rather than starting a new one, which is what
 * makes the history worth anything.
 */
export function ProvenanceTimeline({
  header,
  listing,
}: {
  header: ProvenanceHeader | undefined;
  listing: Listing;
}) {
  const chain = header?.provenance_chain ?? [];

  if (!header?.agent_identity) {
    return (
      <p className="max-w-measure text-micro text-muted">
        No provenance header was published with this listing. What is on chain
        remains: the commitment, the seller and, once settled, the transaction
        that moved it.
      </p>
    );
  }

  const events = [
    {
      title: "Origin",
      detail: `${header.agent_identity} began accumulating memory.`,
      stamp: header.created_at ?? "",
    },
    ...chain.map((link) => ({
      title: `Acquired by ${link.owner}`,
      detail: `Re-derived root ${link.verified_hash.slice(0, 18)}…${
        link.memory_version === undefined ? "" : ` at version ${link.memory_version}`
      }`,
      stamp: link.acquired_at,
    })),
    {
      title: "Listed",
      detail: `Root committed to the contract at ${listing.hash_commitment.slice(0, 18)}…`,
      stamp: listing.created_at || "",
    },
    ...(listing.state === "confirmed"
      ? [
          {
            title: "Settled",
            detail:
              "Delivered root matched the commitment. Payment released, identity transferred, seller sealed.",
            stamp: listing.settled_at || "",
          },
        ]
      : []),
  ];

  return (
    <ol className="border-t border-hairline">
      {events.map((event, i) => (
        <li key={i} className="flex gap-6 border-b border-hairline py-5">
          <span
            aria-hidden
            className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-signal"
          />
          <div className="min-w-0">
            <div className="text-body text-ink">{event.title}</div>
            <div className="mt-1 max-w-measure text-micro text-muted">
              {event.detail}
            </div>
            {event.stamp ? (
              <div className="tnum mt-1 text-micro text-faint">{event.stamp}</div>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}

// --- privacy -------------------------------------------------------------

/**
 * Two independent axes, and the reason they are independent is the part people
 * get wrong: a private record can still be sold, and a record marked
 * non-transferable cannot be, at any price, by anyone.
 */
export function PrivacyControls({ row }: { row: MarketRow }) {
  const preview = row.preview as Preview | undefined;
  const inventory = preview?.inventory ?? {};
  const noConsent = Object.values(inventory).reduce(
    (sum, entry) => sum + entry.withheld_without_consent,
    0,
  );
  const bySeller = Object.values(inventory).reduce(
    (sum, entry) => sum + entry.withheld_by_seller,
    0,
  );

  return (
    <div className="space-y-8">
      <div className="grid gap-8 sm:grid-cols-2">
        <Panel className="p-6">
          <Block label="Sensitivity">
            <ul className="space-y-2 text-micro text-muted">
              <li>Public, visible in the preview.</li>
              <li>Private, counted but never shown before purchase.</li>
              <li>Redacted preview only, summarised and never quoted.</li>
            </ul>
          </Block>
        </Panel>
        <Panel className="p-6">
          <Block label="Transferability">
            <ul className="space-y-2 text-micro text-muted">
              <li>Transferable, moves with the sale.</li>
              <li>
                Not transferable, absolute. No category selection and no buyer
                can override it.
              </li>
            </ul>
          </Block>
        </Panel>
      </div>

      <p className="max-w-reading text-micro text-muted">
        The two are separate on purpose. Private does not imply non-transferable:
        a customer record can be confidential and still be part of what is being
        sold. Non-transferable is the absolute one, and it is enforced before
        hashing, so a withheld record never enters the Merkle tree and cannot be
        delivered by accident.
      </p>

      <dl className="grid gap-8 sm:grid-cols-2">
        <Stat label="Withheld, no consent" value={noConsent.toLocaleString()} />
        <Stat label="Withheld by the seller" value={bySeller.toLocaleString()} />
      </dl>
    </div>
  );
}

// --- known limits --------------------------------------------------------

export function KnownLimit({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="border-l-2 border-rule pl-6">
      <h4 className="text-body text-ink">{title}</h4>
      <div className="mt-2 max-w-reading text-micro text-muted">{children}</div>
    </div>
  );
}
