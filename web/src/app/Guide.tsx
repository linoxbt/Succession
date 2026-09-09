/**
 * The practical half of the documentation: how to actually use this.
 *
 * The conceptual sections in `Docs.tsx` explain what Succession is and why the
 * integrity scheme is shaped the way it is. They contained, between them, zero
 * commands. Someone who had read all eight still did not know how to install
 * the tool or sell anything.
 *
 * Every command below comes from `reference.ts`, which is generated from the
 * argparse parsers that actually run. Nothing here is retyped, so a renamed
 * flag cannot leave a stale example behind.
 */
import type { ReactNode } from "react";

import { Badge, Copyable, Table, Td } from "../ui";
import { Panel } from "./ui";
import { REFERENCE, type Command } from "./reference";

const MARKET = "https://successmarket.netlify.app";

function P({ children }: { children: ReactNode }) {
  return <p className="mt-4 max-w-[70ch] text-body text-ink">{children}</p>;
}

function Code({ children }: { children: ReactNode }) {
  return (
    <code className="rounded bg-shade px-1.5 py-0.5 text-micro text-ink">
      {children}
    </code>
  );
}

function H({ children }: { children: ReactNode }) {
  return (
    <h3 className="mt-10 text-heading font-bold text-ink first:mt-0">{children}</h3>
  );
}

