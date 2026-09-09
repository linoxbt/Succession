/**
 * One listing, inspected the way an acquisition is inspected.
 *
 * The buyer's half of the sale splits across two places, and this page is
 * explicit about where the line falls. Funding escrow is an on-chain action
 * their wallet takes from here. Importing what they bought writes into *their*
 * Sibyl store, which is a file on their machine, so it happens in their
 * terminal, and the page hands over the exact command rather than pretending a
 * web page could do it.
 *
 * **Two lanes, and the distinction is load bearing.** The contract knows four
 * states: open, escrowed, confirmed, refunded. Everything between funding and
 * settlement — delivery, import, re-derivation — happens off chain and the
 * contract cannot see it. So settlement state is shown as what it is, read from
 * the chain, and the delivery steps are shown separately and marked as not yet
 * settled. Nothing on this page may suggest ownership has moved before
 * `confirmTransfer` has, because until then it has not.
 */
import { useState } from "react";

import { formatAmount, type MarketRow } from "../api";
import { shellArgument } from "../app/commands";
import { ClaimAuthorization, EscrowRecovery, FundEscrow, type ChainStatus } from "../chain/Wallet";
import { Button, Copyable, Note, Section } from "../ui";
import {
  AgentIdentity,
  EscrowStatus,
  MemoryPackageViewer,
  MemoryStats,
  MerkleRoot,
  PrivacyControls,
  ProvenanceTimeline,
  ReputationPanel,
  SealStatus,
  STATE_MEANING,
  TransferScope,
  ValuationBreakdown,
  VerificationBadge,
} from "../app/domain";
import { Block, Panel, Steps, Tabs, type StepState } from "../app/ui";

type Tab = "memory" | "package" | "valuation" | "integrity" | "provenance" | "privacy";

/**
 * The delivery lane. Derived from what the chain says plus what the buyer has
 * actually done, and deliberately conservative: a step is only `done` when
 * there is evidence for it, never because the previous one finished.
 */
function deliverySteps(row: MarketRow): { index: string; title: string; state: StepState; detail?: string }[] {
  const { listing } = row;
  const escrowed = listing.state === "escrowed";
  const settled = listing.state === "confirmed";
  const refunded = listing.state === "refunded";
  const delivered = Boolean(listing.delivered_hash);

  const at = (done: boolean, active: boolean): StepState =>
    done ? "done" : active ? "active" : "waiting";

  return [
    {
      index: "1",
      title: "Escrow funded",
      state: refunded ? "failed" : at(escrowed || settled, listing.state === "open"),
      detail:
        listing.state === "open"
          ? "The contract holds nothing yet. Funding is the first irreversible step."
          : undefined,
    },
    {
      index: "2",
      title: "Evaluator verifies delivery",
      state: at(settled, escrowed),
      detail:
        escrowed && !delivered
          ? "The configured evaluator imports into an isolated store and checks the signature and root."
          : undefined,
    },
    {
      index: "3",
      title: "Evaluator root re-derived",
      state: at(settled, escrowed),
      detail:
        "The evaluator derives the root from its imported store, not from the bytes that arrived.",
    },
    {
      index: "4",
      title: "Settled on chain",
      state: refunded ? "failed" : at(settled, escrowed && delivered),
      detail: refunded
        ? "The hash did not match, or the listing was cancelled. The buyer was made whole."
        : settled
          ? "Payment released, identity transferred, seller's copy sealed."
          : "Ownership has not moved until this transaction confirms.",
    },
  ];
}

