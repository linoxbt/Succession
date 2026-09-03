/**
 * Screen 2 — escrow in progress.
 *
 * Funds held, transfer pending, and the hash commitment visible and
 * unchangeable. The commitment is shown in full here on purpose: this is the
 * moment a buyer can still check it against what they were shown at listing.
 */
import type { Listing } from "../api";
import { formatAmount } from "../api";
import {
  Button,
  Definition,
  DefinitionList,
  EvidenceStrip,
  Notice,
  Section,
  StateBadge,
} from "./primitives";

export function Escrow({
  listing,
  onExecute,
  busy,
}: {
  listing: Listing;
  onExecute: () => void;
  busy: boolean;
}) {
  return (
    <div className="space-y-10">
      <header className="space-y-4">
        <p className="font-sans text-xs uppercase tracking-[0.16em] text-ink/50">
          Transfer pending
        </p>
        <h1 className="font-serif text-4xl leading-tight">
          Agent #{listing.agent_id.split(":").pop()}
        </h1>
        {/* Colour plus words. The label carries the state on its own. */}
        <StateBadge tone="escrow">Escrow: funds held</StateBadge>
      </header>

      <Section title="Escrow">
        <DefinitionList>
          <Definition label="Amount held">
            {formatAmount(listing.escrow_balance, listing.currency)}
          </Definition>
          <Definition label="Buyer" mono>
            {listing.buyer}
          </Definition>
          <Definition label="Seller" mono>
            {listing.seller}
          </Definition>
          <Definition label="Released on">
            A delivered hash matching the commitment below.
          </Definition>
        </DefinitionList>
      </Section>

      <Section title="Commitment (unchangeable)">
        <EvidenceStrip>
          <Definition label="Committed hash" mono>
            {listing.hash_commitment}
          </Definition>
        </EvidenceStrip>
      </Section>

      <Notice tone="escrow">
        The content key is released only against funded escrow. Payment, the
        ERC-8004 identity, and the seal on the seller&rsquo;s copy all move in a
        single transaction, or none of them do.
      </Notice>

      <div className="pt-2">
        <Button onClick={onExecute} disabled={busy}>
          {busy ? "Executing transfer…" : "Execute transfer"}
        </Button>
      </div>
    </div>
  );
}
