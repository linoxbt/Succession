/**
 * The dashboard.
 *
 * One read, not five. Assembling this from separate calls would leave it
 * half-drawn for the first second and repeat the same bounded log scan each
 * time, so `/api/overview` aggregates at the source and this renders it.
 *
 * The figures are derived from the listings rather than tracked in a tally.
 * A stored count is a second source of truth that drifts from the first, and
 * the argument this whole project makes is that there is only one.
 */
import { useEffect, useState } from "react";
import { useAccount } from "wagmi";

import { formatAmount, type AgentsHeld, type Overview } from "../api";
import { service } from "../services";
import { explorerAddress } from "../chain/config";
import { Badge, Empty, Figure, Hash, Note, PageHead, Section, Table, Td } from "../ui";
import { Reveal } from "../motion";

const STATE_TONE: Record<string, "neutral" | "escrow" | "closed" | "void"> = {
  open: "neutral",
  escrowed: "escrow",
  confirmed: "closed",
  refunded: "void",
};

export default function Dashboard({
  onOpenListing,
}: {
  onOpenListing: (listingId: string) => void;
}) {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { address, isConnected } = useAccount();
  const [held, setHeld] = useState<AgentsHeld | null>(null);

  useEffect(() => {
    let live = true;
    service
      .overview()
      .then((body) => live && setData(body))
      .catch((e) => live && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (!address) {
      setHeld(null);
      return;
    }
    let live = true;
    service
      .agents(address)
      .then((body) => live && setHeld(body))
      .catch(() => live && setHeld(null));
    return () => {
      live = false;
    };
  }, [address]);

  const totals = data?.totals ?? {};
  const byState = totals.by_state ?? {};
  const deployment = data?.deployment ?? null;

  return (
    <div>
      <PageHead
        index="00 / Overview"
        title="The desk."
        lede={data ? data.explanation : "Reading the contract."}
      />

      {error ? <Note>The service is unreachable ({error}).</Note> : null}

      {/* --- the figures ------------------------------------------------ */}
      <Section index="01" title="Position">
        <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-4">
          <Reveal index={0}>
            <Figure value={String(totals.listings ?? 0)} label="Listings" />
          </Reveal>
          <Reveal index={1}>
            <Figure
              value={formatAmount(totals.volume_settled ?? 0, "USDC").replace(" USDC", "")}
              label="Settled, USDC"
              tone="closed"
            />
          </Reveal>
          <Reveal index={2}>
            <Figure
              value={formatAmount(totals.volume_open ?? 0, "USDC").replace(" USDC", "")}
              label="Open, USDC"
            />
          </Reveal>
          <Reveal index={3}>
            <Figure value={String(totals.agents ?? 0)} label="Agents listed" />
          </Reveal>
        </div>

        <div className="mt-12 flex flex-wrap gap-3">
          {Object.entries(byState).map(([state, n]) => (
            <Badge key={state} tone={STATE_TONE[state] ?? "neutral"}>
              {n} {state}
            </Badge>
          ))}
        </div>

        {totals.listings ? (
          <Note>
            {totals.with_data_room ?? 0} of {totals.listings} sellers published a
            data room. The rest are listed on chain and undescribed, which is a
            real gap rather than a rendering one.
          </Note>
        ) : null}
      </Section>

      {/* --- what actually transfers ------------------------------------- */}
      <Section index="02" title="What transfers" className="mt-chapter">
        <Table head={["Directory", "Status", "Sellable", "Withheld", "In listings"]}>
          {(data?.capabilities ?? []).map((c) => (
            <tr key={c.category} className="border-b border-hairline">
              <Td>
                <span className="evidence-type text-ink">{c.category}</span>
                <span className="mt-1 block max-w-prose text-micro text-muted">
                  {c.note}
                </span>
              </Td>
              <Td>
                <Badge tone={c.transferable ? "closed" : "neutral"}>
                  {c.transferable ? "live" : "coming soon"}
                </Badge>
              </Td>
              <Td className="tnum">
                {c.transferable ? c.records_sellable : ""}
              </Td>
              <Td className="tnum">
                {c.transferable ? c.records_withheld : ""}
              </Td>
              <Td className="tnum">{c.transferable ? c.listings : ""}</Td>
            </tr>
          ))}
        </Table>
        <Note>
          Six directories carry memory and are the selectable units of a sale,
          each with its own Merkle subroot, so a seller can part with a
          percentage of one without touching another. The last three describe
          the package rather than the memory, so they are built rather than
          sold. Withheld counts records a counterparty never consented to move, so
          the seller cannot offer them at any price. Both figures come from
          published data rooms, which is why they read zero while sellers list
          on chain and describe nothing.
        </Note>
      </Section>

      {/* --- your agents ------------------------------------------------ */}
      <Section index="03" title="Your agents" className="mt-chapter">
        {!isConnected ? (
          <Note>Connect a wallet to see the ERC-8004 agents it holds.</Note>
        ) : !held ? (
          <Note>Reading the registry.</Note>
        ) : held.agents.length === 0 ? (
          <Note>This wallet holds no ERC-8004 agents.</Note>
        ) : (
          <>
            <div className="border-t border-hairline">
              {held.agents.map((a) => (
                <div
                  key={a.identity}
                  className="flex flex-wrap items-baseline gap-x-8 gap-y-1 border-b border-hairline py-4"
                >
                  <span className="evidence-type text-body text-ink">{a.identity}</span>
                  <span className="text-label uppercase tracking-[0.14em] text-faint">
                    token {a.agent_id}
                  </span>
                </div>
              ))}
            </div>
            {!held.complete ? (
              <Note>
                Showing {held.found} of {held.balance}. The registry cannot be
                enumerated directly, so older agents may sit outside the scanned
                range. Everything listed is confirmed on chain.
              </Note>
            ) : null}
          </>
        )}
      </Section>

      {/* --- the market --------------------------------------------------- */}
      <Section index="04" title="The market" className="mt-chapter">
        {!data ? (
          <Empty>Reading the contract.</Empty>
        ) : data.listings.length === 0 ? (
          <Empty>No listings on this contract yet.</Empty>
        ) : (
          <Table head={["Agent", "State", "Price", "Committed hash", ""]}>
            {data.listings.map((row) => (
              <tr
                key={row.listing.listing_id}
                className="border-b border-hairline"
              >
                <Td>
                  <span className="text-ink">
                    {row.name || `Agent ${row.agent_identity}`}
                  </span>
                  {row.has_metadata === false ? (
                    <span className="ml-3 text-label uppercase tracking-[0.14em] text-faint">
                      on chain only
                    </span>
                  ) : null}
                </Td>
                <Td>
                  <Badge tone={STATE_TONE[row.listing.state] ?? "neutral"}>
                    {row.listing.state}
                  </Badge>
                </Td>
                <Td className="tnum">
                  {formatAmount(row.listing.price, row.listing.currency)}
                </Td>
                <Td>
                  <Hash value={row.listing.hash_commitment} />
                </Td>
                <Td>
                  <button
                    onClick={() => onOpenListing(row.listing.listing_id)}
                    className="link-underline font-mono text-label uppercase text-muted hover:text-ink"
                  >
                    Open
                  </button>
                </Td>
              </tr>
            ))}
          </Table>
        )}
        {data?.demo_listings?.length ? (
          <Note>
            {data.demo_listings.length} demonstration listing
            {data.demo_listings.length === 1 ? " is" : "s are"} shown in the
            marketplace and excluded from every figure above. They are not on
            chain and cannot be bought.
          </Note>
        ) : null}
      </Section>

      {/* --- the portable score ------------------------------------------- */}
      <Section index="05" title="Reputation" className="mt-chapter">
        <div className="border-t border-hairline">
          {(data?.reputation_model.factors ?? []).map((f) => (
            <div
              key={f.name}
              className="flex flex-col gap-1 border-b border-hairline py-4 sm:flex-row sm:items-baseline sm:gap-10"
            >
              <span className="w-full shrink-0 font-mono text-label uppercase text-faint sm:w-40">
                {f.name}
              </span>
              <span className="tnum w-16 shrink-0 text-ink">{f.weight}</span>
              <span className="max-w-prose text-micro text-muted">{f.note}</span>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          {(data?.reputation_model.grades ?? []).map((g) => (
            <Badge key={g}>{g}</Badge>
          ))}
        </div>

        {data ? <Note>{data.reputation_model.basis}</Note> : null}

        {(data?.reputation_model.does_not_transfer ?? []).map((d) => (
          <Note key={d.item}>
            Does not transfer, {d.item}. {d.why}
          </Note>
        ))}
      </Section>

      {/* --- what it settles on ------------------------------------------ */}
      <Section index="06" title="Settlement" className="mt-chapter">
        {!deployment ? (
          <Note>No contract deployed.</Note>
        ) : (
          <div className="border-t border-hairline">
            {[
              ["Listing contract", deployment.listing_contract],
              ["Identity registry", deployment.identity_registry],
              ["Payment token", deployment.payment_token],
              ["Arbiter", deployment.arbiter],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex flex-col gap-1 border-b border-hairline py-4 sm:flex-row sm:items-baseline sm:gap-10"
              >
                <span className="w-full shrink-0 font-mono text-label uppercase text-faint sm:w-64">
                  {label}
                </span>
                <a
                  href={explorerAddress(String(value))}
                  target="_blank"
                  rel="noreferrer"
                  className="link-underline evidence-type text-micro text-ink"
                >
                  {value}
                </a>
              </div>
            ))}
          </div>
        )}
        {deployment && !deployment.identity_registry_is_mock ? (
          <Note>
            The identity registry is a real ERC-8004 deployment, not a stand-in.
            Payment settles in Circle's USDC.
          </Note>
        ) : null}
      </Section>
    </div>
  );
}
