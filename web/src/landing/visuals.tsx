/**
 * The page's two illustrations, both drawn rather than photographed.
 *
 * Stock imagery would be the wrong instrument here. This product's subject is a
 * mechanism, records moving between stores under a hash commitment, and a
 * photograph of a server rack says nothing true about it. These draw the actual
 * thing.
 *
 * They used to animate: packets travelling a wire, hashes scrambling into
 * place, a checkmark fading up on a timer. All of it is gone, because the brief
 * permits exactly one animated moment in the product and it is not here. A
 * hash that resolves on a timer is also quietly dishonest, it performs a
 * verification that is not happening, on a page where the whole argument is
 * that the verification is real. Static, the same diagram makes a claim the
 * reader can check in the console instead of watching a simulation of.
 *
 * Colours come from the state palette and are used as the console uses them:
 * escrow blue marks the on-chain commitment, closed green marks a verified
 * match, and nothing else is coloured at all.
 */

const ROOT = "0x8a87d0a602d19b8685208b9896d1195c3a83986a694033f0c70b0ded8242aa9c";

const INK = "#23272B";
const MUTED = "#5C6165";
const FAINT = "#8A8F93";
const RULE = "#CFC8B8";
const HAIRLINE = "#DCD6C7";
const PARCHMENT = "#E8E3D6";
const ESCROW = "#2E4A6B";

/**
 * The transfer, as a sequence.
 *
 * Records leave the seller's store, become one committed root, and arrive in a
 * tenant that was empty, the claim the whole system exists to make checkable,
 * so it is worth drawing literally.
 */
export function TransferDiagram() {
  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox="0 0 900 250"
        className="w-full min-w-[680px]"
        role="img"
        aria-label="Records leave the seller's store, are committed as one Merkle root on Base, and arrive in the buyer's previously empty tenant."
      >
        <Store x={20} label="Origin tenant" sub="5 tiers, 49 records" filled />
        <Store x={660} label="Successor tenant" sub="empty until settlement" filled={false} />

        {/* The path the records travel. One hairline, no gradient, no motion. */}
        <line x1={244} y1={125} x2={656} y2={125} stroke={RULE} strokeWidth={1} />
        <polygon points="656,125 648,121 648,129" fill={RULE} />

        {/* The commitment, sitting on the path. */}
        <g transform="translate(382 74)">
          <rect width={136} height={102} fill="none" stroke={ESCROW} strokeWidth={1} />
          <text x={68} y={24} textAnchor="middle" fill={MUTED} fontSize={9} letterSpacing="1.3">
            MERKLE ROOT
          </text>
          <text
            x={68}
            y={50}
            textAnchor="middle"
            fill={INK}
            fontSize={13}
            fontFamily="'IBM Plex Mono', monospace"
          >
            8a87d0a6
          </text>
          <text
            x={68}
            y={68}
            textAnchor="middle"
            fill={INK}
            fontSize={13}
            fontFamily="'IBM Plex Mono', monospace"
          >
            …8242aa9c
          </text>
          <text x={68} y={88} textAnchor="middle" fill={ESCROW} fontSize={9} letterSpacing="1.2">
            ON BASE
          </text>
        </g>
      </svg>
    </div>
  );
}

function Store({
  x,
  label,
  sub,
  filled,
}: {
  x: number;
  label: string;
  sub: string;
  filled: boolean;
}) {
  return (
    <g transform={`translate(${x} 35)`}>
      <rect width={224} height={180} fill="none" stroke={RULE} strokeWidth={1} />
      <text x={20} y={30} fill={INK} fontSize={13} fontWeight={600}>
        {label}
      </text>
      <text x={20} y={50} fill={MUTED} fontSize={11}>
        {sub}
      </text>
      {["identity", "relationships", "commitments", "history"].map((tier, i) => (
        <g key={tier} transform={`translate(20 ${68 + i * 26})`}>
          <rect
            width={184}
            height={18}
            fill={filled ? PARCHMENT : "none"}
            stroke={filled ? "none" : HAIRLINE}
            strokeDasharray={filled ? undefined : "3 3"}
          />
          <text x={9} y={13} fill={filled ? MUTED : FAINT} fontSize={10}>
            {tier}
          </text>
        </g>
      ))}
    </g>
  );
}

/**
 * The credibility beat: the two hashes, side by side, and the verdict.
 *
 * Shown resolved rather than resolving. The comparison is the product's
 * argument, and an argument does not need a reveal.
 */
export function HashVerification() {
  return (
    <div className="border border-rule">
      <div className="grid divide-y divide-hairline sm:grid-cols-2 sm:divide-x sm:divide-y-0">
        <HashPane
          label="Committed at listing"
          caption="Posted before a buyer existed"
          value={ROOT}
          tone="neutral"
        />
        <HashPane
          label="Re-hashed on the buyer's store"
          caption="Derived after the import, from their own records"
          value={ROOT}
          tone="closed"
        />
      </div>
      <div className="flex flex-wrap items-center gap-3 border-t border-rule px-6 py-4">
        <span
          className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-closed text-closed"
          aria-hidden
        >
          <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none">
            <path
              d="M4.5 10.5l3.5 3.5 7.5-8"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span className="text-body text-closed">
          Match, escrow released, identity transferred, origin sealed
        </span>
      </div>
    </div>
  );
}

function HashPane({
  label,
  caption,
  value,
  tone,
}: {
  label: string;
  caption: string;
  value: string;
  tone: "neutral" | "closed";
}) {
  return (
    <div className="p-6">
      <p className="text-label uppercase tracking-[0.08em] text-faint">{label}</p>
      <p
        className={`mt-3 break-all font-mono text-micro leading-relaxed ${
          tone === "closed" ? "text-closed" : "text-ink"
        }`}
      >
        {value}
      </p>
      <p className="mt-3 text-micro text-muted">{caption}</p>
    </div>
  );
}
