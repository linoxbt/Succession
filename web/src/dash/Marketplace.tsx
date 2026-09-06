/**
 * The marketplace.
 *
 * This is the screen the product is judged on, so it opens with the claim and
 * then supports it with the actual market rather than with argument. What
 * follows the grid explains why memory has value and how a sale executes,
 * because a buyer arriving here has usually never seen an asset of this kind
 * and the alternative to explaining is hoping.
 *
 * Real listings come first and demonstration listings after, in their own
 * band, under their own heading. The service keeps the two in separate fields
 * so no total can count a demo row; this screen keeps them in separate bands so
 * no reader can mistake one for the other.
 */
import { useMemo, useState } from "react";

import type { MarketRow } from "../api";
import { useNavigation } from "../router";
import { Button, Empty, Note, Section } from "../ui";
import { Reveal } from "../motion";
import ListingCard from "../app/ListingCard";
import { Panel, Select, Skeleton, TextInput } from "../app/ui";
import { KnownLimit, SELLABLE_DIRECTORIES } from "../app/domain";
import {
  activeCount,
  apply,
  EMPTY,
  fromQuery,
  toQuery,
  type Filters,
} from "../app/filters";

const WHY = [
  ["Tenure", "Time is the one input an agent cannot be given at launch."],
  ["Relationships", "Counterparties, and the terms each of them has accepted."],
  ["Experience", "What was tried, what settled, and what did not."],
  ["Preferences", "Standing choices, learned rather than configured."],
  ["Learned behaviour", "Heuristics adapted in operation, not shipped in code."],
  ["Performance", "Resolved outcomes, verifiable against the ACP contract."],
  ["Provenance", "Who held it before, and whether each handover verified."],
] as const;

const HOW = [
  ["01", "Export", "The seller's tenant is filtered, serialised and hashed into a package."],
  ["02", "List", "The Merkle root is committed to the contract on Base."],
  ["03", "Preview", "The buyer sees aggregate statistics and verifiable history."],
  ["04", "Escrow", "The buyer funds the contract. Nothing has moved yet."],
  ["05", "Deliver", "The encrypted package travels to the buyer."],
  ["06", "Re-key", "It imports into a new tenant under the buyer's own id."],
  ["07", "Verify", "The buyer re-exports their store and re-derives the root."],
  ["08", "Settle", "confirmTransfer pays, moves the identity and seals the seller."],
  ["09", "Record", "The acquisition becomes part of the provenance chain."],
] as const;