export default function ListingView({
  row,
  loading = false,
  error,
  chainStatus,
  onBack,
  onClaim,
  onRefresh,
}: {
  row: MarketRow | null;
  loading?: boolean;
  error?: string;
  chainStatus: ChainStatus | null;
  onBack: () => void;
  onClaim: () => void;
  onRefresh: () => void;
}) {
  // Which of the buyer's agents inherits this memory. Empty until they pick,
  // and the claim command says so rather than defaulting to a placeholder that
  // would import into the wrong tenant if pasted unread.
  const [successor, setSuccessor] = useState("succession-import");
  const [tab, setTab] = useState<Tab>("memory");

  if (!row && loading) return <Note>Loading listing…</Note>;
  if (!row && error) return <Note>Could not load this listing: {error} <Button onClick={onRefresh}>Retry</Button></Note>;
  if (!row) {
    return (
      <Note>
        No listing at this address. It may have been unpublished, or the id may
        be wrong.{" "}
        <button onClick={onBack} className="link-underline text-ink">
          Back to the marketplace
        </button>
        .
      </Note>
    );
  }

  const { listing, preview } = row;
  const deployment = chainStatus?.deployment ?? null;
  const isDemo = Boolean(row.demo);

  return (
    <div>
      {/* --- identity and position --------------------------------------- */}
      <header className="pb-beat">
        <button
          onClick={onBack}
          className="link-underline text-micro font-medium text-muted hover:text-ink"
        >
          Back to marketplace
        </button>

        <div className="mt-8 grid gap-10 lg:grid-cols-[1fr_auto] lg:items-end">
          <AgentIdentity row={row} />

          <div className="lg:text-right">
            <div className="tnum text-display text-ink">
              {formatAmount(listing.price, listing.currency)}
            </div>
            {row.valuation ? (
              <div className="tnum mt-1 text-micro text-faint">
                computed valuation ${row.valuation}
              </div>
            ) : null}
          </div>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
          <EscrowStatus listing={listing} />
          <VerificationBadge row={row} />
        </div>

        <p className="mt-5 max-w-measure text-micro text-muted">
          {STATE_MEANING[listing.state] ?? ""}
        </p>

        {isDemo ? (
          <Note>
            {row.notice ??
              "Demonstration listing. Not on chain, not for sale, and excluded from every figure this marketplace reports."}
          </Note>
        ) : null}
      </header>

      {/* --- what is being acquired -------------------------------------- */}
      <Section index="01" title="What you are acquiring">
        <div className="grid gap-12 lg:grid-cols-[1fr_20rem]">
          <div>
            <Tabs<Tab>
              active={tab}
              onSelect={setTab}
              tabs={[
                { id: "memory", label: "Memory" },
                { id: "package", label: "Package" },
                { id: "valuation", label: "Valuation" },
                { id: "integrity", label: "Integrity" },
                { id: "provenance", label: "Provenance" },
                { id: "privacy", label: "Privacy" },
              ]}
            />

            <div className="pt-10">
              {tab === "memory" ? (
                <div className="space-y-12">
                  <MemoryStats row={row} />
                  <Block label="Track record">
                    <ReputationPanel reputation={preview?.reputation} />
                  </Block>
                </div>
              ) : null}

              {tab === "package" ? (
                <div className="space-y-8">
                  <p className="max-w-reading text-micro text-muted">
                    The memory is exported into a Succession Memory Package. Six
                    directories carry memory and are the units of selection; three
                    are generated to describe the package rather than to be part
                    of it. Record bodies are withheld until purchase and hash
                    verification, so what follows is counts and roots.
                  </p>
                  <MemoryPackageViewer row={row} />
                </div>
              ) : null}

              {tab === "valuation" ? <ValuationBreakdown row={row} /> : null}

              {tab === "integrity" ? (
                <MerkleRoot
                  manifest={row.integrity}
                  committed={listing.hash_commitment}
                />
              ) : null}

              {tab === "provenance" ? (
                <ProvenanceTimeline header={row.provenance} listing={listing} />
              ) : null}

              {tab === "privacy" ? <PrivacyControls row={row} /> : null}
            </div>
          </div>

          {/* --- the standing summary ------------------------------------ */}
          <aside className="space-y-8 lg:sticky lg:top-32 lg:self-start">
            <Panel className="p-7">
              <Block label="Transfer scope">
                <TransferScope row={row} />
              </Block>
            </Panel>

            <Panel className="p-7">
              <Block label="After settlement">
                <SealStatus listing={listing} />
              </Block>
            </Panel>
          </aside>
        </div>
      </Section>

      {/* --- where the sale stands --------------------------------------- */}
      <Section index="02" title="Where this sale stands" className="mt-chapter">
        <div className="grid gap-12 lg:grid-cols-2">
          <div>
            <Block label="Settlement state, read from the contract">
              <div className="space-y-4">
                <EscrowStatus listing={listing} />
                <p className="max-w-measure text-micro text-muted">
                  {STATE_MEANING[listing.state]}
                </p>
                <p className="max-w-measure text-micro text-faint">
                  The contract holds four states. Everything between funding and
                  settlement happens off chain, so it is tracked beside this
                  rather than inside it.
                </p>
              </div>
            </Block>
          </div>

          <div>
            <Block label="Delivery progress, off chain">
              <Steps steps={deliverySteps(row)} />
            </Block>
          </div>
        </div>
      </Section>

      {/* --- the transactional half -------------------------------------- */}
      {isDemo ? (
        <Section index="03" title="Acquisition" className="mt-chapter">
          <Note>
            This listing is a demonstration and has no seller. Its address is the
            zero address, which no key produces, so no transaction against it
            could be authorised even if this button existed.
          </Note>
        </Section>
      ) : (
        <>
          {deployment && listing.state === "open" ? (
            <Section index="03" title="Fund escrow" className="mt-chapter">
              <p className="mb-8 max-w-measure text-body text-muted">
                Two transactions, shown as two: approve the payment token, then
                fund. The money is held by the contract and goes to the seller
                only when a matching hash is confirmed, or back to you if it is
                not.
              </p>
              {row.has_envelope ? <FundEscrow
                deployment={deployment}
                listingId={listing.listing_id}
                price={BigInt(listing.price)}
                onFunded={onRefresh}
              /> : <Note>The seller has not published the encrypted deliverable. Funding is unavailable until it is published.</Note>}
            </Section>
          ) : null}

          {listing.state === "escrowed" ? (
            <Section index="04" title="Independent evaluation" className="mt-chapter">
              <p className="mb-8 max-w-measure text-body text-muted">
                Your escrow is funded. The content key is available only to the
                evaluator configured in the contract. It imports the package,
                checks the seller signature, re-derives the root, and settles
                only a verified delivery.
              </p>
              <Note>
                The buyer cannot collect plaintext or submit a delivery root
                while a refund remains possible. You may reclaim expired escrow
                if evaluation never completes.
              </Note>
            </Section>
          ) : null}

          {listing.state === "confirmed" ? (
            <Section index="05" title="Claim evaluator-approved memory" className="mt-chapter">
              <label className="block text-body">Fresh destination tenant
                <input aria-label="Destination tenant" value={successor} onChange={e => setSuccessor(e.target.value)} maxLength={128} className="mt-3 block w-full border border-rule p-3" />
              </label>
              <Note>Payment and identity transfer are confirmed. The buyer may now collect the key and import into a fresh local tenant.</Note>
              {deployment ? <ClaimAuthorization deployment={deployment} listing={listing} /> : null}
              <div className="mt-10"><Copyable text={`succession claim \\
    --listing ${shellArgument(listing.listing_id)} \\
    --db ~/.sibyl-memory/memory.db \\
    --tenant ${shellArgument(successor.trim() || "succession-import")} \\
    --marketplace ${shellArgument(window.location.origin)}`} /></div>
              <div className="mt-4"><Button size="sm" variant="quiet" onClick={onClaim}>Full instructions</Button></div>
            </Section>
          ) : null}
          {deployment ? <EscrowRecovery deployment={deployment} listing={listing} onChanged={onRefresh} /> : null}
        </>
      )}
    </div>
  );
}
