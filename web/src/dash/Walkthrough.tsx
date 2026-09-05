/**
 * The scripted sale, on a sample agent, behind a banner that never leaves.
 *
 * This is the one screen in the console that is not live data, and it says so
 * permanently rather than once. It exists because the claim the project makes,
 * that memory is the asset, and that a successor agent inherits working context
 * rather than a file, is only convincing when you watch a cold agent answer
 * from memory it did not have a minute ago.
 *
 * The memory is invented. The pipeline is not: export, hash, encrypt, import and
 * re-hash all run the same code a real sale runs, so the hash comparison below
 * is genuinely computed and the seal that rejects the seller's next write is the
 * real guard. Settlement is `LocalSettlement`, whose references are
 * `local:`-prefixed so they cannot be mistaken for a transaction.
 */
import { useCallback, useEffect, useState } from "react";

import { walkthrough, type Listing, type Outcome, type Preview, type Reply } from "../api";
import {
  Badge,
  Button,
  Evidence,
  Field,
  FieldList,
  FullHash,
  Note,
  PageHead,
  Section,
  VerifyMark,
} from "../ui";

export default function Walkthrough() {
  const [listing, setListing] = useState<Listing | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [sealed, setSealed] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const guard = useCallback(async (work: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    setListing(await walkthrough.listing().catch(() => null));
    setPreview(await walkthrough.preview().catch(() => null));
    setOutcome(await walkthrough.outcome().catch(() => null));
    setSealed(
      await walkthrough
        .seal("walkthrough-seller")
        .then((s) => s.sealed)
        .catch(() => null),
    );
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const start = () =>
    guard(async () => {
      await walkthrough.reset();
      setOutcome(null);
      await refresh();
    });

  const fund = () =>
    guard(async () => {
      await walkthrough.buy();
      await refresh();
    });

  const settle = () =>
    guard(async () => {
      setOutcome(await walkthrough.transfer());
      await refresh();
    });

  return (
    <div>
      <PageHead
        index="05 / Walkthrough"
        title="A scripted sale, on a sample agent."
        lede="The memory here is invented and nothing on this page touches a chain. It exists because the claim the product makes is only convincing when you watch a cold agent answer from memory it did not have a minute ago."
      />

      {/* Standing condition, not a dismissible alert. It stays for as long as
          the page does, because what it qualifies never stops being true. */}
      <div className="on-carbon -mx-6 mb-beat px-6 py-6 sm:-mx-10 sm:px-10 lg:-mx-16 lg:px-16 xl:-mx-24 xl:px-24">
        <p className="font-mono text-label uppercase text-chalkFaint">Not a live listing</p>
        <p className="mt-3 max-w-measure text-body text-chalkMuted">
          Settlement here is an in-process mirror of the contract's state machine.
          Real listings are on the Marketplace.
        </p>
      </div>

      <Section
        title="A scripted sale"
        action={
          <Button size="sm" variant="ghost" onClick={start} disabled={busy}>
            {listing ? "Restart" : "Start"}
          </Button>
        }
      >
        <p className="max-w-measure text-body text-muted">
          A freight agent with ninety-odd days of accumulated context: who its
          counterparties are, what it has quoted, what it has learned about how
          each one behaves, and one open commitment it has not yet closed.
        </p>
      </Section>

      {error ? <Note>{error}</Note> : null}

      {listing ? (
        <Section title="What a buyer sees before paying">
          <FieldList>
            <Field label="State">
              <Badge tone={listing.state === "open" ? "neutral" : "escrow"}>
                {listing.state === "open" ? "Open, no buyer" : "Escrow: funds held"}
              </Badge>
            </Field>
            <Field label="Committed hash">
              <FullHash value={listing.hash_commitment} />
            </Field>
            {preview ? (
              <>
                <Field label="Records">
                  {Object.values(preview.counts ?? {}).reduce((a, b) => a + b, 0)}
                </Field>
                <Field label="Memory size">{preview.memory_size_bytes} bytes</Field>
              </>
            ) : null}
          </FieldList>
          <Note>
            Counts, not contents. The data room is built from aggregates, so
            there is no record body in scope to leak by accident.
          </Note>
          {listing.state === "open" ? (
            <div className="mt-5">
              <Button onClick={fund} disabled={busy}>
                Fund escrow
              </Button>
            </div>
          ) : null}
          {listing.state === "escrowed" ? (
            <div className="mt-5">
              <Button onClick={settle} disabled={busy}>
                Deliver, import and settle
              </Button>
            </div>
          ) : null}
        </Section>
      ) : null}

      {outcome ? (
        <Section title="The comparison that matters">
          <Evidence>
            <div className="flex items-start gap-4">
              <VerifyMark matched={outcome.outcome === "verified"} pulse />
              <div className="min-w-0 flex-1">
                <p className="mb-3 text-body text-muted">
                  Committed before a buyer existed, then re-derived from the
                  buyer's own store after the import, not from the bytes sent.
                </p>
                <FieldList>
                  <Field label="Committed">
                    <FullHash value={outcome.committed_root} />
                  </Field>
                  <Field label="Re-derived">
                    <FullHash
                      value={outcome.delivered_root}
                      tone={outcome.outcome === "verified" ? "closed" : "void"}
                    />
                  </Field>
                </FieldList>
              </div>
            </div>
          </Evidence>
          {sealed ? (
            <Note>
              The seller's copy is sealed. Its next write is rejected, try it in
              the conversation below by asking the seller's agent anything.
            </Note>
          ) : null}
        </Section>
      ) : null}

      <Section title="The successor, booting cold">
        <p className="mb-4 max-w-measure text-body text-muted">
          A different tenant in a different file. Before the sale it knows
          nothing; after it, it answers from memory that was written into its own
          store by the import. Ask it about a counterparty, try{" "}
          <em>"Hi, Northwind Mills again, still good on that Duluth run?"</em>
        </p>
        <Conversation side="buyer" />
      </Section>
    </div>
  );
}

function Conversation({ side }: { side: "seller" | "buyer" }) {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState<Reply | null>(null);
  const [busy, setBusy] = useState(false);

  const send = async () => {
    if (!message.trim()) return;
    setBusy(true);
    try {
      setReply(await walkthrough.message(side, message));
    } catch {
      setReply(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void send()}
          placeholder="Message the agent as a returning customer"
          className="flex-1 border border-rule bg-paper px-3 py-2 text-body placeholder:text-faint"
        />
        <Button size="sm" variant="ghost" onClick={() => void send()} disabled={busy}>
          Send
        </Button>
      </div>
      {reply ? (
        <div className="border-l-2 border-rule pl-4">
          <p className="text-body text-ink">{reply.text}</p>
          {reply.citations?.length ? (
            <p className="mt-2 text-label text-faint">
              recalled from {reply.citations.map((c) => c.tier).join(", ")}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