export default function Marketplace({
  rows,
  demo,
  onChain,
  loading,
  onOpen,
  onSell,
  onRefresh,
}: {
  rows: MarketRow[];
  demo: MarketRow[];
  onChain: boolean | null;
  loading: boolean;
  onOpen: (row: MarketRow) => void;
  onSell: () => void;
  onRefresh: () => void;
}) {
  const { query, setQuery } = useNavigation();
  const filters = useMemo(() => fromQuery(query), [query]);
  const [open, setOpen] = useState(false);

  const set = (patch: Partial<Filters>) =>
    setQuery(toQuery({ ...filters, ...patch }));

  const visible = useMemo(() => apply(rows, filters), [rows, filters]);
  const visibleDemo = useMemo(() => apply(demo, filters), [demo, filters]);
  const active = activeCount(filters);

  return (
    <div>
      {/* --- the claim ---------------------------------------------------- */}
      <header className="max-w-wide pb-beat">
        <Reveal>
          <p className="chapter-mark">01 / Marketplace</p>
          <h1 className="display-type mt-6 max-w-reading text-display text-ink">
            What an agent learned outlives the agent.
          </h1>
          <p className="mt-8 max-w-measure text-lede text-muted">
            Agent memory with verifiable provenance, transferable identity and
            cryptographic integrity, settled on Base.
          </p>
        </Reveal>
        <div className="mt-10 flex flex-wrap items-center gap-4">
          <Button onClick={() => setOpen((v) => !v)}>Explore listings</Button>
          <Button variant="ghost" onClick={onSell}>
            Sell agent memory
          </Button>
        </div>
      </header>

      {/* --- search and filters ------------------------------------------- */}
      <Section index="02" title="Live marketplace" action={
        <button
          onClick={onRefresh}
          className="link-underline font-mono text-label uppercase text-muted hover:text-ink"
        >
          Refresh
        </button>
      }>
        {onChain === false ? (
          <Note>
            No contract is being read, so there is no live market to show. What
            follows is demonstration data and is labelled as such.
          </Note>
        ) : null}

        <div className="mb-10 grid gap-6 lg:grid-cols-[1fr_auto_auto]">
          <TextInput
            label="Search"
            type="search"
            value={filters.q}
            onChange={(q) => set({ q })}
            placeholder="Agent name, identity, owner, listing id, or committed hash"
          />
          <Select
            label="Sort"
            value={filters.sort}
            onChange={(sort) => set({ sort })}
            options={[
              { value: "price-desc", label: "Price, high to low" },
              { value: "price-asc", label: "Price, low to high" },
              { value: "records-desc", label: "Most memory" },
              { value: "age-desc", label: "Longest tenure" },
            ]}
          />
          <div className="flex items-end">
            <Button variant="ghost" onClick={() => setOpen((v) => !v)}>
              Filters{active ? ` (${active})` : ""}
            </Button>
          </div>
        </div>

        {open ? (
          <Panel className="mb-10 p-7">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              <Select
                label="Transfer scope"
                value={filters.scope}
                onChange={(scope) => set({ scope })}
                options={[
                  { value: "any", label: "Any" },
                  { value: "full", label: "Full succession" },
                  { value: "partial", label: "Partial succession" },
                ]}
              />
              <Select
                label="Verification"
                value={filters.verified}
                onChange={(verified) => set({ verified })}
                options={[
                  { value: "any", label: "Any" },
                  { value: "verified", label: "Manifest published" },
                  { value: "unverified", label: "No manifest" },
                ]}
              />
              <Select
                label="Memory age"
                value={filters.age}
                onChange={(age) => set({ age })}
                options={[
                  { value: "any", label: "Any" },
                  { value: "under3", label: "Under 3 months" },
                  { value: "3to6", label: "3 to 6 months" },
                  { value: "6to12", label: "6 to 12 months" },
                  { value: "over12", label: "Over a year" },
                ]}
              />
              <Select
                label="Interaction density"
                value={filters.density}
                onChange={(density) => set({ density })}
                options={[
                  { value: "any", label: "Any" },
                  { value: "low", label: "Low" },
                  { value: "medium", label: "Medium" },
                  { value: "high", label: "High" },
                ]}
              />
              <Select
                label="Relationship breadth"
                value={filters.breadth}
                onChange={(breadth) => set({ breadth })}
                options={[
                  { value: "any", label: "Any" },
                  { value: "low", label: "Low" },
                  { value: "medium", label: "Medium" },
                  { value: "high", label: "High" },
                ]}
              />
              <Select
                label="Performance"
                value={filters.performance}
                onChange={(performance) => set({ performance })}
                options={[
                  { value: "any", label: "Any" },
                  { value: "low", label: "Low" },
                  { value: "medium", label: "Medium" },
                  { value: "high", label: "High" },
                ]}
              />
              <Select
                label="Status"
                value={filters.state}
                onChange={(state) => set({ state })}
                options={[
                  { value: "any", label: "Any" },
                  { value: "open", label: "Available" },
                  { value: "escrowed", label: "Escrowed" },
                  { value: "confirmed", label: "Transferred" },
                  { value: "refunded", label: "Refunded" },
                ]}
              />
              <div className="flex items-end">
                <Button variant="quiet" onClick={() => setQuery(toQuery(EMPTY))}>
                  Clear filters
                </Button>
              </div>
            </div>
            <p className="mt-6 max-w-reading text-micro text-faint">
              Bands are fixed thresholds, not percentiles of what is currently
              shown, so a listing does not change band because another was
              filtered out. A listing that publishes no data room cannot satisfy
              a filter that reads one, and is excluded rather than guessed at.
            </p>
          </Panel>
        ) : null}

        {loading ? (
          <Skeleton rows={4} />
        ) : rows.length === 0 && onChain !== false ? (
          <Empty>
            No listings on this contract yet. A listing exists here because a
            seller committed its root on chain, so an empty market is a true
            answer rather than a missing fetch.
          </Empty>
        ) : visible.length === 0 ? (
          <Empty>
            Nothing matches these filters.{" "}
            <button
              onClick={() => setQuery(toQuery(EMPTY))}
              className="link-underline text-ink"
            >
              Clear them
            </button>
            .
          </Empty>
        ) : (
          <>
            <p className="mb-8 font-mono text-label uppercase tracking-[0.14em] text-faint">
              {visible.length} of {rows.length} listing
              {rows.length === 1 ? "" : "s"}
            </p>
            <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {visible.map((row, i) => (
                <Reveal key={row.listing.listing_id} index={i % 3}>
                  <ListingCard row={row} onOpen={onOpen} />
                </Reveal>
              ))}
            </div>
          </>
        )}
      </Section>

      {/* --- the demonstration band --------------------------------------- */}
      {visibleDemo.length ? (
        <Section index="03" title="Demonstration listings" className="mt-chapter">
          <Note>
            These are not real. They exist so the interface can be judged at a
            realistic size while the live market is small. None of them is on
            chain, none can be bought, and none is counted in any figure this
            marketplace reports.
          </Note>
          <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {visibleDemo.map((row, i) => (
              <Reveal key={row.listing.listing_id} index={i % 3}>
                <ListingCard row={row} onOpen={onOpen} />
              </Reveal>
            ))}
          </div>
        </Section>
      ) : null}

      {/* --- why memory has value ----------------------------------------- */}
      <Section index="04" title="Why memory has value" className="mt-chapter">
        <p className="mb-12 max-w-measure text-lede text-muted">
          Code gives an agent capability. A model gives it reasoning. Memory
          gives it continuity, and continuity is the part that cannot be
          reproduced by starting a new one.
        </p>
        <dl className="grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
          {WHY.map(([term, line], i) => (
            <Reveal key={term} index={i % 3}>
              <dt className="text-body text-ink">{term}</dt>
              <dd className="mt-1 max-w-measure text-micro text-muted">{line}</dd>
            </Reveal>
          ))}
        </dl>
      </Section>

      {/* --- how a sale works --------------------------------------------- */}
      <Section index="05" title="How a sale works" className="mt-chapter">
        <ol className="grid gap-px border border-hairline bg-hairline sm:grid-cols-2 lg:grid-cols-3">
          {HOW.map(([index, title, line]) => (
            <li key={index} className="bg-paper p-7">
              <span className="font-mono text-label uppercase tracking-[0.14em] text-signal">
                {index}
              </span>
              <h3 className="mt-3 text-body text-ink">{title}</h3>
              <p className="mt-2 text-micro text-muted">{line}</p>
            </li>
          ))}
        </ol>
      </Section>

      {/* --- what is verifiable, and what is not -------------------------- */}
      <Section index="06" title="Cryptographically verifiable" className="mt-chapter">
        <div className="grid gap-12 lg:grid-cols-2">
          <div className="space-y-8">
            <dl className="space-y-6">
              <div>
                <dt className="text-body text-ink">Merkle root</dt>
                <dd className="mt-1 max-w-measure text-micro text-muted">
                  Two levels over keccak256, one subroot per directory, committed
                  before a buyer exists. Each of the {SELLABLE_DIRECTORIES.length}{" "}
                  sellable directories can be checked on its own.
                </dd>
              </div>
              <div>
                <dt className="text-body text-ink">Signed identity</dt>
                <dd className="mt-1 max-w-measure text-micro text-muted">
                  The provenance header is signed by the seller and names the
                  ERC-8004 identity the sale transfers.
                </dd>
              </div>
              <div>
                <dt className="text-body text-ink">Destination verification</dt>
                <dd className="mt-1 max-w-measure text-micro text-muted">
                  The buyer re-exports their own store after import and derives
                  the root from that, rather than hashing the bytes that arrived.
                  Verifying the delivery would prove only that a file was sent.
                </dd>
              </div>
            </dl>
          </div>

          <div className="space-y-8">
            <h3 className="font-mono text-label uppercase tracking-[0.14em] text-faint">
              Known limits
            </h3>
            <KnownLimit title="The buyer asserts the delivered hash">
              A dishonest buyer can submit an incorrect hash, receive an
              automatic refund and keep the decrypted package. Closing this
              needs an independent attestation of the destination root.
            </KnownLimit>
            <KnownLimit title="Delivery and sealing are not one transaction">
              They are ordered so that no state is unsafe if the sequence stops
              partway, but chain and off-chain storage cannot commit atomically.
            </KnownLimit>
            <KnownLimit title="Counterparty terms are a real question">
              Whether relationship data may move with a sale is a matter of the
              terms each counterparty accepted, and production deployment needs
              an answer to it rather than a default.
            </KnownLimit>
          </div>
        </div>
      </Section>
    </div>
  );
}
