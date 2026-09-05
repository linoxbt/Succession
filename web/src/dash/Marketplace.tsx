/**
 * Real listings, read from the contract.
 *
 * Every row here exists because a seller ran `succession list` against their own
 * Sibyl store and paid gas to commit its root. There is no seed data and no
 * fallback: an empty marketplace means nobody has listed yet, which is a true
 * answer and the only honest one available. A screen that filled itself with
 * plausible rows would be exactly the pattern this project argues against.
 *
 * The figures come from two places on purpose. The seller, the commitment, the
 * price and the state are read from `ListingContract` — it is authoritative and
 * this page shows what it says. The counts and the valuation come from the
 * seller's published metadata, because the contract has no field for them and
 * should not.
 */
import type { MarketRow } from "../api";
import { formatAmount } from "../api";
import { Badge, Button, Empty, Hash, Note, Section, Table, Td } from "../ui";

export default function Marketplace({
  rows,
  onChain,
  onOpen,
  onSell,
  onRefresh,
}: {
  rows: MarketRow[];
  onChain: boolean | null;
  onOpen: (row: MarketRow) => void;
  onSell: () => void;
  onRefresh: () => void;
}) {
  return (
    <div className="flex flex-col gap-8">
      <Section
        title="Marketplace"
        action={
          <div className="flex gap-4">
            <Button size="sm" variant="quiet" onClick={onRefresh}>
              Refresh
            </Button>
            <Button size="sm" variant="ghost" onClick={onSell}>
              Sell your agent
            </Button>
          </div>
        }
      >
        <p className="max-w-column text-[0.9375rem] leading-relaxed text-muted">
          Agent memory offered for sale. Each row's committed hash was posted on
          chain before a buyer existed, so it cannot have been computed after the
          fact to match whatever was delivered.
        </p>
      </Section>

      {onChain === false ? (
        <Note>
          No contract is deployed, so there is nothing to read. This marketplace
          takes its listings from <code>ListingContract</code> and has no offline
          mode — there is deliberately no configuration that makes it show
          listings without one.
        </Note>
      ) : null}

      {rows.length === 0 ? (
        <Empty>
          {onChain
            ? "No listings yet. The first seller to run succession list will appear here."
            : "Nothing to show."}
        </Empty>
      ) : (
        <Table head={["Agent", "Records", "Committed hash", "Price", "State", ""]}>
          {rows.map((row) => {
            const records = Object.values(row.preview?.counts ?? {}).reduce(
              (a, b) => a + b,
              0,
            );
            return (
              <tr key={row.listing.listing_id} className="border-b border-hairline">
                <Td>
                  <span className="text-ink">{row.name || row.agent_identity}</span>
                  {row.vertical ? (
                    <span className="ml-2 text-[0.75rem] text-faint">{row.vertical}</span>
                  ) : null}
                </Td>
                <Td className="tnum">{records || "—"}</Td>
                <Td>
                  <Hash value={row.listing.hash_commitment} />
                </Td>
                <Td className="tnum">
                  {formatAmount(row.listing.price, row.listing.currency)}
                </Td>
                <Td>
                  <Badge tone={row.listing.state === "open" ? "neutral" : "escrow"}>
                    {row.listing.state}
                  </Badge>
                </Td>
                <Td>
                  <Button size="sm" variant="quiet" onClick={() => onOpen(row)}>
                    Open
                  </Button>
                </Td>
              </tr>
            );
          })}
        </Table>
      )}
    </div>
  );
}
