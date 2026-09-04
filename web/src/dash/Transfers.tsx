/**
 * The settlement ledger.
 *
 * One row per transfer, verified and refunded alike. Refunds are not hidden or
 * filtered out by default: a ledger that shows only the wins is a marketing
 * page, and the refund path is the half that protects the buyer.
 */
import type { Outcome } from "../api";
import { Badge, Empty, Hash, Section, Table, Td } from "../ui";

export interface TransferRow {
  index: number;
  agent_id: string;
  listing_id: string;
  outcome: "verified" | "refunded";
  committed_root: string;
  delivered_root: string;
  tx: string;
  explorer?: string;
  intentionally_corrupted?: boolean;
}

export function Transfers({
  rows,
  current,
}: {
  rows: TransferRow[];
  current: Outcome | null;
}) {
  const all: TransferRow[] = [...rows];
  if (current?.receipt) {
    all.unshift({
      index: 0,
      agent_id: current.certificate?.origin_agent ?? "—",
      listing_id: current.listing_id,
      outcome: current.outcome,
      committed_root: current.committed_root,
      delivered_root: current.delivered_root,
      tx: current.receipt.reference,
    });
  }

  const verified = all.filter((r) => r.outcome === "verified").length;

  if (!all.length) {
    return (
      <Section title="Settlement ledger">
        <Empty>No transfers yet.</Empty>
      </Section>
    );
  }

  return (
    <Section
      title="Settlement ledger"
      action={
        <span className="text-[0.8125rem] text-muted tnum">
          {verified} verified · {all.length - verified} refunded
        </span>
      }
    >
      <div className="mt-4" />
      <Table head={["Agent", "Committed", "Delivered", "Outcome", "Transaction"]}>
        {all.map((row) => (
          <tr key={`${row.listing_id}-${row.index}`}>
            <Td>
              <span className="font-mono text-[0.8125rem]">{row.agent_id}</span>
              {row.intentionally_corrupted ? (
                <span className="ml-2 text-[0.75rem] text-muted">corrupted on purpose</span>
              ) : null}
            </Td>
            <Td>
              <Hash value={row.committed_root} chars={6} />
            </Td>
            <Td>
              <Hash value={row.delivered_root} chars={6} />
            </Td>
            <Td>
              <Badge tone={row.outcome === "verified" ? "closed" : "void"}>
                {row.outcome === "verified" ? "Released" : "Refunded"}
              </Badge>
            </Td>
            <Td>
              {row.explorer ? (
                <a
                  href={row.explorer}
                  target="_blank"
                  rel="noreferrer"
                  className="underline underline-offset-4 hover:text-escrow"
                >
                  <Hash value={row.tx} chars={6} />
                </a>
              ) : (
                <Hash value={row.tx} chars={6} />
              )}
            </Td>
          </tr>
        ))}
      </Table>
    </Section>
  );
}
