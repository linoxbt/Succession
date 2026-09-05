/**
 * The visual compositions.
 *
 * Original vector artwork rather than photography, for three reasons that
 * happen to align. Stock imagery of archives and handshakes would say nothing
 * true about this product and would read as exactly the generic filler the
 * design is trying to avoid. Vector stays sharp at the full-bleed sizes used
 * here and costs a few kilobytes instead of a few hundred. And it needs no
 * external origin, so the deployed Content-Security-Policy stays closed.
 *
 * Each composition is about something the product actually does:
 *
 *   `MemoryField`  accumulation. A dense lattice of counterparties and the
 *                  edges between them, thinning toward the margins, which is
 *                  what a memory store looks like as it grows.
 *   `Lineage`      inheritance. Strata laid down over time, with one band
 *                  carried across the break into the next owner.
 *   `HashPlate`    evidence. A commitment rendered as a fixed field of marks,
 *                  the visual equivalent of something that either matches or
 *                  does not.
 *
 * All three are deterministic: a seeded generator, not `Math.random`, so the
 * artwork is identical on every render and every machine. Artwork that
 * reshuffles on a re-render is decoration, not design.
 */

/** A small deterministic PRNG. Same seed, same composition, forever. */
function seeded(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 0xffffffff;
  };
}

/**
 * Accumulation. Nodes clustered toward a centre of mass with edges between
 * near neighbours, so the eye reads relationship rather than scatter.
 */
export function MemoryField({ className = "" }: { className?: string }) {
  const rand = seeded(0x5eed);
  const W = 1600;
  const H = 900;
  const nodes: { x: number; y: number; r: number }[] = [];

  for (let i = 0; i < 190; i += 1) {
    // Two samples averaged pulls points toward the middle, which gives the
    // field a dense core and a thinning edge instead of an even dusting.
    const x = ((rand() + rand()) / 2) * W;
    const y = ((rand() + rand()) / 2) * H;
    nodes.push({ x, y, r: 1 + rand() * 2.4 });
  }

  // Edges carry their endpoints rather than indices into the array: the render
  // below then needs no lookup, and no lookup means nothing to be undefined.
  const edges: { x1: number; y1: number; x2: number; y2: number }[] = [];
  for (let i = 0; i < nodes.length; i += 1) {
    const a = nodes[i];
    if (!a) continue;
    for (let j = i + 1; j < nodes.length; j += 1) {
      const b = nodes[j];
      if (!b) continue;
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      if (dx * dx + dy * dy < 6200) edges.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y });
    }
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className={className}
      role="img"
      aria-label="A field of connected points, dense at the centre and thinning toward the edges"
      preserveAspectRatio="xMidYMid slice"
    >
      <g stroke="currentColor" strokeWidth="0.6" opacity="0.28">
        {edges.map((e, i) => (
          <line key={i} x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2} />
        ))}
      </g>
      <g fill="currentColor">
        {nodes.map((n, i) => (
          <circle key={i} cx={n.x} cy={n.y} r={n.r} opacity={0.35 + (n.r / 3.4) * 0.5} />
        ))}
      </g>
    </svg>
  );
}

/**
 * Inheritance. Horizontal strata of varying weight, broken once, with a single
 * band continuing across the break: the same memory, a different owner.
 */
export function Lineage({ className = "" }: { className?: string }) {
  const rand = seeded(0xa11ce);
  const W = 1600;
  const H = 900;
  const bands: { y: number; h: number; o: number }[] = [];
  let y = 40;
  while (y < H - 40) {
    const h = 2 + rand() * 22;
    bands.push({ y, h, o: 0.1 + rand() * 0.5 });
    y += h + 4 + rand() * 16;
  }
  const breakX = W * 0.58;
  const carried = Math.floor(bands.length * 0.42);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className={className}
      role="img"
      aria-label="Horizontal strata interrupted by a vertical break, with one band continuing across it"
      preserveAspectRatio="xMidYMid slice"
    >
      <g fill="currentColor">
        {bands.map((b, i) => (
          <g key={i}>
            <rect x={0} y={b.y} width={breakX - 14} height={b.h} opacity={b.o} />
            {/* Past the break the strata resume, lighter: a new owner, starting
                from what they were given rather than from nothing. */}
            <rect
              x={breakX + 14}
              y={b.y}
              width={W - breakX - 14}
              height={b.h}
              opacity={i === carried ? b.o : b.o * 0.32}
            />
          </g>
        ))}
      </g>
      <line x1={breakX} y1={0} x2={breakX} y2={H} stroke="currentColor" strokeWidth="1" opacity="0.5" />
    </svg>
  );
}

/**
 * Evidence. A fixed grid of marks derived from a seed, which is what a
 * commitment is: not decorative, not negotiable, and either identical to the
 * one you were given or not.
 */
export function HashPlate({ className = "" }: { className?: string }) {
  const rand = seeded(0x9f3a1c);
  const cols = 48;
  const rows = 16;
  const cell = 26;

  return (
    <svg
      viewBox={`0 0 ${cols * cell} ${rows * cell}`}
      className={className}
      role="img"
      aria-label="A dense grid of marks, forming a fixed pattern"
      preserveAspectRatio="xMidYMid slice"
    >
      <g fill="currentColor">
        {Array.from({ length: rows }).map((_, r) =>
          Array.from({ length: cols }).map((__, c) => {
            const v = rand();
            if (v < 0.42) return null;
            const size = v > 0.86 ? cell * 0.5 : cell * 0.2;
            return (
              <rect
                key={`${r}-${c}`}
                x={c * cell + (cell - size) / 2}
                y={r * cell + (cell - size) / 2}
                width={size}
                height={size}
                opacity={0.2 + v * 0.6}
              />
            );
          }),
        )}
      </g>
    </svg>
  );
}
