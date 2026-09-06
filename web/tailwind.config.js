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
      // Every colour resolves through a CSS variable rather than a literal, so
      // one subtree of the document can carry a different palette without a
      // second set of class names. `:root` in index.css holds the values that
      // used to sit here, so the marketing pages render exactly as before; the
      // console overrides the same names under `[data-surface="app"]`.
      //
      // The channel-triplet form is not decoration. Around fifteen call sites
      // use alpha modifiers (`bg-paper/95`, `bg-ink/25`, `border-escrow/40`),
      // and a plain `var(--x)` holding a hex would silently drop the alpha and
      // leave those surfaces opaque.
      colors: {
        // Paper and carbon. On the marketing pages both are warm: the ground
        // carries a little brown so it reads as stock rather than as a white
        // screen. In the console the same two names carry a dark institutional
        // ground and its elevated panel.
        paper: "rgb(var(--c-paper) / <alpha-value>)",
        // A half-step off the page for an inset region.
        shade: "rgb(var(--c-shade) / <alpha-value>)",
        carbon: "rgb(var(--c-carbon) / <alpha-value>)",
        // One step up from carbon, for hairlines on inverted sections.
        carbonRule: "rgb(var(--c-carbon-rule) / <alpha-value>)",

        ink: "rgb(var(--c-ink) / <alpha-value>)",
        // Secondary and tertiary ink, mixed toward the ground rather than grey,
        // so type never looks like it is floating on a different background.
        muted: "rgb(var(--c-muted) / <alpha-value>)",
        faint: "rgb(var(--c-faint) / <alpha-value>)",
        rule: "rgb(var(--c-rule) / <alpha-value>)",
        hairline: "rgb(var(--c-hairline) / <alpha-value>)",

        // Inverted equivalents, for type on carbon.
        chalk: "rgb(var(--c-chalk) / <alpha-value>)",
        chalkMuted: "rgb(var(--c-chalk-muted) / <alpha-value>)",
        chalkFaint: "rgb(var(--c-chalk-faint) / <alpha-value>)",

        // State. These mean something: funds held, hash verified, mismatch.
        // The console re-tints them for legibility on a dark ground; it does
        // not repurpose them, and nothing else in the system is allowed to
        // borrow them.
        escrow: "rgb(var(--c-escrow) / <alpha-value>)",
        closed: "rgb(var(--c-closed) / <alpha-value>)",
        void: "rgb(var(--c-void) / <alpha-value>)",

        // Two names that exist so the console can differ without the marketing
        // pages moving. `signal` is the console's accent, and resolves to the
        // escrow blue at `:root` so that a stray use outside the app stays on
        // system rather than introducing a colour. `press` replaces a literal
        // `bg-black` in the primary button, and is black at `:root`, so the
        // marketing pages keep the button they had.
        signal: "rgb(var(--c-signal) / <alpha-value>)",
        press: "rgb(var(--c-press) / <alpha-value>)",
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
