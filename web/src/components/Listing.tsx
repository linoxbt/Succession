/**
 * Screen 1 — the data-room teaser.
 *
 * Agent identity, tenure, and aggregate stats as a short definition list, then
 * a clearly separated verified-on-chain strip. No cards, no ratings, no
 * product-grid anything.
 */
import { useState } from "react";
import type { Listing as ListingType, Preview } from "../api";
import { abbreviate, formatAmount } from "../api";
import {
  Button,
  Definition,
  DefinitionList,
  EvidenceStrip,
  Figure,
  Notice,
  Rule,
  Section,
} from "./primitives";

const CATEGORY_LABELS: Record<string, string> = {
  identity: "Identity",
  relationships: "Relationships",
  preferences: "Preferences",
  history: "History",
  commitments: "Commitments",
  "learned-behaviors": "Learned behaviors",
};

export function Listing({
  listing,
  preview,
  onRequestTransfer,
  busy,
}: {
  listing: ListingType;
  preview: Preview;
  onRequestTransfer: () => void;
  busy: boolean;
}) {
  const [showFactors, setShowFactors] = useState(false);
  const valuation = preview.valuation;

  return (
    <div className="space-y-10">
      <header className="space-y-2">
        <p className="font-sans text-xs uppercase tracking-[0.16em] text-ink/50">
          Memory asset for transfer
        </p>
        <h1 className="font-serif text-4xl leading-tight">
          Agent #{listing.agent_id.split(":").pop()}
        </h1>
        <p className="font-sans text-sm text-ink/60">
          Registered {preview.tenure_days} days · {listing.agent_id}
        </p>
      </header>

      <Section title="Aggregate position">
        <DefinitionList>
          <Definition label="Completed journal events">
            {preview.counts.journal_events?.toLocaleString()}
          </Definition>
          <Definition label="Counterparties">
            {preview.category_breakdown.relationship ?? 0}
          </Definition>
          <Definition label="Records in transfer">
            {preview.counts.total_records?.toLocaleString()}
          </Definition>
          <Definition label="Memory size">
            {(preview.memory_size_bytes / 1024).toFixed(1)} KB
          </Definition>
          <Definition
            label="Valuation (reference)"
            hint="Displayed beside the asking price. Not enforced by the contract."
          >
            <Figure>
              {valuation ? `$${valuation.amount}` : "—"}
            </Figure>
          </Definition>
          <Definition label="Asking price">
            <Figure>{formatAmount(listing.price, listing.currency)}</Figure>
          </Definition>
        </DefinitionList>
      </Section>

      {valuation ? (
        <Section>
          <button
            onClick={() => setShowFactors((v) => !v)}
            className="font-sans text-sm text-ink/60 underline decoration-rule underline-offset-4 hover:text-ink"
            aria-expanded={showFactors}
          >
            {showFactors ? "Hide" : "Show"} how this figure is derived
          </button>
          {showFactors ? (
            <div className="mt-5 space-y-5">
              <p className="font-mono text-xs text-ink/60">{valuation.formula}</p>
              <DefinitionList>
                {valuation.factors.map((factor) => (
                  <Definition key={factor.name} label={factor.name} hint={factor.explanation}>
                    <span className="font-mono">× {factor.value}</span>
                  </Definition>
                ))}
              </DefinitionList>
              <Notice>
                Not included: {Object.keys(valuation.excluded).join(", ")}. A single
                listing has no marketplace to compute them from, and a fabricated
                figure would be worse than none.
              </Notice>
            </div>
          ) : null}
        </Section>
      ) : null}

      <Section title="Disclosure">
        <DefinitionList>
          <Definition label="Categories in transfer">
            {listing.categories.map((c) => CATEGORY_LABELS[c] ?? c).join(", ")}
          </Definition>
          <Definition
            label="Named in preview"
            hint="Only counterparties the seller marked public."
          >
            {preview.public_counterparties.length
              ? preview.public_counterparties.join(", ")
              : "None"}
          </Definition>
          <Definition
            label="Withheld as non-transferable"
            hint="Excluded before hashing, so not present in the committed tree."
          >
            {preview.withheld_non_transferable} record
            {preview.withheld_non_transferable === 1 ? "" : "s"}
          </Definition>
        </DefinitionList>
        <Rule className="my-4" />
        <p className="font-sans text-sm text-ink/60">{preview.disclosure}</p>
      </Section>

      <Section title="Verified on-chain">
        <EvidenceStrip>
          <Definition label="Committed hash" mono>
            {listing.hash_commitment}
          </Definition>
          <Definition
            label="Seller signature"
            mono
            hint="EIP-191, over the provenance header."
          >
            {abbreviate(listing.seller_signature, 22, 12)}
          </Definition>
          <Definition label="Listing contract" mono>
            {listing.listing_id}
          </Definition>
        </EvidenceStrip>
      </Section>

      <div className="pt-2">
        <Button onClick={onRequestTransfer} disabled={busy}>
          {busy ? "Requesting…" : "Request transfer"}
        </Button>
      </div>
    </div>
  );
}
