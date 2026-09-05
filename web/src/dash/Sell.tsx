/**
 * Selling, which does not happen in this browser and cannot.
 *
 * Sibyl 0.8.0 is local-only: `MemoryClient.local(path)` is its only constructor
 * and the package makes no network calls beyond a tier check. A seller's memory
 * is a SQLite file on their own machine, so there is no Sibyl account for this
 * page to connect to and nothing for it to read.
 *
 * A form here would therefore be a lie with a submit button. What this page does
 * instead is hand over the exact command, which has the side benefit of being
 * the only arrangement where "plaintext never leaves the seller before escrow"
 * is a fact rather than a promise: the export, the encryption and the signature
 * all happen on their machine, and what reaches the network is a hash, a
 * signature, aggregate counts, and ciphertext.
 */
import { useState } from "react";

import type { ChainStatus } from "../api";
import { Copyable, Note, PageHead, Section } from "../ui";

/** The six directories that carry memory. The other three are generated. */
const CATEGORIES = [
  "identity",
  "relationships",
  "preferences",
  "history",
  "commitments",
  "learned-behaviors",
] as const;

export default function Sell({ chainStatus }: { chainStatus: ChainStatus | null }) {
  const [db, setDb] = useState("~/.sibyl-memory/memory.db");
  const [tenant, setTenant] = useState("");
  const [agent, setAgent] = useState("");
  const [price, setPrice] = useState("25");

  // Percentage per category. 100 means the whole directory; 0 leaves it out of
  // the sale entirely, which is why "not selling this" and "selling none of it"
  // are the same control rather than two.
  const [shares, setShares] = useState<Record<string, number>>(
    Object.fromEntries(CATEGORIES.map((c) => [c, 100])),
  );

  const share = (c: string) => shares[c] ?? 100;
  const scope = CATEGORIES.filter((c) => share(c) > 0)
    .map((c) => `${c}=${share(c)}`)
    .join(",");
  const partial = CATEGORIES.some((c) => share(c) !== 100);

  const minor = Math.round((Number(price) || 0) * 1_000_000);
  const command = [
    "SUCCESSION_SIGNING_KEY=0x… \\",
    "  succession list \\",
    `    --db ${db || "<your store>"} \\`,
    `    --tenant ${tenant || "<your tenant>"} \\`,
    `    --agent ${agent || "erc8004:84532:<your agent id>"} \\`,
    ...(partial ? [`    --scope ${scope || "<nothing selected>"} \\`] : []),
    `    --price ${minor}`,
  ].join("\n");

  return (
    <div>
      <PageHead
        index="03 / Sell"
        title="Listing runs on your machine."
        lede="Your Sibyl store is a local file and this page cannot read it, which is the same reason the memory never reaches anyone until escrow is funded. The command below exports it, commits the hash on Base, and keeps the key in a vault on your disk."
      />

      <Section title="Build the command">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Sibyl store" hint="the path sibyl status prints" value={db} onChange={setDb} />
          <Field label="Tenant" hint="which tenant holds the agent" value={tenant} onChange={setTenant} />
          <Field
            label="ERC-8004 identity"
            hint="the agent token you hold"
            value={agent}
            onChange={setAgent}
          />
          <Field label="Asking price (USDC)" hint="what a buyer pays" value={price} onChange={setPrice} />
        </div>

        <div className="mt-12">
          <p className="chapter-mark mb-6">How much of each to sell</p>
          <p className="mb-8 max-w-measure text-body text-muted">
            Run <code>succession inventory</code> first to see what this agent
            actually holds. A category it has never written to cannot be sold,
            and offering it anyway would list a directory that exports empty.
          </p>

          <div className="border-t border-hairline">
            {CATEGORIES.map((category) => (
              <div
                key={category}
                className="flex flex-wrap items-center gap-x-8 gap-y-3 border-b border-hairline py-5"
              >
                <span className="w-56 shrink-0 text-body text-ink">{category}</span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={share(category)}
                  onChange={(e) =>
                    setShares((s) => ({ ...s, [category]: Number(e.target.value) }))
                  }
                  className="h-px flex-1 min-w-[8rem] cursor-pointer appearance-none bg-rule accent-ink"
                  aria-label={`Percentage of ${category} to sell`}
                />
                <span className="w-20 shrink-0 text-right tnum text-body text-ink">
                  {share(category)}%
                </span>
              </div>
            ))}
          </div>

          <Note>
            Records are ordered newest first and a percentage takes that many
            from the front, so a successor inherits recent context rather than
            the oldest half. Relationship edges follow their endpoints rather
            than counting toward the percentage, because half an edge is not a
            thing. The rule is written into the package, so a buyer can
            reproduce your selection exactly.
          </Note>
        </div>

        <div className="mt-12">
          <Copyable text={command} />
          <Note>
            The key is read from the environment, never from an argument, a
            private key on a command line lands in shell history and in the
            process table.
          </Note>
        </div>
      </Section>

      <Section title="Then stay reachable until it sells">
        <p className="max-w-measure text-body text-muted">
          The content key is yours and is released only when you have seen escrow
          funded on chain yourself. This watcher checks for that and hands the key
          over when it lands:
        </p>
        <div className="mt-4">
          <Copyable text="succession fulfil" />
        </div>
        <Note>
          If you are offline when a buyer funds escrow, they wait. That is a real
          cost and it is bounded: after the confirmation window anyone can call{" "}
          <code>reclaimExpired</code> and the buyer gets their money back without
          needing you at all.
        </Note>
      </Section>

      {chainStatus?.mode !== "chain" ? (
        <Note>
          No contract is deployed yet, so <code>succession list</code> will stop
          rather than pretend. Listing settles on chain and has no offline mode.
        </Note>
      ) : null}
    </div>
  );
}

function Field({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-micro text-ink">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="border border-rule bg-paper px-3 py-2 text-body placeholder:text-faint"
      />
      <span className="text-label text-faint">{hint}</span>
    </label>
  );
}
