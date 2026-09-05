/**
 * The documentation, in the app.
 *
 * The repository has the full specs; this is the version someone reads while
 * looking at the console, so it stays at the level of "what is this and why is
 * it built that way" rather than reproducing the format byte layout. Sections
 * are addressable, so a link into a specific answer works.
 */
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Badge, Section, Rule, Table, Td } from "../ui";

interface Doc {
  id: string;
  title: string;
  body: ReactNode;
}

const DOCS: Doc[] = [
  {
    id: "overview",
    title: "What Succession is",
    body: (
      <>
        <P>
          Code gives an agent capability. A model gives it reasoning. Memory gives
          it continuity, and Succession gives that continuity an economic life
          beyond the original agent.
        </P>
        <P>
          The model and the code are the employee. The accumulated memory is the
          customer book: the relationships, preferences and institutional
          knowledge that make an operating business worth more than its
          equipment. Succession does not sell the employee. It makes the customer
          book itself a transferable asset.
        </P>
        <Callout>
          Delete the memory layer and there is no product, no asset, no hash to
          commit, no data room, and no cutover. That is the test, and it is the
          point.
        </Callout>
      </>
    ),
  },
  {
    id: "flow",
    title: "How a sale works",
    body: (
      <>
        <Ol
          items={[
            ["Export", "The seller's tenant is filtered, serialized and hashed into a Succession Memory Package, signed with the key holding the agent's ERC-8004 identity."],
            ["List", "The Merkle root is committed to ListingContract on Base, before any buyer exists."],
            ["Preview", "A buyer sees aggregate statistics only, counts, never record bodies, beside verifiable ACP job history."],
            ["Escrow", "The buyer funds the contract. Nothing has moved: the seller cannot touch the money, the buyer holds no identity."],
            ["Deliver", "The package travels encrypted. The content key is released only against funded escrow."],
            ["Re-key", "It imports into a brand-new tenant under the buyer's tenant id."],
            ["Verify", "The buyer re-exports their own store and re-derives the root."],
            ["Settle", "confirmTransfer releases payment, transfers the identity token, and sets the sealed flag, in one transaction, or none."],
            ["Record", "The acquisition is written into the buyer's memory, extending the provenance chain for any future resale."],
          ]}
        />
        <Callout>
          Verification re-hashes the destination, not the bytes on the wire.
          Checking what arrived only proves the courier was honest; re-hashing the
          buyer's store proves the importer wrote what it received and the engine
          did not silently coerce anything.
        </Callout>
      </>
    ),
  },
  {
    id: "smp",
    title: "The memory package",
    body: (
      <>
        <P>
          Nine directories. Six carry memory; three are generated at build time
          and describe the package rather than living inside it.
        </P>
        <Table head={["Directory", "Carries"]}>
          {[
            ["identity/", "The agent's own registration record"],
            ["relationships/", "Per-counterparty entities, and the edges between them"],
            ["preferences/", "Learned settings and operating limits"],
            ["history/", "The journal, archived records, and verifiable ACP job history"],
            ["commitments/", "Open quotes, agreed terms, and live working state"],
            ["learned-behaviors/", "Adapted patterns and encoded playbooks"],
            ["provenance/", "Origin, version, prior-owner chain, signature"],
            ["permissions/", "Redaction flags, consent basis, access tiers"],
            ["integrity-proof/", "Merkle root and per-category subroots"],
          ].map(([dir, carries]) => (
            <tr key={dir}>
              <Td className="font-mono text-escrow">{dir}</Td>
              <Td className="text-muted">{carries}</Td>
            </tr>
          ))}
        </Table>
        <P className="mt-6">
          A directory is a <em>selection unit</em>, not a storage location, it is
          what partial succession filters on and what gets its own Merkle subroot.
          Every record also carries its <Code>origin</Code>, the exact tier and
          category it held in the source engine, which is what the importer
          re-keys against. So the grouping can be opinionated without ever being
          lossy.
        </P>
      </>
    ),
  },
  {
    id: "integrity",
    title: "The integrity scheme",
    body: (
      <>
        <P>
          A two-level Merkle tree over keccak256: a subroot per category, then a
          root over the <Code>(category, subroot)</Code> pairs. The two-level
          shape is what makes partial succession verifiable without a redesign; a
          flat hash would have needed one.
        </P>
        <Table head={["Decision", "Why"]}>
          {[
            ["Leaves and nodes are domain-separated", "Stops an internal node being presented as a leaf, the classic second-preimage attack"],
            ["An odd node is promoted, never duplicated", "Duplication makes two different leaf sets produce the same root"],
            ["The category name is bound to its subroot", "A seller cannot relabel a cheap directory as an expensive one"],
            ["Timestamps and row ids are excluded from leaves", "Destinations assign their own; hashing them would fail every honest import"],
            ["Ties break on content hash, not row id", "Row ids do not survive a transfer; two events in one millisecond must still sort identically"],
          ].map(([d, why]) => (
            <tr key={d}>
              <Td>{d}</Td>
              <Td className="text-muted">{why}</Td>
            </tr>
          ))}
        </Table>
        <P className="mt-6">
          The provenance header is signed in full, not just the root. Signing the
          bare root would leave the agent identity and the owner chain
          unauthenticated, an intercepted package could keep a valid signature
          while claiming to be a different, more valuable agent.
        </P>
      </>
    ),
  },
  {
    id: "privacy",
    title: "Privacy and redaction",
    body: (
      <>
        <P>Two independent axes, deliberately not collapsed into one.</P>
        <Table head={["Flag", "Meaning"]}>
          {[
            ["sensitivity: public", "Visible in the pre-purchase data room"],
            ["sensitivity: private", "Transfers with the sale, never previewed"],
            ["sensitivity: redacted-preview-only", "Counts toward aggregates; body never leaves before purchase"],
            ["transferable: false", "Absolute. Outranks every tier, buyer and category selection, permanently"],
          ].map(([flag, meaning]) => (
            <tr key={flag}>
              <Td className="font-mono text-escrow">{flag}</Td>
              <Td className="text-muted">{meaning}</Td>
            </tr>
          ))}
        </Table>
        <Callout>
          Filtering runs before hashing, not before display. A withheld record
          never reaches the Merkle tree in recoverable form, otherwise anyone
          able to diff two packages could recover it.
        </Callout>
        <P className="mt-6">
          An unflagged record defaults to <Code>private</Code> and{" "}
          <Code>transferable</Code>: part of the asset, but not leaking into a
          preview because nobody remembered to flag it.
        </P>
      </>
    ),
  },
  {
    id: "valuation",
    title: "Valuation",
    body: (
      <>
        <P>
          Five clamped factors, exact decimal, re-derivable by hand. Every factor
          reports its own inputs and a sentence explaining what it did with them.
        </P>
        <Pre>{`valuation = base_price
          × tenure_factor        age of the tenant
          × interaction_density  journal events per day
          × relationship_breadth distinct counterparties
          × task_performance     ACP outcomes, else the journal
          × recency_weight       time since the last write`}</Pre>
        <P className="mt-6">
          <Code>task_performance</Code> prefers the real completed-versus-
          cancelled ratio from Virtuals ACP over reading English out of the
          seller's own journal. It falls back on a thin sample rather than
          treating two-for-two as a perfect record.
        </P>
        <Callout tone="escrow">
          There is no buyer-demand term and no memory-reputation score. Those are
          real inputs at protocol scale and meaningless in a single-listing demo,
          and a hardcoded "12 buyers watching" is exactly the pattern a technical
          reader probes first.
        </Callout>
      </>
    ),
  },
  {
    id: "sealing",
    title: "Sealing the seller's copy",
    body: (
      <>
        <P>What stops a seller keeping a copy and carrying on? Two layers.</P>
        <Ol
          items={[
            ["Contract-level", "confirmTransfer sets a sealed flag against the agentId, readable by anyone. A sealed agent cannot be relisted."],
            ["Service-level", "The seller's credentials for that tenant are revoked, and every write path, the adapter and the underlying client, checks the seal first and rejects unconditionally."],
          ]}
        />
        <Callout tone="escrow">
          What sealing does not claim: the seller's database file still exists on
          their disk, and nothing reaches onto their machine. The guarantee is
          narrower and actually enforceable, that copy can no longer
          authenticate, sync, or be represented anywhere as the live agent. The
          asset was never the bytes; it was the right to be that agent.
        </Callout>
        <P className="mt-6">
          There is deliberately no <Code>unseal</Code>. It would recreate exactly
          the state the seal prevents, and an admin escape hatch is the same hole
          with a login page in front of it.
        </P>
      </>
    ),
  },
  {
    id: "limits",
    title: "Known limits",
    body: (
      <>
        <P>Stated rather than discovered.</P>
        <Ul
          items={[
            "The buyer asserts the delivered hash. A dishonest buyer can submit a wrong one, take the automatic refund, and keep the decrypted package. No on-chain logic closes this, the chain cannot see the delivered bytes. The contract's arbiter role is the hook for an Evaluator-style agent that re-derives it independently.",
            "Atomicity is by ordering, not by magic. One transaction cannot span the chain and an off-chain store; confirmTransfer is genuinely atomic because it is one EVM transaction, and delivery and sealing are ordered around it so every intermediate state is safe to abandon.",
            "relationships/ carries the WARM edges, so its subroot depends on which other categories travel with it, an edge is pruned when the entity at its far end is not part of the sale.",
            "Relationship records describe real counterparties. A production version needs a real answer to what terms let that data move with a sale, grounded in the operator's own terms of service. A hackathon build should not pretend to solve it.",
          ]}
        />
      </>
    ),
  },
];

