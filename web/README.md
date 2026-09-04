# Succession web

Two surfaces, one system.

```bash
npm install
npm run dev      # proxies /api to http://127.0.0.1:8000
```

**Landing** (`/`) — statements, not paragraphs. Every line is a claim the
product can be held to, and nothing explains itself twice. The scale does the
persuading.

**Console** (`/app`) — an internal operations surface for the team running
sales: left rail, dense tables, tabular numerals, one accent reserved for
transaction state. There is deliberately no `Card` component and no shadow
anywhere; depth is what a marketing page uses to make a list feel important.

Five views: Overview, Listing (the full list → escrow → settle workflow),
Transfers (the settlement ledger, refunds included), Agents (Virtuals ACP job
history), Memory (the cold-booted successor agent).

## Rules the surface keeps

- **Colour encodes transaction state and nothing else**, and never alone —
  every badge says what it means in words.
- **The hash comparison is the screen**, not a detail behind a success banner.
  Two monospace blocks in eight-character runs, so a person can actually read
  one against the other.
- **Self-reported and verifiable figures are labelled separately.** Record
  counts come from the seller's own memory; ACP job history resolves to on-chain
  job ids. A buyer's confidence in each should differ, so the UI does not blend
  them.
- **The Memory view is deliberately plain.** The surprise belongs to what the
  agent says. The citation line under each reply names the records behind every
  claim — that is what separates "the agent remembered" from "the agent said
  something plausible".

## Recorded mode

With no service reachable the build replays `public/recorded-run.json` — one
real end-to-end run. A banner names the mode and the recording date on every
screen. Regenerate it whenever the pipeline changes.
