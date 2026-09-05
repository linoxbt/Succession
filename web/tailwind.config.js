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
 *   1. **Colour encodes transaction state and nothing else.** `escrow`,
 *      `closed` and `void` mean funds held, hash verified, and mismatch. A
 *      screen where nothing is pending shows no colour at all. A brand accent
 *      would be decoration by definition — it would appear on screens where
 *      nothing is happening.
 *   2. **A hash is evidence, not a headline.** It is always mono, always
 *      distinguishable from every other numeral on the page.
 *
 * Three families:
 *   Instrument Serif  display. High contrast, and it holds up at the sizes
 *                     this design actually uses — a hero line is set in the
 *                     hundreds of pixels, where most serifs fall apart.
 *   Inter Tight       everything else: labels, navigation, metadata, body.
 *                     Tight enough to sit as a caption under display type
 *                     without competing with it.
 *   IBM Plex Mono     hashes and on-chain identifiers, and nothing else.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Paper and carbon: the two grounds the page alternates between.
        paper: "#F4F1EA",
        // A half-step off the page for an inset region. Not a card surface —
        // there are no cards.
        shade: "#E9E4D8",
        carbon: "#16130F",
        // One step up from carbon, for hairlines on inverted sections.
        carbonRule: "#2C2721",

        ink: "#1A1815",
        // Secondary and tertiary ink, mixed toward the page rather than grey,
        // so type never looks like it is floating on a different background.
        muted: "#57534B",
        faint: "#8B857A",
        rule: "#CDC6B6",
        hairline: "#DED8C9",

        // Inverted equivalents, for type on carbon.
        chalk: "#F4F1EA",
        chalkMuted: "#A8A196",
        chalkFaint: "#6E675C",

        // State — the only colours in the system.
        escrow: "#2E4A6B",
        closed: "#3C6E4A",
        void: "#8A4038",
      },
      fontFamily: {
        display: ['"Instrument Serif"', "Georgia", "Times New Roman", "serif"],
        sans: ['"Inter Tight"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        // The scale is deliberately gapped rather than continuous. Editorial
        // hierarchy comes from large intervals between few sizes; a smooth
        // ramp of nine sizes reads as a UI kit.
        colossal: ["clamp(3.5rem, 13vw, 13rem)", { lineHeight: "0.86", letterSpacing: "-0.035em" }],
        display: ["clamp(2.75rem, 8vw, 7rem)", { lineHeight: "0.92", letterSpacing: "-0.03em" }],
        title: ["clamp(2rem, 4.5vw, 3.5rem)", { lineHeight: "1.02", letterSpacing: "-0.025em" }],
        heading: ["clamp(1.35rem, 2.2vw, 1.85rem)", { lineHeight: "1.15", letterSpacing: "-0.015em" }],
        figure: ["clamp(1.75rem, 3.2vw, 2.75rem)", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
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
