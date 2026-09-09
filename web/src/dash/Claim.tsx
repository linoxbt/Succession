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
import { shellArgument } from "../app/commands";
import { useQuery } from "@tanstack/react-query";
import { useAccount } from "wagmi";

import { formatAmount, type MarketRow } from "../api";
import { service } from "../services";
import { explorerAddress } from "../chain/config";
import { Badge, Button, Copyable, Empty, Note, PageHead, Section } from "../ui";
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
  const registry = useQuery({queryKey: ['agents', address], queryFn: () => service.agents(address!), enabled: Boolean(address), retry: 1});
  const held = address ? registry.data : undefined;
  const loading = registry.isFetching;

  const mine = address
    ? rows.filter(
        (row) => row.listing.buyer.toLowerCase() === address.toLowerCase(),
      )
    : [];
  const settled = mine.filter((row) => row.listing.state === "confirmed");
  const outstanding = mine.filter((row) => row.listing.state === "escrowed");

  // The listing the user arrived from, when they came via a listing page.
  const detail = useQuery({queryKey: ['listing', listingId], queryFn: () => service.listing(listingId), enabled: Boolean(listingId), retry: 1});
  const arrived = rows.find((row) => row.listing.listing_id === listingId) || detail.data;
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
        ) : registry.error ? (
          <Note>Could not read the registry: {registry.error.message} <Button onClick={() => { void registry.refetch(); }}>Retry</Button></Note>
        ) : held && !held.complete && held.agents.length === 0 ? (
          <Note>The scan is incomplete: the wallet reports {held.balance} identities, but none were found in this range.</Note>
        ) : !held || held.agents.length === 0 ? (
          <Empty>
            No ERC-8004 identities were found. Claiming memory requires a fresh local tenant; you do not need to register another NFT.
          </Empty>
        ) : (
          <>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {held.agents.map((agent) => (
                <Panel key={agent.identity} className="p-6">
                  <div className="evidence-type text-body text-ink">
                    {agent.identity}
                  </div>
                  <div className="mt-2 text-micro font-medium text-faint">
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
                  className="link-underline mt-3 inline-block text-micro font-medium text-muted hover:text-ink"
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
            No settled acquisitions. A sale appears here once the evaluator has
            matched the delivered root and released payment.
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
                <div className="basis-full pt-3">
                  <Copyable text={`succession claim \\
    --listing ${shellArgument(row.listing.listing_id)} \\
    --db ~/.sibyl-memory/memory.db \\
    --tenant succession-import \\
    --marketplace ${shellArgument(window.location.origin)}`} />
                </div>
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
            evaluator status and recovery controls.
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
                      <Copyable text={'pipx install "succession-cli[chain]"'} />
                    </div>

                    <div>
                      <p className="chapter-mark mb-3">
                        2, Wait for independent evaluation
                      </p>
                      <Note>
                        The configured evaluator alone can collect the key while
                        escrow remains refundable. It imports into an isolated
                        store, checks the seller signature, and re-derives the root.
                      </Note>
                    </div>

                    <div>
                      <p className="chapter-mark mb-3">3, Claim after settlement</p>
                      <p className="max-w-measure text-micro text-muted">
                        A passing evaluator verdict releases payment and transfers
                        the identity in one transaction. The buyer key becomes
                        available only then. Open this listing again to download
                        a wallet authorization and run the claim command.
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
