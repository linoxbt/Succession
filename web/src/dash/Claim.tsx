/**
 * Claim: the register of what this wallet owns, and what it still has to do.
 *
 * Two things live here and they are different. **Title** is what has settled:
 * the ERC-8004 identities this wallet holds and the listings the contract
 * records it as the buyer of. **Work outstanding** is a sale that is funded but
 * not finished, where the memory still has to be collected and imported on the
 * owner's own machine before anything can settle.
 *
 * The import cannot happen here. It writes into the buyer's Sibyl store, which
 * is a file on their disk, so this page hands over the command and reports what
 * the chain says about the rest.
 */
import { useEffect, useState } from "react";
import { useAccount } from "wagmi";

import { formatAmount, type AgentsHeld, type MarketRow } from "../api";
import { service } from "../services";
import { explorerAddress } from "../chain/config";
import { Badge, Copyable, Empty, Note, PageHead, Section } from "../ui";
import { Block, CopyLine, Panel, Skeleton } from "../app/ui";
import { EscrowStatus, SealStatus, STATE_MEANING } from "../app/domain";

export default function Claim({
  listingId,
  rows,
  onOpenListing,
}: {
  listingId: string;
  rows: MarketRow[];
  onOpenListing: (listingId: string) => void;
}) {
  const { address, isConnected } = useAccount();
  const [held, setHeld] = useState<AgentsHeld | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!address) {
      setHeld(null);
      return;
    }
    let live = true;
    setLoading(true);
    void service
      .agents(address)
      .then((body) => live && setHeld(body))
      .catch(() => live && setHeld(null))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [address]);

  const mine = address
    ? rows.filter(
        (row) => row.listing.buyer.toLowerCase() === address.toLowerCase(),
      )
    : [];
  const settled = mine.filter((row) => row.listing.state === "confirmed");
  const outstanding = mine.filter((row) => row.listing.state === "escrowed");

  // The listing the user arrived from, when they came via a listing page.
  const arrived = rows.find((row) => row.listing.listing_id === listingId);
  const pending = outstanding.length ? outstanding : arrived ? [arrived] : [];

  return (
    <div>
      <PageHead
        index="04 / Claim"
        title="What this wallet owns."
        lede="A register of title, read from the contract and the identity registry rather than from anything this service stores."
      />

      {/* --- identities held --------------------------------------------- */}
      <Section index="01" title="Agent identities">
        {!isConnected ? (
          <Note>Connect a wallet to read the ERC-8004 agents it holds.</Note>
        ) : loading ? (
          <Skeleton rows={3} />
        ) : !held || held.agents.length === 0 ? (
          <Empty>
            This wallet holds no ERC-8004 agents. An acquired memory is imported
            into an agent you already hold, so a successor has to exist first.
          </Empty>
        ) : (
          <>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {held.agents.map((agent) => (
                <Panel key={agent.identity} className="p-6">
                  <div className="evidence-type text-body text-ink">
                    {agent.identity}
                  </div>
                  <div className="mt-2 font-mono text-label uppercase tracking-[0.14em] text-faint">
                    token {agent.agent_id}
                  </div>
                </Panel>
              ))}
            </div>
            {!held.complete ? (
              <Note>
                Showing {held.found} of {held.balance}. The registry is not
                enumerable, so holdings are reconstructed from transfer logs over
                a bounded range and an older agent can sit outside it. Everything
                listed is confirmed against ownerOf.
              </Note>
            ) : null}
            {address ? (
              <div className="mt-8">
                <CopyLine label="owner" value={address} />
                <a
                  href={explorerAddress(address)}
                  target="_blank"
                  rel="noreferrer"
                  className="link-underline mt-3 inline-block font-mono text-label uppercase text-muted hover:text-ink"
                >
                  View on Basescan
                </a>
              </div>
            ) : null}
          </>
        )}
      </Section>

      {/* --- settled acquisitions ---------------------------------------- */}
      <Section index="02" title="Memory acquired" className="mt-chapter">
        {!isConnected ? (
          <Note>Connect a wallet to see what it has acquired.</Note>
        ) : settled.length === 0 ? (
          <Empty>
            No settled acquisitions. A sale appears here once confirmTransfer has
            matched the delivered root and released payment, and not before.
          </Empty>
        ) : (
          <div className="border-t border-hairline">
            {settled.map((row) => (
              <div
                key={row.listing.listing_id}
                className="flex flex-wrap items-baseline gap-x-8 gap-y-3 border-b border-hairline py-6"
              >
                <div className="min-w-0 flex-1">
                  <button
                    onClick={() => onOpenListing(row.listing.listing_id)}
                    className="link-underline text-body text-ink"
                  >
                    {row.name || `Agent ${row.listing.agent_id}`}
                  </button>
                  <div className="evidence-type mt-1 truncate text-micro text-faint">
                    {row.agent_identity}
                  </div>
                </div>
                <span className="tnum text-micro text-muted">
                  {formatAmount(row.listing.price, row.listing.currency)}
                </span>
                <Badge tone="closed">title transferred</Badge>
                {row.listing.sealed ? <Badge tone="closed">origin sealed</Badge> : null}
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* --- work outstanding -------------------------------------------- */}
      <Section index="03" title="Outstanding" className="mt-chapter">
        {pending.length === 0 ? (
          <Note>
            Nothing is waiting on you. A funded escrow appears here with the
            command that collects and imports what it paid for.
          </Note>
        ) : (
          <div className="space-y-12">
            {pending.map((row) => (
              <Panel key={row.listing.listing_id} className="p-7">
                <Block
                  label={row.name || row.listing.listing_id}
                  action={<EscrowStatus listing={row.listing} />}
                >
                  <p className="max-w-measure text-micro text-muted">
                    {STATE_MEANING[row.listing.state]}
                  </p>

                  <div className="mt-8 space-y-6">
                    <div>
                      <p className="chapter-mark mb-3">1, Install</p>
                      <Copyable text="pipx install succession" />
                    </div>

                    <div>
                      <p className="chapter-mark mb-3">
                        2, Claim, import and verify
                      </p>
                      <Copyable
                        text={`succession claim \\
    --listing ${row.listing.listing_id} \\
    --db ~/.sibyl-memory/memory.db \\
    --tenant <the agent that inherits>`}
                      />
                      <Note>
                        It prints the hash the seller committed and the one
                        re-derived from your own store after the import. The
                        second is derived from what you now hold, not from the
                        bytes that arrived, which is the only version of the
                        check worth running.
                      </Note>
                    </div>

                    <div>
                      <p className="chapter-mark mb-3">3, Confirm on chain</p>
                      <p className="max-w-measure text-micro text-muted">
                        Only if the two hashes match. Confirming releases the
                        payment, transfers the identity and seals the seller's
                        copy in one transaction. If they do not match, do not
                        confirm: the refund path exists for exactly this.
                      </p>
                    </div>
                  </div>

                  <div className="mt-8 border-t border-hairline pt-6">
                    <CopyLine
                      label="committed"
                      value={row.listing.hash_commitment}
                    />
                    {row.listing.delivered_hash ? (
                      <div className="mt-3">
                        <CopyLine
                          label="delivered"
                          value={row.listing.delivered_hash}
                        />
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-6">
                    <SealStatus listing={row.listing} />
                  </div>
                </Block>
              </Panel>
            ))}
          </div>
        )}
      </Section>

      <Section index="04" title="If the key is not there yet" className="mt-chapter">
        <p className="max-w-measure text-body text-muted">
          The seller releases the content key only after they have seen your
          escrow on chain themselves, so a short wait is the system working. If
          they never appear, the confirmation window expires and anyone can call{" "}
          <code>reclaimExpired</code> to return your money. You do not need the
          seller's cooperation to get it back.
        </p>
      </Section>
    </div>
  );
}
