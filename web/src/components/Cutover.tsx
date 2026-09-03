/**
 * Screen 4 — the buyer's agent, cold-booted.
 *
 * Kept visually unremarkable on purpose. The surprise lives in what the agent
 * says, not in the interface around it, so this is a plain chat column with no
 * decoration the other screens do not already have.
 *
 * The one addition is the citation line under each reply. It is not ornament:
 * it names the record behind every claim, which is what separates "the agent
 * remembered" from "the agent said something plausible".
 */
import { useState } from "react";
import type { Reply } from "../api";
import { Button, Notice, Rule, Section, StateBadge } from "./primitives";

interface Turn {
  from: "customer" | "agent";
  text: string;
  citations?: { tier: string; key: string }[];
}

const OPENERS = [
  "Hi, Northwind Mills again — are we still good on that Duluth run?",
  "Selkirk Timber here, about the standing rate.",
  "This is Acme Widgets, we've never worked together before.",
];

interface Backend {
  message(side: "seller" | "buyer", message: string): Promise<Reply>;
  writeAttempt(): Promise<{ accepted: boolean; reason: string }>;
}

export function Cutover({
  sealed,
  backend,
}: {
  sealed: { sealed: boolean; at: string } | null;
  backend: Backend;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState(OPENERS[0]!);
  const [busy, setBusy] = useState(false);
  const [writeAttempt, setWriteAttempt] = useState<{ accepted: boolean; reason: string } | null>(
    null,
  );

  async function send(message: string) {
    if (!message.trim() || busy) return;
    setBusy(true);
    setTurns((t) => [...t, { from: "customer", text: message }]);
    setDraft("");
    try {
      const reply: Reply = await backend.message("buyer", message);
      setTurns((t) => [
        ...t,
        { from: "agent", text: reply.text, citations: reply.citations },
      ]);
    } catch (error) {
      setTurns((t) => [
        ...t,
        { from: "agent", text: `Could not reach the agent: ${String(error)}` },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <p className="font-sans text-xs uppercase tracking-[0.16em] text-ink/50">
          Successor agent · cold session
        </p>
        <h1 className="font-serif text-4xl leading-tight">Agent #1183</h1>
        <p className="max-w-2xl font-sans text-[0.9375rem] leading-relaxed text-ink/70">
          New infrastructure, a tenant that was empty until the transfer
          completed, and no prior contact with any of these counterparties.
        </p>
      </header>

      <Section title="Conversation">
        <div className="border border-rule">
          <div className="min-h-[16rem] space-y-6 p-6">
            {turns.length === 0 ? (
              <p className="font-sans text-sm text-ink/45">
                No messages yet. Send one as a returning customer.
              </p>
            ) : null}
            {turns.map((turn, i) => (
              <div key={i} className="space-y-1.5">
                <p className="font-sans text-xs uppercase tracking-[0.1em] text-ink/45">
                  {turn.from === "customer" ? "Customer" : "Agent #1183"}
                </p>
                <p className="font-sans text-[0.9375rem] leading-relaxed">{turn.text}</p>
                {turn.citations?.length ? (
                  <p className="pt-1 font-mono text-xs text-ink/50">
                    recalled from{" "}
                    {turn.citations.map((c) => `${c.tier}/${c.key}`).join(" · ")}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
          <Rule />
          <form
            className="flex flex-col gap-3 p-4 sm:flex-row"
            onSubmit={(e) => {
              e.preventDefault();
              void send(draft);
            }}
          >
            <label className="sr-only" htmlFor="message">
              Message to the agent
            </label>
            <input
              id="message"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Message the agent as a returning customer"
              className="flex-1 border border-rule bg-vellum px-3 py-2 font-sans text-sm placeholder:text-ink/35"
            />
            <Button type="submit" disabled={busy}>
              {busy ? "…" : "Send"}
            </Button>
          </form>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {OPENERS.map((opener) => (
            <button
              key={opener}
              onClick={() => void send(opener)}
              disabled={busy}
              className="border border-rule px-3 py-1.5 text-left font-sans text-xs text-ink/70 hover:border-ink hover:text-ink disabled:opacity-40"
            >
              {opener}
            </button>
          ))}
        </div>
      </Section>

      <Section title="The origin agent">
        <div className="space-y-4">
          {sealed?.sealed ? (
            <StateBadge tone="closed">Origin tenant sealed {sealed.at}</StateBadge>
          ) : (
            <StateBadge tone="neutral">Origin tenant not sealed</StateBadge>
          )}
          <p className="max-w-2xl font-sans text-sm leading-relaxed text-ink/70">
            The seller&rsquo;s database file still exists on their machine — nothing
            here reaches onto it. What it can no longer do is authenticate,
            sync, or be represented anywhere in this system as the live agent.
          </p>
          <Button
            tone="quiet"
            onClick={async () => setWriteAttempt(await backend.writeAttempt())}
          >
            Attempt a write as the origin agent
          </Button>
          {writeAttempt ? (
            <Notice tone={writeAttempt.accepted ? "void" : "closed"}>
              {writeAttempt.accepted ? "Write accepted — " : "Write rejected. "}
              {writeAttempt.reason}
            </Notice>
          ) : null}
        </div>
      </Section>
    </div>
  );
}
