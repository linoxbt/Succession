/**
 * The activity ledger.
 *
 * The rest of the console answers "what is true now". This answers "what
 * happened", which is the question a dashboard is actually for: when a listing
 * was made, when escrow landed, who bought it, which transaction settled it.
 *
 * Every row traces to a transaction hash on Basescan. Nothing here is derived
 * from the service's own records, because these are contract events, so a
 * demonstration listing cannot appear in this list at all. That is a stronger
 * guarantee than filtering: there is nothing to filter.
 */
import { formatAmount, type ActivityEvent } from "../api";
import { explorerTx } from "../chain/config";
import { Badge, Empty, type Tone } from "../ui";

/** What each event means, in the language of the sale rather than of the ABI. */
const MEANING: Record<string, { label: string; tone: Tone; line: string }> = {
  Listed: {
    label: "listed",
    tone: "neutral",
    line: "A root was committed on chain, before any buyer existed.",
  },
  Escrowed: {
    label: "escrow funded",
    tone: "escrow",
    line: "A buyer's funds are held by the contract. Nothing has settled.",
  },
  TransferConfirmed: {
    label: "settled",
    tone: "closed",
    line: "The delivered root matched. Paid, identity moved, seller sealed.",
  },
  Refunded: {
    label: "refunded",
    tone: "void",
    line: "The hash did not match, so the buyer was made whole.",
  },
  Cancelled: {
    label: "cancelled",
    tone: "neutral",
    line: "The seller withdrew the listing before anyone funded it.",
  },
  AgentSealed: {
    label: "agent sealed",
    tone: "closed",
    line: "The origin agent's writes were closed permanently. There is no unseal.",
  },
};

function when(timestamp: number | null): string {
  if (!timestamp) return "";
  return new Date(timestamp * 1000).toISOString().replace("T", " ").slice(0, 19);
}

function short(value: unknown): string {
  const text = String(value ?? "");
  return text.length > 22 ? `${text.slice(0, 10)}…${text.slice(-6)}` : text;
}

/** The detail worth reading per kind, rather than every decoded argument. */
function detail(event: ActivityEvent): string {
  const args = event.args;
  switch (event.event) {
    case "Listed":
      return args.price ? `${formatAmount(Number(args.price), "USDC")} asked` : "";
    case "Escrowed":
      return `${short(args.buyer)} funded ${formatAmount(Number(args.amount ?? 0), "USDC")}`;
    case "TransferConfirmed":
      return `${formatAmount(Number(args.amount ?? 0), "USDC")} released`;
    case "Refunded":
      return String(args.reason || "no reason recorded");
    case "Cancelled":
      return `withdrawn by ${short(args.seller)}`;
    case "AgentSealed":
      return `agent ${args.agentId ?? ""}, former owner ${short(args.formerOwner)}`;
    default:
      return "";
  }
}

export default function Ledger({
  events,
  emptyNote,
}: {
  events: ActivityEvent[];
  emptyNote: string;
}) {
  if (events.length === 0) return <Empty>{emptyNote}</Empty>;

  return (
    <div className="border-t border-hairline">
      {events.map((event) => {
        const meaning = MEANING[event.event] ?? {
          label: event.event,
          tone: "neutral" as Tone,
          line: "",
        };
        return (
          <div
            key={`${event.tx}-${event.event}-${event.block}`}
            className="grid gap-x-8 gap-y-2 border-b border-hairline py-5 lg:grid-cols-[9rem_1fr_auto] lg:items-baseline"
          >
            <Badge tone={meaning.tone}>{meaning.label}</Badge>

            <div className="min-w-0">
              <div className="flex flex-wrap items-baseline gap-x-4">
                {event.listing_id ? (
                  <span className="evidence-type text-body text-ink">
                    {event.listing_id}
                  </span>
                ) : (
                  <span className="text-body text-muted">no listing</span>
                )}
                <span className="text-micro text-muted">{detail(event)}</span>
              </div>
              <p className="mt-1 max-w-measure text-micro text-faint">
                {meaning.line}
              </p>
            </div>

            <div className="lg:text-right">
              <a
                href={explorerTx(event.tx)}
                target="_blank"
                rel="noreferrer"
                className="link-underline evidence-type text-micro text-muted hover:text-ink"
              >
                {short(event.tx)}
              </a>
              <div className="tnum mt-1 text-micro text-faint">
                {when(event.timestamp) || `block ${event.block}`}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
