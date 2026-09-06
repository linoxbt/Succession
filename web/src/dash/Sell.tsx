/**
 * Selling, which does not happen in this browser and cannot.
 *
 * Sibyl 0.8.0 is local-only: `MemoryClient.local(path)` is its only constructor
 * and the package makes no network calls beyond a tier check. A seller's memory
 * is a SQLite file on their own machine, so there is no Sibyl account for this
 * page to connect to and nothing for it to read.
 *
 * A form here would therefore be a lie with a submit button. What this page does
 * instead is prepare the command, which has the side benefit of being the only
 * arrangement where "plaintext never leaves the seller before escrow" is a fact
 * rather than a promise: the export, the encryption and the signature all happen
 * on their machine, and what reaches the network is a hash, a signature,
 * aggregate counts, and ciphertext.
 *
 * The command is withheld until the seller acknowledges the seal. Settlement
 * revokes their tenant's credentials and there is deliberately no unseal, so
 * that is not a detail to discover afterwards in a receipt.
 */
import { useState } from "react";

import type { ChainStatus } from "../api";
import { Copyable, Note, PageHead, Section } from "../ui";
import { Block, Panel, Slider, Steps, TextInput } from "../app/ui";
import { SELLABLE_DIRECTORIES, DIRECTORY_NOTE } from "../app/domain";

/**
 * The three generated directories. They ship with every package and describe
 * it, rather than carrying memory of their own, so they are shown here as
 * present-but-not-priced instead of being silently absent from the list.
 */
const GENERATED: readonly (readonly [string, string])[] = [
  ["provenance", "origin, prior owners, signature"],
  ["permissions", "redaction flags and consent basis"],
  ["integrity-proof", "the Merkle root and its subroots"],
] as const;

const PREPARATION = [
  ["1", "Select the agent", "Which ERC-8004 identity is being sold."],
  ["2", "Inspect the memory", "succession inventory reports what it actually holds."],
  ["3", "Choose the scope", "Whole directories, or a percentage of each."],
  ["4", "Apply privacy", "Consent and transferability are read per record."],
  ["5", "Generate the package", "Filtered, serialised, hashed, encrypted."],
  ["6", "Calculate the valuation", "Five factors, each one re-derivable."],
  ["7", "Review integrity", "One subroot per directory, one root over all."],
  ["8", "Acknowledge the seal", "Settlement is irreversible for the seller."],
  ["9", "Commit the root", "The hash goes on chain before a buyer exists."],
  ["10", "Publish", "Counts, valuation and proofs reach the marketplace."],
] as const;

