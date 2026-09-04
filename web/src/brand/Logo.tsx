/**
 * The Succession mark.
 *
 * The idea is the product in one shape: a single S-spine drawn as **two
 * strokes with a visible seam**. The upper half is the origin agent, the lower
 * half the successor, and the gap between them is the transfer. One continuous
 * letterform, visibly handed over — continuity that changed hands, which is
 * the whole thesis.
 *
 * Both halves are the same path with `pathLength="100"` normalised, so the
 * split is expressed as a dash offset rather than as two hand-drawn curves that
 * would drift apart at different sizes. That also makes the handover
 * animatable: the successor half draws itself in, once, on first paint.
 *
 * It survives 16px because it is one stroke weight, one shape, and no interior
 * detail — the seam stays legible when everything else has collapsed.
 */

/** The S-spine. Two mirrored bowls, drawn as cubics for an even weight. */
const SPINE = "M23.5 10.5C23.5 5.5 8.5 5.5 8.5 12.5C8.5 19.5 23.5 12.5 23.5 19.5C23.5 26.5 8.5 26.5 8.5 21.5";

/** Where the origin half ends and the successor half begins, out of 100. */
const SEAM_START = 46;
const SEAM_END = 54;

export function Mark({
  size = 32,
  animate = false,
  className = "",
}: {
  size?: number;
  animate?: boolean;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      role="img"
      aria-label="Succession"
      className={className}
    >
      {/* Origin: solid, present from the first frame. */}
      <path
        d={SPINE}
        pathLength={100}
        stroke="currentColor"
        strokeWidth={3}
        strokeLinecap="round"
        strokeDasharray={`${SEAM_START} 100`}
      />
      {/* Successor: the half that arrives. */}
      <path
        d={SPINE}
        pathLength={100}
        stroke="var(--mark-accent, #1D9BF0)"
        strokeWidth={3}
        strokeLinecap="round"
        strokeDasharray={`${100 - SEAM_END} 100`}
        strokeDashoffset={-SEAM_END}
        className={animate ? "mark-successor" : undefined}
      />
    </svg>
  );
}

/** Mark plus name, for the header and the console rail. */
export function Wordmark({
  size = 22,
  animate = false,
  className = "",
}: {
  size?: number;
  animate?: boolean;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <Mark size={size} animate={animate} />
      <span
        className="font-semibold tracking-[-0.02em]"
        style={{ fontSize: size * 0.72 }}
      >
        Succession
      </span>
    </span>
  );
}

/**
 * The contained variant: the mark inside a seal.
 *
 * Used where the logo sits on an unpredictable ground — a favicon, an avatar,
 * an OG card — and needs to carry its own background rather than inherit one.
 */
export function Seal({ size = 32, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      role="img"
      aria-label="Succession"
      className={className}
    >
      <rect width="32" height="32" rx="8" fill="#0A0A0B" />
      <rect x="0.5" y="0.5" width="31" height="31" rx="7.5" stroke="#22262B" />
      <g transform="translate(3.2 3.2) scale(0.8)">
        <path
          d={SPINE}
          pathLength={100}
          stroke="#E7E9EA"
          strokeWidth={3.4}
          strokeLinecap="round"
          strokeDasharray={`${SEAM_START} 100`}
        />
        <path
          d={SPINE}
          pathLength={100}
          stroke="#1D9BF0"
          strokeWidth={3.4}
          strokeLinecap="round"
          strokeDasharray={`${100 - SEAM_END} 100`}
          strokeDashoffset={-SEAM_END}
        />
      </g>
    </svg>
  );
}