/** A numbered step with the command that performs it. */
function Step({
  n,
  title,
  children,
  command,
}: {
  n: number;
  title: string;
  children?: ReactNode;
  command?: string;
}) {
  return (
    <div className="mt-8 flex gap-5">
      <span
        aria-hidden
        className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-signal/10 text-micro font-bold text-signal"
      >
        {n}
      </span>
      <div className="min-w-0 flex-1">
        <h4 className="text-body font-semibold text-ink">{title}</h4>
        {children ? (
          <div className="mt-1 max-w-[70ch] text-micro text-muted">{children}</div>
        ) : null}
        {command ? (
          <div className="mt-3">
            <Copyable text={command} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function flagsOf(command: Command) {
  return command.flags.filter((f) => !f.positional);
}

/** One command, its purpose, and every flag it accepts. */
function CommandEntry({ command }: { command: Command }) {
  const flags = flagsOf(command);
  const positional = command.flags.filter((f) => f.positional);

  return (
    <Panel className="mt-6 p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <code className="evidence-type text-body font-semibold text-ink">
          succession {command.name}
          {positional.map((p) => ` <${p.names[0]}>`).join("")}
        </code>
        {flags.some((f) => f.required) ? (
          <Badge>has required flags</Badge>
        ) : null}
      </div>
      <p className="mt-2 max-w-[70ch] text-micro text-muted">{command.help}</p>

      {flags.length ? (
        <div className="mt-5">
          <Table head={["Flag", "Required", "What it does"]}>
            {flags.map((flag) => (
              <tr key={flag.names.join(",")} className="border-b border-hairline">
                <Td>
                  <code className="evidence-type text-micro text-ink">
                    {flag.names.join(", ")}
                  </code>
                  {flag.choices.length ? (
                    <span className="mt-1 block text-micro text-faint">
                      one of {flag.choices.join(", ")}
                    </span>
                  ) : null}
                </Td>
                <Td>
                  {flag.required ? (
                    <Badge tone="escrow">required</Badge>
                  ) : (
                    <span className="text-micro text-faint">optional</span>
                  )}
                </Td>
                <Td>
                  <span className="text-micro text-muted">
                    {flag.help || "No description."}
                  </span>
                </Td>
              </tr>
            ))}
          </Table>
        </div>
      ) : (
        <p className="mt-4 text-micro text-faint">Takes no flags.</p>
      )}
    </Panel>
  );
}

const BY_NAME = new Map(REFERENCE.succession.map((c) => [c.name, c]));

// --- the sections --------------------------------------------------------

export const INSTALL = (
  <>
    <P>
      One package, two extras. The command is <Code>succession</Code>; the
      distribution is <Code>succession-cli</Code>, because the name{" "}
      <Code>succession</Code> has belonged to an unrelated library on PyPI since
      2016.
    </P>
    <div className="mt-5">
      <Copyable text={'pipx install "succession-cli[chain,mcp]"'} />
    </div>
    <P>
      <Code>chain</Code> pulls web3, which every command that touches Base needs:{" "}
      <Code>list</Code>, <Code>publish</Code>, <Code>fulfil</Code>,{" "}
      <Code>claim</Code>, <Code>buy</Code> and <Code>evaluate</Code>. Drop{" "}
      <Code>mcp</Code> if you do not want the agent-facing server. The contract
      ABI and the deployment record ship inside the wheel, so an installed CLI
      reaches the chain with no checkout.
    </P>

    <H>Check what it is connected to</H>
    <P>
      Four systems connect in different ways and conflating them is easy, so
      this reports all of them rather than leaving you to infer connectivity
      from a failure three commands later.
    </P>
    <div className="mt-5">
      <Copyable text="succession status" />
    </div>
    <P>
      Memory is a local SQLite file that Succession shares with the Sibyl CLI.
      The memory SDK has no sync endpoint in either direction, which is what
      makes "plaintext never leaves the seller before escrow" a fact rather than
      a promise. If <Code>sibyl init</Code> has written credentials, Succession
      reads them, so a paid tier stays paid; without them the SDK enforces a
      strict 5 MB cap.
    </P>

    <H>Prove it works before trusting it</H>
    <div className="mt-5">
      <Copyable text={`succession audit --check-chain --marketplace ${MARKET}`} />
    </div>
    <P>
      Seven checks against a memory it builds itself: that all six directories
      survive a sale with identical Merkle subroots, that a non-transferable
      record leaves no trace in the tree, that the preview carries no record
      bodies, that every valuation factor recomputes from its published inputs,
      that a percentage sale takes the newest records, that a sealed tenant
      rejects every write, and that every published root equals its on-chain
      commitment. It exits non-zero if any fails, and a check that could not run
      reports as skipped rather than passed.
    </P>
  </>
);

export const SELLING = (
  <>
    <P>
      Selling runs on your machine and cannot run anywhere else. A Sibyl store is
      a file on your disk, so no web page can read it, and that constraint is
      also the only arrangement in which the memory genuinely never reaches
      anyone before escrow is funded.
    </P>

    <Step
      n={1}
      title="See what is actually sellable"
      command="succession inventory --db ~/.sibyl-memory/memory.db --tenant my-agent"
    >
      Per directory, split three ways: what transfers, what you withheld, and
      what a counterparty never consented to move. The last of those cannot be
      sold at any price.
    </Step>

    <Step
      n={2}
      title="Prove a sale would carry it all"
      command={
        "SUCCESSION_SIGNING_KEY=0x… succession prove \\\n" +
        "  --db ~/.sibyl-memory/memory.db \\\n" +
        "  --tenant my-agent \\\n" +
        "  --agent erc8004:84532:0417"
      }
    >
      Exports, imports into a throwaway store, re-exports, and compares Merkle
      subroots. Touches no chain and spends nothing. Add{" "}
      <Code>--scope relationships=60,history=100</Code> to prove a partial sale.
    </Step>

    <Step
      n={3}
      title="Price it"
      command="succession value --db ~/.sibyl-memory/memory.db --tenant my-agent"
    >
      Five factors, each showing the input it read, the multiplier it produced
      and the rule it applied, so a buyer can recompute the figure by hand.
    </Step>

    <Step
      n={4}
      title="Commit the root and publish"
      command={
        "export SUCCESSION_SIGNING_KEY=0x…\n" +
        `export SUCCESSION_MARKETPLACE=${MARKET}\n\n` +
        "succession list \\\n" +
        "  --db ~/.sibyl-memory/memory.db \\\n" +
        "  --tenant my-agent \\\n" +
        "  --agent erc8004:84532:0417 \\\n" +
        "  --price 25000000"
      }
    >
      Price is in the payment token's minor units, so 25000000 is 25 USDC. This
      exports, hashes, encrypts, commits the root on Base and publishes the data
      room and the ciphertext. The commitment is the irreversible half: if the
      marketplace was unreachable, use <Code>succession publish</Code> rather
      than listing again, which the contract would refuse.
    </Step>

    <Step
      n={5}
      title="Stay reachable until it sells"
      command={`succession fulfil --marketplace ${MARKET}`}
    >
      Polls the chain and releases the content key once it sees your escrow
      funded, and not before. If you are offline when a buyer pays, they wait,
      and after the confirmation window anyone can reclaim the escrow for them
      without needing you.
    </Step>

    <Panel className="mt-10 border-void/30 p-6">
      <h4 className="text-body font-semibold text-ink">
        Settlement seals the agent, permanently
      </h4>
      <p className="mt-2 max-w-[70ch] text-micro text-muted">
        When a succession completes the contract sets a sealed flag against the
        identity, the tenant's credentials are revoked, and every write path
        rejects afterwards. There is deliberately no unseal. A buyer paying for
        continuity is paying for you to no longer have it, and an operation that
        could undo that would make the thing being sold unsellable.
      </p>
    </Panel>
  </>
);

export const BUYING = (
  <>
    <P>
      You can do all of this from the terminal. Funding escrow is the first
      irreversible step from your side, and the two commands that send
      transactions describe what they will do and stop unless given{" "}
      <Code>--yes</Code>.
    </P>

    <Step n={1} title="Find something" command={`succession market --marketplace ${MARKET}`}>
      Add <Code>--state open</Code> for what can still be bought, or{" "}
      <Code>--json</Code> to pipe it somewhere.
    </Step>

    <Step
      n={2}
      title="Read the data room before paying"
      command={`succession show --listing listing-672 --marketplace ${MARKET}`}
    >
      What transfers per directory, the valuation with its factors, and whether
      the published Merkle root matches the commitment on chain. Counts and
      aggregates only: record bodies are released after purchase and hash
      verification, never before.
    </Step>

    <Step
      n={3}
      title="Fund escrow"
      command={"export SUCCESSION_BUYER_KEY=0x…\n\nsuccession buy --listing listing-672 --yes"}
    >
      Two transactions, an ERC-20 approval and then buy(). The money is held by
      the contract, not paid: it reaches the seller only when a matching hash is
      confirmed, and returns to you otherwise.
    </Step>

    <Step
      n={4}
      title="Independent evaluation"
      command={
        "succession evaluate \\\n" +
        "  --listing listing-672 \\\n" +
        "  --db ~/.succession/evaluator.db \\\n" +
        "  --tenant isolated \\\n" +
        "  --yes \\\n" +
        `  --marketplace ${MARKET}`
      }
    >
      The configured evaluator alone receives the key before settlement. It
      imports into an isolated store, checks the seller signature, and derives
      the root it submits on chain.
    </Step>

    <Step
      n={5}
      title="Claim after settlement"
      command="succession claim --listing listing-672 --db ~/.sibyl-memory/memory.db --tenant my-successor"
    >
      Once evaluation releases payment and transfers the identity, the buyer
      may collect the key and import into a fresh local tenant.
    </Step>
  </>
);

export const COMMANDS = (
  <>
    <P>
      Every command both entry points accept, generated from the parsers
      themselves rather than written here, so this cannot describe a flag the
      tool does not have.
    </P>

    {REFERENCE.groups.map((group) => (
      <section key={group.title} className="mt-12 first:mt-8">
        <h3 className="text-heading font-bold text-ink">{group.title}</h3>
        <p className="mt-1 text-micro text-muted">{group.note}</p>
        {group.commands
          .map((name) => BY_NAME.get(name))
          .filter((c): c is Command => Boolean(c))
          .map((command) => (
            <CommandEntry key={command.name} command={command} />
          ))}
      </section>
    ))}

    <section className="mt-12">
      <h3 className="text-heading font-bold text-ink">Virtuals ACP</h3>
      <p className="mt-1 max-w-[70ch] text-micro text-muted">
        A second entry point, <Code>succession-acp</Code>. It needs a wallet
        whitelisted by Virtuals; until it has one a listing carries no ACP
        history and the valuation scores from the journal instead, which the
        data room states rather than hides.
      </p>
      {REFERENCE["succession-acp"].map((command) => (
        <Panel key={command.name} className="mt-6 p-6">
          <code className="evidence-type text-body font-semibold text-ink">
            succession-acp {command.name}
          </code>
          <p className="mt-2 max-w-[70ch] text-micro text-muted">{command.help}</p>
        </Panel>
      ))}
    </section>
  </>
);

const MCP_TOOLS: [string, string, boolean][] = [
  ["inventory", "What this agent has to sell, per directory.", false],
  ["preview", "The pre-purchase data room. Counts, never record bodies.", false],
  ["value", "The valuation, with every factor's inputs and multiplier.", false],
  ["prove", "Prove a sale would carry every selected directory intact.", false],
  ["audit", "Check every claim the project makes about itself.", false],
  ["marketplace_listings", "Listings on a marketplace, read from the contract.", false],
  ["activity", "What has happened on the contract, newest first.", false],
  ["listing_detail", "One listing's full data room before any money moves.", false],
  ["buy", "Fund escrow. Irreversible from the buyer's side.", true],
  ["evaluate", "Independently verify and settle an escrowed delivery.", true],
  ["list_for_sale", "Sell memory. Seals the origin agent once settled.", true],
  ["fulfil", "Release a content key to the evaluator after escrow.", true],
  ["claim", "After settlement, collect and import memory you paid for.", true],
];

export const FOR_AGENTS = (
  <>
    <P>
      Succession is a protocol for what happens to agent memory, so an agent
      should be able to drive it rather than only a person at a terminal. The
      MCP server exposes the same surface the CLI does, calling the same
      functions.
    </P>
    <div className="mt-5">
      <Copyable text={'pipx install "succession-cli[chain,mcp]"\nsuccession-mcp'} />
    </div>

    <H>The write gate</H>
    <P>
      Five of the thirteen tools spend money, release a decryption key, or
      permanently seal an agent. They refuse unless{" "}
      <Code>SUCCESSION_MCP_ALLOW_WRITES=1</Code> is set, and say so rather than
      failing obscurely. That gate is not security, since anyone who can set the
      variable can also run the CLI. It is there so an agent enumerating its own
      tools cannot end its memory's life because a description sounded useful.
    </P>

    <div className="mt-8">
      <Table head={["Tool", "What it does", "Gated"]}>
        {MCP_TOOLS.map(([name, note, gated]) => (
          <tr key={name} className="border-b border-hairline">
            <Td>
              <code className="evidence-type text-micro text-ink">{name}</code>
            </Td>
            <Td>
              <span className="text-micro text-muted">{note}</span>
            </Td>
            <Td>
              {gated ? (
                <Badge tone="void">needs the gate</Badge>
              ) : (
                <span className="text-micro text-faint">always available</span>
              )}
            </Td>
          </tr>
        ))}
      </Table>
    </div>
  </>
);

export const ENVIRONMENT = (
  <>
    <P>
      Keys are read from the environment and never from an argument, because a
      private key on a command line lands in shell history and in the process
      table.
    </P>
    <div className="mt-8">
      <Table head={["Variable", "What it is for"]}>
        {REFERENCE.env.map((entry) => (
          <tr key={entry.name} className="border-b border-hairline">
            <Td>
              <code className="evidence-type text-micro text-ink">{entry.name}</code>
            </Td>
            <Td>
              <span className="text-micro text-muted">{entry.help}</span>
            </Td>
          </tr>
        ))}
      </Table>
    </div>
  </>
);