export default function Sell({ chainStatus }: { chainStatus: ChainStatus | null }) {
  const [db, setDb] = useState("~/.sibyl-memory/memory.db");
  const [tenant, setTenant] = useState("");
  const [agent, setAgent] = useState("");
  const [price, setPrice] = useState("25");
  const [sealAcknowledged, setSealAcknowledged] = useState(false);

  // Percentage per category. 100 means the whole directory; 0 leaves it out of
  // the sale entirely, which is why "not selling this" and "selling none of it"
  // are the same control rather than two.
  const [shares, setShares] = useState<Record<string, number>>(
    Object.fromEntries(SELLABLE_DIRECTORIES.map((c) => [c, 100])),
  );

  const share = (c: string) => shares[c] ?? 100;
  const included = SELLABLE_DIRECTORIES.filter((c) => share(c) > 0);
  const scope = included.map((c) => `${c}=${share(c)}`).join(",");
  const partial = SELLABLE_DIRECTORIES.some((c) => share(c) !== 100);

  const minor = Math.round((Number(price) || 0) * 1_000_000);
  const command = [
    "SUCCESSION_SIGNING_KEY=0x… \\",
    "  succession list \\",
    `    --db ${db || "<your store>"} \\`,
    `    --tenant ${tenant || "<your tenant>"} \\`,
    `    --agent ${agent || "erc8004:84532:<your agent id>"} \\`,
    `    --marketplace ${typeof window === "undefined" ? "" : window.location.origin} \\`,
    ...(partial ? [`    --scope ${scope || "<nothing selected>"} \\`] : []),
    `    --price ${minor}`,
  ].join("\n");

  const ready = Boolean(tenant && agent && included.length && minor > 0);

  return (
    <div>
      <PageHead
        index="03 / Sell"
        title="Turn accumulated memory into transferable property."
        lede="Your Sibyl store is a local file and this page cannot read it, which is the same reason the memory never reaches anyone until escrow is funded. What this page does is prepare the command that exports it, commits the hash on Base, and keeps the key in a vault on your disk."
      />

      <Section index="01" title="What listing involves">
        <div className="grid gap-12 lg:grid-cols-2">
          <Steps
            steps={PREPARATION.slice(0, 5).map(([index, title, detail]) => ({
              index,
              title,
              detail,
              state: "waiting" as const,
            }))}
          />
          <Steps
            steps={PREPARATION.slice(5).map(([index, title, detail]) => ({
              index,
              title,
              detail,
              state: "waiting" as const,
            }))}
          />
        </div>
      </Section>

      <Section index="02" title="The agent" className="mt-chapter">
        <div className="grid gap-6 sm:grid-cols-2">
          <TextInput
            label="Sibyl store"
            hint="the path sibyl status prints"
            value={db}
            onChange={setDb}
          />
          <TextInput
            label="Tenant"
            hint="which tenant holds the agent"
            value={tenant}
            onChange={setTenant}
          />
          <TextInput
            label="ERC-8004 identity"
            hint="the agent token you hold"
            value={agent}
            onChange={setAgent}
          />
          <TextInput
            label="Asking price, USDC"
            hint="what a buyer pays into escrow"
            value={price}
            onChange={setPrice}
          />
        </div>
        <Note>
          Run <code>succession inventory</code> before deciding anything here. It
          reports what this agent actually holds, per directory, split by what is
          sellable and what consent withholds. A directory it has never written
          to cannot be sold, and offering it anyway lists something that exports
          empty.
        </Note>
      </Section>

      <Section index="03" title="Transfer scope" className="mt-chapter">
        <p className="mb-10 max-w-measure text-body text-muted">
          Each directory is a unit of selection and receives its own Merkle
          subroot, which is what makes a partial succession verifiable on its own
          terms rather than as a claim about a whole that was never delivered.
        </p>

        <div className="grid gap-x-12 gap-y-8 sm:grid-cols-2">
          {SELLABLE_DIRECTORIES.map((category) => (
            <div key={category}>
              <Slider
                label={category}
                value={share(category)}
                onChange={(value) =>
                  setShares((s) => ({ ...s, [category]: value }))
                }
              />
              <p className="mt-2 text-micro text-faint">
                {share(category) === 0
                  ? "Excluded from the sale entirely."
                  : DIRECTORY_NOTE[category]}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-12">
          <Panel className="p-7">
            <Block label="Resulting scope">
              <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
                <span className="text-body text-ink">
                  {partial ? "Partial succession" : "Full succession"}
                </span>
                <span className="tnum text-micro text-muted">
                  {included.length} of {SELLABLE_DIRECTORIES.length} directories
                </span>
              </div>
              {included.length === 0 ? (
                <p className="mt-3 text-micro text-void">
                  Nothing is selected, so there is nothing to sell.
                </p>
              ) : null}
            </Block>
          </Panel>
        </div>

        <div className="mt-12 border-t border-hairline pt-8">
          <p className="chapter-mark mb-5">Not yet sellable</p>
          <div className="flex flex-col gap-3">
            {GENERATED.map(([name, why]) => (
              <div key={name} className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
                <span className="w-56 shrink-0 text-body text-faint">{name}</span>
                <span className="font-mono text-label uppercase tracking-[0.14em] text-faint">
                  Coming soon
                </span>
                <span className="text-micro text-faint">{why}</span>
              </div>
            ))}
          </div>
          <Note>
            These three describe the package rather than carry memory. They are
            generated at export time and travel with every sale already, so there
            is nothing to price separately yet. Selling them on their own is a
            later question, not a missing feature.
          </Note>
        </div>

        <Note>
          Records are ordered newest first and a percentage takes that many from
          the front, so a successor inherits recent context rather than the
          oldest half. Relationship edges follow their endpoints rather than
          counting toward the percentage, because half an edge is not a thing.
          The rule is written into the package, so a buyer can reproduce your
          selection exactly.
        </Note>
      </Section>

      {/* --- the gate ----------------------------------------------------- */}
      <Section index="04" title="Sealing is permanent" className="mt-chapter">
        <div className="border-l-2 border-void pl-8">
          <p className="max-w-reading text-body text-ink">
            When a succession settles, the agent you sold is sealed. The
            contract sets a sealed flag against its identity, this tenant's
            credentials are revoked, and every write path rejects afterwards:
            the adapter, the underlying client, and anything holding a reference
            to either.
          </p>
          <p className="mt-5 max-w-reading text-body text-muted">
            There is deliberately no unseal. It is not gated behind an
            administrator or a delay, it does not exist. A buyer paying for
            continuity is paying for the seller to no longer have it, and an
            operation that could undo that would make the thing being sold
            unsellable.
          </p>
        </div>

        <label className="mt-10 flex max-w-reading cursor-pointer items-start gap-4">
          <input
            type="checkbox"
            checked={sealAcknowledged}
            onChange={(e) => setSealAcknowledged(e.target.checked)}
            className="mt-1 h-4 w-4 shrink-0 accent-signal"
          />
          <span className="text-body text-ink">
            I understand that a completed succession permanently seals this
            agent, and that there is no unseal.
          </span>
        </label>
      </Section>

      {/* --- the command, once the gate is passed ------------------------- */}
      <Section index="05" title="Commit the root" className="mt-chapter">
        {!sealAcknowledged ? (
          <Note>
            The listing command appears once the seal is acknowledged above. This
            is not a formality: it is the one step of a sale the seller cannot
            take back.
          </Note>
        ) : !ready ? (
          <Note>
            Fill in the tenant, the identity and a price, and keep at least one
            directory in scope. The command is withheld while it would be
            incomplete rather than shown with placeholders that fail on paste.
          </Note>
        ) : (
          <>
            <Copyable text={command} />
            <Note>
              The key is read from the environment, never from an argument. A
              private key on a command line lands in shell history and in the
              process table.
            </Note>
          </>
        )}
      </Section>

      <Section index="06" title="Then stay reachable until it sells" className="mt-chapter">
        <p className="max-w-measure text-body text-muted">
          The content key is yours and is released only when you have seen escrow
          funded on chain yourself. This watcher checks for that and hands the key
          over when it lands:
        </p>
        <div className="mt-6">
          <Copyable text={`succession fulfil --marketplace ${window.location.origin}`} />
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
