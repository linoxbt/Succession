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
 * price and the state are read from `ListingContract`, it is authoritative and
 * this page shows what it says. The counts and the valuation come from the
 * seller's published metadata, because the contract has no field for them and
 * should not.
 */
import type { MarketRow } from "../api";
import { formatAmount } from "../api";
import { Badge, Button, Empty, Hash, Note, PageHead, Table, Td } from "../ui";

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
    <div>
      <PageHead
        index="01 / Marketplace"
        title="Memory, offered for sale."
        lede="Read from the contract."
        action={
          <div className="flex flex-wrap items-center gap-6">
            <Button size="sm" variant="quiet" onClick={onRefresh}>
              Refresh
            </Button>
            <Button size="sm" variant="ghost" onClick={onSell}>
              Sell your agent
            </Button>
          </div>
        }
      />

      {onChain === false ? (
        <Note>No contract deployed.</Note>
      ) : null}

      {rows.length === 0 ? (
        <Empty>
          {onChain
            ? "No listings on this contract yet. The first seller to run succession list will appear here."
            : "No contract is deployed, so there is nothing to read."}
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
                  <span className="text-ink">
                    {row.name || `Agent ${row.agent_identity}`}
                  </span>
                  {row.vertical ? (
                    <span className="ml-2 text-label text-faint">{row.vertical}</span>
                  ) : null}
                  {row.has_metadata === false ? (
                    <span className="ml-3 text-label uppercase tracking-[0.14em] text-faint">
                      on chain only
                    </span>
                  ) : null}
                </Td>
                <Td className="tnum">
                  {records || <span className="text-faint">not published</span>}
                </Td>
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
