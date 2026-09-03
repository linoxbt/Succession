/**
 * Screen 3 — transfer confirmation.
 *
 * The hash comparison is the product's credibility, so it is the screen, not
 * something behind a "Success!" banner. Committed and delivered sit side by
 * side in monospace, character for character, with an unambiguous verdict.
 *
 * The one animated moment on the whole site lives here: a brief pulse on the
 * match mark when verification completes. Nothing else moves.
 */
import type { Outcome } from "../api";
import { Certificate } from "./Certificate";
import {
  Button,
  Definition,
  EvidenceStrip,
  Notice,
  Section,
  StateBadge,
} from "./primitives";

export function Confirmation({
  outcome,
  onContinue,
}: {
  outcome: Outcome;
  onContinue: () => void;
}) {
  const verified = outcome.outcome === "verified";

  return (
    <div className="space-y-10">
      <header className="space-y-4">
        <p className="font-sans text-xs uppercase tracking-[0.16em] text-ink/50">
          {verified ? "Transfer confirmed" : "Transfer failed"}
        </p>
        <h1 className="font-serif text-4xl leading-tight">
          {verified ? "Hash verified." : "Hash mismatch."}
        </h1>
        <p className="max-w-2xl font-sans text-[0.9375rem] leading-relaxed text-ink/70">
          {verified ? (
            <>
              Delivered memory matches the committed hash. Funds released to
              seller; ERC-8004 identity transferred to buyer; the seller&rsquo;s
              tenant is sealed.
            </>
          ) : (
            <>
              Delivered memory does not match the committed hash. Escrow
              automatically refunded to buyer. The seller&rsquo;s tenant was not
              sealed and the identity did not move.
            </>
          )}
        </p>
      </header>

      <Section title="Hash comparison">
        <div className="grid gap-px border border-rule bg-rule sm:grid-cols-2">
          <HashPanel label="Committed at listing" value={outcome.committed_root} />
          <HashPanel
            label="Delivered and re-hashed on the buyer's store"
            value={outcome.delivered_root}
            tone={verified ? "closed" : "void"}
          />
        </div>

        <div className="mt-6 flex items-center gap-3">
          <span
            aria-hidden
            className={`inline-flex h-7 w-7 animate-verify items-center justify-center border font-mono text-sm ${
              verified ? "border-closed text-closed" : "border-void text-void"
            }`}
          >
            {verified ? "✓" : "✕"}
          </span>
          <StateBadge tone={verified ? "closed" : "void"}>
            {verified ? "Match — escrow released" : "Mismatch — escrow refunded"}
          </StateBadge>
        </div>
      </Section>

      {outcome.receipt ? (
        <Section title="Settlement">
          <EvidenceStrip>
            <Definition label="Outcome">{outcome.receipt.outcome}</Definition>
            <Definition label="Paid to" mono>
              {outcome.receipt.paid_to}
            </Definition>
            {verified ? (
              <Definition label="Identity transferred to" mono>
                {outcome.receipt.identity_transferred_to}
              </Definition>
            ) : null}
            <Definition label="Reference" mono>
              {outcome.receipt.reference}
            </Definition>
            <Definition label="Settled at" mono>
              {outcome.receipt.settled_at}
            </Definition>
          </EvidenceStrip>
        </Section>
      ) : null}

      {!verified && outcome.failure_reason ? (
        <Notice tone="void">{outcome.failure_reason}</Notice>
      ) : null}

      {outcome.certificate ? (
        <Certificate
          certificate={outcome.certificate}
          text={outcome.certificate_text ?? ""}
        />
      ) : null}

      <div className="pt-2">
        <Button onClick={onContinue}>
          {verified ? "Open the successor agent" : "Return to listing"}
        </Button>
      </div>
    </div>
  );
}

function HashPanel({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "closed" | "void";
}) {
  const accent = {
    neutral: "text-ink",
    closed: "text-closed",
    void: "text-void",
  }[tone];
  return (
    <div className="bg-vellum p-5">
      <p className="mb-3 font-sans text-xs uppercase tracking-[0.1em] text-ink/50">
        {label}
      </p>
      {/* Broken into groups so a human can actually compare two of these. */}
      <p className={`break-all font-mono text-[0.8125rem] leading-relaxed ${accent}`}>
        {value.replace(/^0x/, "").match(/.{1,8}/g)?.join(" ") ?? value}
      </p>
    </div>
  );
}
