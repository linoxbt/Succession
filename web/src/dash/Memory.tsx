/**
 * The successor agent, cold-booted.
 *
 * Deliberately the plainest screen here. The surprise belongs to what the agent
 * says, not to anything around it. The one addition is the citation line under
 * each reply, naming the records behind every claim — that line is what
 * separates "the agent remembered" from "the agent said something plausible".
 */
import { useState } from "react";
import type { Reply } from "../api";
import { Badge, Button, Section, Rule } from "../ui";

interface Backend {
  message(side: "seller" | "buyer", message: string): Promise<Reply>;
  writeAttempt(): Promise<{ accepted: boolean; reason: string }>;
}

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

export function Memory({
  backend,
  sealed,
}: {
  backend: Backend;
  sealed: { sealed: boolean; at: string } | null;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState<{ accepted: boolean; reason: string } | null>(null);

  async function send(message: string) {
    if (!message.trim() || busy) return;
    setBusy(true);
    setTurns((t) => [...t, { from: "customer", text: message }]);
    setDraft("");
    try {
      const reply = await backend.message("buyer", message);
      setTurns((t) => [...t, { from: "agent", text: reply.text, citations: reply.citations }]);
    } catch (error) {
      setTurns((t) => [...t, { from: "agent", text: `Unreachable: ${String(error)}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <Section
        title="Successor agent"
        action={<span className="text-xs text-faint">Cold session, new tenant</span>}
      >
        <div className="min-h-[15rem] space-y-5 px-5 py-5">
          {turns.length === 0 ? (
            <p className="text-[0.8125rem] text-faint">
              Message the agent as a returning customer.
            </p>
          ) : null}
          {turns.map((turn, i) => (
            <div key={i} className="space-y-1">
              <p className="text-[0.6875rem] uppercase tracking-[0.08em] text-faint">
                {turn.from === "customer" ? "Customer" : "Agent"}
              </p>
              <p className="text-[0.9375rem] leading-relaxed">{turn.text}</p>
              {turn.citations?.length ? (
                <p className="pt-1 font-mono text-[0.75rem] text-escrow/80">
                  recalled from {turn.citations.map((c) => `${c.tier}/${c.key}`).join(" · ")}
                </p>
              ) : null}
            </div>
          ))}
        </div>
        <Rule />
        <form
          className="flex flex-col gap-2 px-5 py-4 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            void send(draft);
          }}
        >
          <label className="sr-only" htmlFor="msg">
            Message the agent
          </label>
          <input
            id="msg"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Message the agent as a returning customer"
            className="flex-1 rounded-md border border-rule bg-vellum px-3 py-2 text-[0.8125rem] placeholder:text-faint"
          />
          <Button type="submit" disabled={busy}>
            {busy ? "…" : "Send"}
          </Button>
        </form>
        <div className="flex flex-wrap gap-2 border-t border-hairline px-5 py-3">
          {OPENERS.map((opener) => (
            <button
              key={opener}
              onClick={() => void send(opener)}
              disabled={busy}
              className="rounded-md border border-rule px-2.5 py-1 text-left text-xs text-muted hover:border-secondary hover:text-ink disabled:opacity-40"
            >
              {opener}
            </button>
          ))}
        </div>
      </Section>

      <Section title="Origin tenant">
        <div className="space-y-4 px-5 py-4">
          {sealed?.sealed ? (
            <span className="flex flex-wrap items-center gap-2">
              <Badge tone="closed">Sealed</Badge>
              <span className="text-[0.8125rem] text-muted">{sealed.at}</span>
            </span>
          ) : (
            <Badge>Live</Badge>
          )}
          <p className="max-w-[62ch] text-[0.8125rem] leading-relaxed text-muted">
            The seller's database file still exists on their machine. What it can
            no longer do is authenticate, sync, or be represented anywhere in this
            system as the live agent.
          </p>
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => setAttempt(await backend.writeAttempt())}
          >
            Attempt a write as the origin agent
          </Button>
          {attempt ? (
            <p
              className={`border-l-2 pl-3 text-[0.8125rem] ${
                attempt.accepted ? "border-bad text-bad" : "border-good text-muted"
              }`}
            >
              {attempt.accepted ? "Write accepted — " : "Write rejected. "}
              {attempt.reason}
            </p>
          ) : null}
        </div>
      </Section>
    </div>
  );
}
