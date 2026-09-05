/**
 * One listing: the data room, then the escrow.
 *
 * The buyer's half of the sale splits across two places, and this page is
 * explicit about where the line falls. Funding escrow is an on-chain action
 * their wallet takes from here. Importing what they bought writes into *their*
 * Sibyl store, which is a file on their machine, so it happens in their
 * terminal, and the page hands over the exact command rather than pretending
 * a web page could do it.
 */
import { formatAmount, type MarketRow } from "../api";
import { ConfirmOnChain, FundEscrow, SettlementMode, type ChainStatus } from "../chain/Wallet";
import {
  Badge,
  Button,
  Copyable,
  Field,
  FieldList,
  FullHash,
  Note,
  Section,
} from "../ui";

export default function ListingView({
  row,
  chainStatus,
  onBack,
  onClaim,
  onRefresh,
}: {
  row: MarketRow | null;
  chainStatus: ChainStatus | null;
  onBack: () => void;
  onClaim: () => void;
  onRefresh: () => void;
}) {
  if (!row) {
    return (
      <Note>
        No listing selected. Choose one from the Marketplace.
      </Note>
    );
  }

  const { listing, preview } = row;
  const records = Object.values(preview?.counts ?? {}).reduce((a, b) => a + b, 0);
  const deployment = chainStatus?.deployment ?? null;

  return (
    <div className="flex flex-col gap-chapter">
      <Section
        title={row.name || row.agent_identity}
        action={
          <Button size="sm" variant="quiet" onClick={onBack}>
            Back to marketplace
          </Button>
        }
      >
        <SettlementMode status={chainStatus} />
      </Section>

      <Section index="01" title="The data room">
        <p className="mb-4 max-w-measure text-body text-muted">
          Aggregate statistics only. The preview is built from counts, so there
          is no record body in scope for it to leak, what is for sale is
          described, never shown.
        </p>
        <FieldList>
          <Field label="Agent identity">{row.agent_identity || "-"}</Field>
          <Field label="Seller">
            <FullHash value={listing.seller} />
          </Field>
          <Field label="Records">{records || "-"}</Field>
          {preview?.memory_size_bytes ? (
            <Field label="Memory size">{preview.memory_size_bytes} bytes</Field>
          ) : null}
          {row.valuation ? (
            <Field label="Reference valuation">${row.valuation}</Field>
          ) : null}
          <Field label="Asking price" emphasis>
            {formatAmount(listing.price, listing.currency)}
          </Field>
          <Field label="State">
            <Badge tone={listing.state === "open" ? "neutral" : "escrow"}>
              {listing.state}
            </Badge>
          </Field>
          <Field label="Committed hash">
            <FullHash value={listing.hash_commitment} />
          </Field>
        </FieldList>
        <Note>
          The hash above was posted at listing time, before this buyer existed.
          That ordering is what makes it a commitment rather than a description.
        </Note>
      </Section>

      {deployment && listing.state === "open" ? (
        <Section index="02" title="Fund escrow">
          <p className="mb-4 max-w-measure text-body text-muted">
            Two transactions, shown as two: approve the payment token, then fund.
            The money is held by the contract and goes to the seller only when a
            matching hash is confirmed, or back to you if it is not.
          </p>
          <FundEscrow
            deployment={deployment}
            listingId={listing.listing_id}
            price={BigInt(listing.price)}
            onFunded={onRefresh}
          />
        </Section>
      ) : null}

      {listing.state === "escrowed" ? (
        <Section index="03" title="Claim what you paid for">
          <p className="mb-4 max-w-measure text-body text-muted">
            Your escrow is funded. Once the seller releases the key, collect and
            import the package on your own machine, the import writes into your
            Sibyl store, which this page cannot reach.
          </p>
          <Copyable
            text={`succession claim \\
    --listing ${listing.listing_id} \\
    --db ~/.sibyl-memory/memory.db \\
    --tenant my-successor-agent`}
          />
          <div className="mt-4">
            <Button size="sm" variant="quiet" onClick={onClaim}>
              Full instructions
            </Button>
          </div>
          <Note>
            It prints the committed hash and the one re-derived from your own
            store after the import. Confirm on chain only if they match.
          </Note>
        </Section>
      ) : null}

      {deployment && listing.state === "escrowed" && listing.delivered_hash ? (
        <Section index="04" title="Confirm on chain">
          <ConfirmOnChain
            deployment={deployment}
            listingId={listing.listing_id}
            deliveredRoot={listing.delivered_hash}
            onConfirmed={onRefresh}
          />
        </Section>
      ) : null}
    </div>
  );
}
