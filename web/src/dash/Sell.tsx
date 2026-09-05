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
import { Copyable, Note, Section } from "../ui";

export default function Sell({ chainStatus }: { chainStatus: ChainStatus | null }) {
  const [db, setDb] = useState("~/.sibyl-memory/memory.db");
  const [tenant, setTenant] = useState("");
  const [agent, setAgent] = useState("");
  const [price, setPrice] = useState("25");

  const minor = Math.round((Number(price) || 0) * 1_000_000);
  const command = [
    "SUCCESSION_SIGNING_KEY=0x… \\",
    "  succession list \\",
    `    --db ${db || "<your store>"} \\`,
    `    --tenant ${tenant || "<your tenant>"} \\`,
    `    --agent ${agent || "erc8004:84532:<your agent id>"} \\`,
    `    --price ${minor}`,
  ].join("\n");

  return (
    <div className="flex flex-col gap-10">
      <Section title="List your agent's memory">
        <p className="max-w-column text-[0.9375rem] leading-relaxed text-muted">
          Listing runs on your own machine. Your Sibyl store is a local file and
          this page cannot read it — which is the same reason the memory itself
          never reaches anyone until escrow is funded. The command below exports
          your store, commits its hash on Base, encrypts the package, and keeps
          the key in a vault on your disk.
        </p>
      </Section>

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

        <div className="mt-6">
          <Copyable text={command} />
          <Note>
            The key is read from the environment, never from an argument — a
            private key on a command line lands in shell history and in the
            process table.
          </Note>
        </div>
      </Section>

      <Section title="Then stay reachable until it sells">
        <p className="max-w-column text-[0.9375rem] leading-relaxed text-muted">
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
      <span className="text-[0.8125rem] text-ink">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="border border-rule bg-vellum px-3 py-2 text-[0.875rem] placeholder:text-faint"
      />
      <span className="text-[0.75rem] text-faint">{hint}</span>
    </label>
  );
}
