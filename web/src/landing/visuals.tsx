/**
 * The page's two illustrations, both drawn rather than photographed.
 *
 * Stock imagery would be the wrong instrument here. This product's subject is a
 * mechanism — records moving between stores under a hash commitment — and a
 * photograph of a server rack says nothing true about it. These draw the actual
 * thing, and animate the part that matters.
 */
import { useEffect, useState } from "react";
import { ScrambleHash, prefersReducedMotion, useInView } from "./motion";

const ROOT = "0x8a87d0a602d19b8685208b9896d1195c3a83986a694033f0c70b0ded8242aa9c";

/**
 * The transfer, as a sequence.
 *
 * Records leave the seller's store, become one committed root, and arrive in a
 * tenant that was empty — which is the claim the whole system exists to make
 * checkable, so it is worth drawing literally.
 */
export function TransferDiagram() {
  const { ref, seen } = useInView<HTMLDivElement>(0.3);

  return (
    <div ref={ref} className="w-full overflow-x-auto">
      <svg
        viewBox="0 0 900 260"
        className={`w-full min-w-[680px] ${seen ? "diagram-in" : ""}`}
        role="img"
        aria-label="Records leave the seller's store, are committed as one Merkle root, and arrive in the buyer's empty tenant."
      >
        <defs>
          <linearGradient id="wire" x1="0" x2="1">
            <stop offset="0" stopColor="#1D9BF0" stopOpacity="0" />
            <stop offset="0.5" stopColor="#1D9BF0" stopOpacity="0.9" />
            <stop offset="1" stopColor="#1D9BF0" stopOpacity="0" />
          </linearGradient>
        </defs>

        <Store x={20} label="Origin tenant" sub="5 tiers, 49 records" filled />
        <Store x={660} label="Successor tenant" sub="empty until settlement" filled={false} />

        {/* The wire the records travel along. */}
        <line x1={244} y1={130} x2={656} y2={130} stroke="#22262B" strokeWidth={1} />
        <line
          x1={244}
          y1={130}
          x2={656}
          y2={130}
          stroke="url(#wire)"
          strokeWidth={2}
          className="wire-pulse"
        />

        {/* The commitment, sitting on the wire. */}
        <g transform="translate(380 78)">
          <rect width={140} height={104} rx={10} fill="#0E1013" stroke="#22262B" />
          <text x={70} y={26} textAnchor="middle" fill="#5A6169" fontSize={10} letterSpacing="1.4">
            MERKLE ROOT
          </text>
          <text x={70} y={52} textAnchor="middle" fill="#E7E9EA" fontSize={13} fontFamily="monospace">
            8a87d0a6
          </text>
          <text x={70} y={70} textAnchor="middle" fill="#E7E9EA" fontSize={13} fontFamily="monospace">
            …8242aa9c
          </text>
          <text x={70} y={90} textAnchor="middle" fill="#1D9BF0" fontSize={10} letterSpacing="1.2">
            ON BASE
          </text>
        </g>

        {/* Records in flight. Staggered, so it reads as a stream. */}
        {[0, 1, 2, 3, 4].map((i) => (
          <rect
            key={i}
            className="packet"
            style={{ animationDelay: `${i * 0.42}s` }}
            y={126}
            width={14}
            height={8}
            rx={2}
            fill="#1D9BF0"
          />
        ))}
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
    <g transform={`translate(${x} 40)`}>
      <rect width={224} height={180} rx={12} fill="#0E1013" stroke="#22262B" />
      <text x={20} y={30} fill="#E7E9EA" fontSize={13} fontWeight={600}>
        {label}
      </text>
      <text x={20} y={50} fill="#5A6169" fontSize={11}>
        {sub}
      </text>
      {["identity", "relationships", "commitments", "history"].map((tier, i) => (
        <g key={tier} transform={`translate(20 ${68 + i * 26})`}>
          <rect
            width={184}
            height={18}
            rx={4}
            fill={filled ? "#16181C" : "none"}
            stroke={filled ? "none" : "#1A1D21"}
            strokeDasharray={filled ? undefined : "3 3"}
          />
          <text x={9} y={13} fill={filled ? "#8B949E" : "#2F343A"} fontSize={10}>
            {tier}
          </text>
        </g>
      ))}
    </g>
  );
}

/**
 * The credibility beat: two hashes settling, then a verdict.
 *
 * The comparison is the product. Showing it as an animation rather than a
 * static pair is the difference between telling a visitor the check happens and
 * letting them watch it resolve.
 */
export function HashVerification() {
  const { ref, seen } = useInView<HTMLDivElement>(0.4);
  const [matched, setMatched] = useState(() => prefersReducedMotion());

  useEffect(() => {
    if (!seen) return;
    if (prefersReducedMotion()) {
      setMatched(true);
      return;
    }
    const timer = setTimeout(() => setMatched(true), 1150);
    return () => clearTimeout(timer);
  }, [seen]);

  return (
    <div ref={ref} className="overflow-hidden rounded-xl border border-line bg-panel">
      <div className="grid divide-y divide-line sm:grid-cols-2 sm:divide-x sm:divide-y-0">
        <HashPane
          label="Committed at listing"
          caption="Posted before a buyer existed"
          value={ROOT}
          active={seen}
          tone="neutral"
        />
        <HashPane
          label="Re-hashed on the buyer's store"
          caption="Derived after the import, from their own records"
          value={ROOT}
          active={seen}
          tone={matched ? "good" : "neutral"}
        />
      </div>
      <div className="flex flex-wrap items-center gap-3 border-t border-line px-6 py-4">
        <span
          className={`inline-flex h-6 w-6 items-center justify-center rounded-full border text-xs transition-all duration-500 ${
            matched
              ? "scale-100 border-good/50 bg-good/15 text-good opacity-100"
              : "scale-75 border-line text-faint opacity-0"
          }`}
          aria-hidden
        >
          ✓
        </span>
        <span
          className={`text-[0.8125rem] transition-colors duration-500 ${
            matched ? "text-good" : "text-faint"
          }`}
        >
          {matched ? "Match — escrow released, identity transferred, origin sealed" : "Comparing…"}
        </span>
      </div>
    </div>
  );
}

function HashPane({
  label,
  caption,
  value,
  active,
  tone,
}: {
  label: string;
  caption: string;
  value: string;
  active: boolean;
  tone: "neutral" | "good";
}) {
  return (
    <div className="p-6">
      <p className="text-[0.6875rem] uppercase tracking-[0.1em] text-faint">{label}</p>
      <p
        className={`mt-3 break-all font-mono text-[0.8125rem] leading-relaxed transition-colors duration-700 ${
          tone === "good" ? "text-good" : "text-primary"
        }`}
      >
        <ScrambleHash value={value} active={active} />
      </p>
      <p className="mt-3 text-xs text-faint">{caption}</p>
    </div>
  );
}
