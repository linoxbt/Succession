/**
 * Collecting memory you have paid for.
 *
 * The purchase splits across two places for the same reason selling does: the
 * escrow is an on-chain action your wallet can take from this page, but the
 * import writes into *your* Sibyl store, which is a file on your machine. So
 * funding happens here and claiming happens in your terminal.
 *
 * The step that matters is the re-hash. Checking the bytes you received only
 * proves the courier was honest; re-exporting your own store after the import
 * proves the importer wrote what it received and the engine coerced nothing on
 * the way in. `succession claim` does that and refuses to tell you to confirm
 * if the roots disagree.
 */
import { Copyable, Note, PageHead, Section } from "../ui";

export default function Claim({ listingId }: { listingId: string }) {
  const id = listingId || "<listing id>";
  return (
    <div>
      <PageHead
        index="04 — Claim"
        title="Collect what you paid for."
        lede="Once escrow is funded and the seller has released the key, this collects the encrypted package, imports it into your own store, and re-derives the hash from what actually landed there."
      />

      <Section title="1 — Install">
        <Copyable text={'pip install "succession[chain]"'} />
        <Note>
          You need a Sibyl store to import into. If you do not have one:{" "}
          <code>pip install 'sibyl-memory-cli[mcp]'</code> then{" "}
          <code>sibyl init</code>.
        </Note>
      </Section>

      <Section title="2 — Claim, import and verify">
        <Copyable
          text={`succession claim \\
    --listing ${id} \\
    --db ~/.sibyl-memory/memory.db \\
    --tenant my-successor-agent`}
        />
        <p className="mt-4 max-w-measure text-body text-muted">
          It prints the root the seller committed before you existed as a buyer,
          and the root re-derived from your own store after the import. They
          match or the purchase is not what was advertised.
        </p>
      </Section>

      <Section title="3 — Confirm on chain">
        <p className="max-w-measure text-body text-muted">
          Only if it printed <strong>VERIFIED</strong>. One transaction releases
          payment to the seller, transfers the ERC-8004 identity to you, and
          seals the seller's copy — all three, or none of them.
        </p>
        <Note>
          If the roots disagree, do not confirm. Submitting the mismatched root
          refunds you and abandons the sale, which is the correct outcome for a
          bad delivery. Doing nothing at all also works: after the confirmation
          window your escrow is reclaimable by anyone, and it can only ever go
          back to you.
        </Note>
      </Section>

      <Section title="If the key is not there yet">
        <p className="max-w-measure text-body text-muted">
          The seller releases it only after seeing your escrow on chain
          themselves — nobody else holds it, including this marketplace. If they
          are offline you wait, and your money is never stuck: the confirmation
          window ends and you can take it back.
        </p>
      </Section>
    </div>
  );
}