export function Docs() {
  const [active, setActive] = useState(DOCS[0]!.id);
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    if (!query.trim()) return DOCS;
    const q = query.toLowerCase();
    return DOCS.filter((d) => d.title.toLowerCase().includes(q) || d.id.includes(q));
  }, [query]);

  // Deep links: /app#integrity opens that section.
  useEffect(() => {
    const hash = window.location.hash.replace("#", "");
    if (hash && DOCS.some((d) => d.id === hash)) setActive(hash);
  }, []);

  const doc = DOCS.find((d) => d.id === active) ?? DOCS[0]!;

  return (
    <div className="grid gap-6 lg:grid-cols-[15rem_1fr]">
      <nav className="lg:sticky lg:top-24 lg:self-start">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter"
          aria-label="Filter documentation"
          className="mb-3 w-full border border-rule bg-paper px-3 py-2 text-micro placeholder:text-faint"
        />
        <ul className="space-y-0.5">
          {filtered.map((d) => (
            <li key={d.id}>
              <button
                onClick={() => {
                  setActive(d.id);
                  window.history.replaceState({}, "", `#${d.id}`);
                }}
                aria-current={active === d.id ? "page" : undefined}
                className={`w-full border-l py-2 pl-4 pr-3 text-left text-micro transition-[border-color,color,transform] duration-500 ease-swift ${
                  active === d.id
                    ? "border-ink text-ink"
                    : "border-transparent text-faint hover:translate-x-1 hover:text-ink"
                }`}
              >
                {d.title}
              </button>
            </li>
          ))}
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-micro text-faint">No match.</li>
          ) : null}
        </ul>
      </nav>

      <Section title={doc.title}>
        <article className="px-6 py-6">{doc.body}</article>
        <Rule />
        <div className="flex flex-wrap items-center gap-3 px-6 py-4 text-xs text-faint">
          <span>Full specifications in the repository:</span>
          <a
            href="https://github.com/linoxbt/Succession/blob/main/docs/smp-format.md"
            className="text-escrow hover:underline"
          >
            SMP format
          </a>
          <a
            href="https://github.com/linoxbt/Succession/blob/main/docs/sibyl-setup.md"
            className="text-escrow hover:underline"
          >
            Memory brief
          </a>
          <a
            href="https://github.com/linoxbt/Succession/blob/main/docs/ROADMAP.md"
            className="text-escrow hover:underline"
          >
            Roadmap
          </a>
        </div>
      </Section>
    </div>
  );
}

