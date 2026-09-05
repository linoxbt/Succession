/**
 * The design system.
 *
 * The product is an escrow desk for agent memory — real money, irreversible
 * transfers, hashes that either match or do not. So the art direction is
 * editorial rather than promotional: this is set like a broadsheet and a
 * closing document, not like a storefront. What carries the page is scale,
 * rhythm and negative space, and the drama comes from alternating between
 * paper and carbon at full bleed rather than from an accent colour.
 *
 * Two rules survive from the original system because they are semantic, not
 * stylistic, and the interface would be worse without them:
 *
 *   1. Colour encodes transaction state and nothing else. `escrow`, `closed`
 *      and `void` mean funds held, hash verified, and mismatch. A screen where
 *      nothing is pending shows no colour at all. A brand accent would be
 *      decoration by definition, appearing on screens where nothing happens.
 *   2. A hash is evidence, not prose. It no longer gets its own face, so it
 *      earns its distinction through tabular figures, tighter tracking and a
 *      lighter weight than the copy around it.
 *
 * One family: Inter Tight, across display, interface and figures. Hierarchy is
 * carried by size, weight and tracking rather than by a change of voice, which
 * is a harder discipline and a quieter result.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Paper and carbon, both warm. The ground carries a little brown
        // rather than sitting neutral, so the page reads as stock rather than
        // as a white screen, and the dark chapters are a deep umber rather
        // than a near-black: an inversion of the same paper, not a different
        // material.
        paper: "#EFE9DE",
        // A half-step off the page for an inset region. Not a card surface,
        // there are no cards.
        shade: "#E3DACA",
        carbon: "#1C1611",
        // One step up from carbon, for hairlines on inverted sections.
        carbonRule: "#352B22",

        ink: "#201A14",
        // Secondary and tertiary ink, mixed toward the page rather than grey,
        // so type never looks like it is floating on a different background.
        muted: "#5A5044",
        faint: "#8C8172",
        rule: "#C7BCA8",
        hairline: "#D9D0BD",

        // Inverted equivalents, for type on carbon.
        chalk: "#F1EBE0",
        chalkMuted: "#A79C8A",
        chalkFaint: "#6F6453",

        // State. The only colours in the system that mean anything, and the
        // only ones untouched by the warming above: they have to stay
        // separable from the ground, not harmonised into it.
        escrow: "#2E4A6B",
        closed: "#3C6E4A",
        void: "#8A4038",
      },
      // One family. `display`, `sans` and `mono` all resolve to it so existing
      // markup keeps working, and hierarchy is carried entirely by size, weight
      // and tracking. Figures stay aligned through `font-variant-numeric`
      // rather than through a separate monospaced face.
      fontFamily: {
        display: ['"Inter Tight"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        sans: ['"Inter Tight"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ['"Inter Tight"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      fontSize: {
        // The scale is deliberately gapped rather than continuous. Editorial
        // hierarchy comes from large intervals between few sizes; a smooth
        // ramp of nine sizes reads as a UI kit.
        colossal: ["clamp(3rem, 9vw, 7.5rem)", { lineHeight: "0.86", letterSpacing: "-0.035em" }],
        display: ["clamp(2.25rem, 5.5vw, 4.5rem)", { lineHeight: "0.92", letterSpacing: "-0.03em" }],
        title: ["clamp(1.75rem, 3.2vw, 2.5rem)", { lineHeight: "1.02", letterSpacing: "-0.025em" }],
        heading: ["clamp(1.35rem, 2.2vw, 1.85rem)", { lineHeight: "1.15", letterSpacing: "-0.015em" }],
        figure: ["clamp(1.5rem, 2.4vw, 2.25rem)", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        // The small end: labels and metadata, set wide because they are read
        // as annotation rather than prose.
        label: ["0.6875rem", { lineHeight: "1.4", letterSpacing: "0.14em" }],
        micro: ["0.75rem", { lineHeight: "1.5", letterSpacing: "0.02em" }],
        body: ["1.0625rem", { lineHeight: "1.65", letterSpacing: "-0.003em" }],
        lede: ["clamp(1.125rem, 1.6vw, 1.375rem)", { lineHeight: "1.5", letterSpacing: "-0.008em" }],
      },
      maxWidth: { reading: "42rem", measure: "34rem", wide: "96rem" },
      spacing: {
        // Chapter rhythm. Sections are separated by these, not by margins
        // chosen per component, so the vertical cadence is a system decision.
        chapter: "clamp(6rem, 14vh, 11rem)",
        beat: "clamp(3rem, 7vh, 5.5rem)",
      },
      transitionTimingFunction: {
        // One curve for interface response, one for entrances. Two is enough;
        // a library of easings makes motion feel arbitrary.
        swift: "cubic-bezier(0.22, 0.61, 0.24, 1)",
        enter: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      keyframes: {
        verify: {
          "0%": { transform: "scale(0.82)", opacity: "0" },
          "55%": { transform: "scale(1.06)", opacity: "1" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        marquee: {
          from: { transform: "translate3d(0,0,0)" },
          to: { transform: "translate3d(-50%,0,0)" },
        },
      },
      animation: {
        verify: "verify 420ms cubic-bezier(0.22, 0.7, 0.25, 1) both",
        marquee: "marquee 42s linear infinite",
      },
    },
  },
  plugins: [],
};