// -- small prose primitives ------------------------------------------------

/** Body copy is ink. Muted is for labels and asides, a document whose own
 *  argument is set in the secondary colour reads as a footnote to itself. */
function P({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <p className={`mt-4 max-w-[70ch] text-body text-ink ${className}`}>
      {children}
    </p>
  );
}

function Code({ children }: { children: ReactNode }) {
  return (
    <code className="bg-shade px-1.5 py-0.5 font-mono text-micro text-ink">
      {children}
    </code>
  );
}

function Pre({ children }: { children: string }) {
  return (
    <pre className="mt-5 overflow-x-auto border border-rule bg-shade p-4 font-mono text-micro leading-relaxed text-ink">
      {children}
    </pre>
  );
}

function Callout({ children, tone = "escrow" }: { children: ReactNode; tone?: "escrow" | "void" }) {
  const border = tone === "void" ? "border-void/40" : "border-escrow/40";
  return (
    <div className={`mt-6 border-l-2 ${border} pl-4`}>
      <p className="max-w-[68ch] text-body text-ink">{children}</p>
    </div>
  );
}

function Ol({ items }: { items: [string, string][] }) {
  return (
    <ol className="mt-5 space-y-3">
      {items.map(([term, line], i) => (
        <li key={term} className="flex gap-4">
          <span className="tnum w-5 shrink-0 pt-0.5 text-xs text-faint">{i + 1}</span>
          <span className="max-w-[66ch] text-body">
            <span className="font-medium text-ink">{term}. </span>
            <span className="text-ink">{line}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

function Ul({ items }: { items: string[] }) {
  return (
    <ul className="mt-5 space-y-3">
      {items.map((line) => (
        <li key={line} className="flex gap-3">
          <span className="pt-2 text-faint" aria-hidden>
            <Badge>·</Badge>
          </span>
          <span className="max-w-[68ch] text-body text-ink">
            {line}
          </span>
        </li>
      ))}
    </ul>
  );
}
