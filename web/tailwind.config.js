/**
 * The design system.
 *
 * The product is an escrow desk for agent memory: real money, irreversible
 * transfers, hashes that either match or do not. The art direction is a
 * payments console, which is what it behaves like. White ground, bounded cards,
 * one blue that means "act", and figures set to line up column to column.
 *
 * This replaced two earlier systems that both existed at once, warm editorial
 * paper on the marketing pages and dark charcoal in the console, each asked for
 * separately and each coherent alone. Read one after the other they were two
 * products, so there is now one.
 *
 * Two rules survive from the original system because they are semantic rather
 * than stylistic, and the interface would be worse without them:
 *
 *   1. `escrow`, `closed` and `void` mean funds held, hash verified, and
 *      mismatch, and nothing else may borrow them. A screen where nothing is
 *      pending shows none of them, which is what keeps them legible when
 *      something is. `signal` is the one addition: an accent for interactive
 *      affordance, which is a different job from encoding state.
 *   2. A hash is evidence, not prose. There is no monospaced face, so it earns
 *      its distinction through tabular figures, tighter tracking and a lighter
 *      weight than the copy around it. See `.evidence-type` in index.css.
 *
 * One family: Plus Jakarta Sans, across display, interface and figures.
 * Hierarchy comes from size, weight and tracking rather than from a change of
 * voice, which is a harder discipline and a quieter result.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Every colour resolves through a CSS variable rather than a literal.
      // There is one palette now, in `:root`, but the indirection is kept: it
      // costs nothing and puts a second palette one block away rather than one
      // refactor away.
      //
      // The channel-triplet form is not decoration. Around fifteen call sites
      // use alpha modifiers (`bg-paper/95`, `bg-ink/25`, `border-escrow/40`),
      // and a plain `var(--x)` holding a hex would silently drop the alpha and
      // leave those surfaces opaque.
      colors: {
        // The ground, and the half step off it that a card sits on.
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
        // Nothing else in the system is allowed to borrow them.
        escrow: "rgb(var(--c-escrow) / <alpha-value>)",
        closed: "rgb(var(--c-closed) / <alpha-value>)",
        void: "rgb(var(--c-void) / <alpha-value>)",

        // `signal` is the interactive accent: what to press, what is selected,
        // what a tab is on. Deliberately deep enough to carry text at 4.5,
        // unlike the brighter cyan the reference uses for large fills, which
        // fails as a label colour. `press` is its active state.
        signal: "rgb(var(--c-signal) / <alpha-value>)",
        press: "rgb(var(--c-press) / <alpha-value>)",
      },
      // One family still, as before. Plus Jakarta Sans is the geometric,
      // friendly grotesque the reference's own face belongs to, where Inter
      // Tight was a neutral editorial one. `mono` resolves here too: there is no
      // monospaced face, and hashes are set apart by tabular figures and
      // tracking instead. See `.evidence-type` in index.css.
      fontFamily: {
        display: ['"Plus Jakarta Sans"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        sans: ['"Plus Jakarta Sans"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ['"Plus Jakarta Sans"', "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      fontSize: {
        // Brought down from a broadsheet scale to a product one. The old
        // ceilings were built for a page read at a distance; a console is read
        // at arm's length and wants more rows and less drama. The intervals
        // stay gapped so hierarchy is still obvious without shouting.
        colossal: ["clamp(2.5rem, 6.5vw, 4.75rem)", { lineHeight: "1.02", letterSpacing: "-0.03em" }],
        display: ["clamp(1.875rem, 3.6vw, 3rem)", { lineHeight: "1.1", letterSpacing: "-0.025em" }],
        title: ["clamp(1.375rem, 2.2vw, 1.75rem)", { lineHeight: "1.25", letterSpacing: "-0.018em" }],
        heading: ["clamp(1.125rem, 1.5vw, 1.3125rem)", { lineHeight: "1.35", letterSpacing: "-0.01em" }],
        figure: ["clamp(1.5rem, 2vw, 2rem)", { lineHeight: "1.15", letterSpacing: "-0.02em" }],
        // The small end: labels and metadata, set wide because they are read
        // as annotation rather than prose.
        label: ["0.6875rem", { lineHeight: "1.45", letterSpacing: "0.08em" }],
        micro: ["0.75rem", { lineHeight: "1.5", letterSpacing: "0.02em" }],
        body: ["1rem", { lineHeight: "1.65", letterSpacing: "0" }],
        lede: ["clamp(1.0625rem, 1.3vw, 1.25rem)", { lineHeight: "1.6", letterSpacing: "-0.005em" }],
      },
      borderRadius: {
        // Named for what they wrap rather than by size, so a control and a card
        // cannot drift apart as the scale is tuned.
        control: "0.5rem",
        card: "0.75rem",
        panel: "1rem",
        pill: "999px",
      },
      boxShadow: {
        // One elevation, used sparingly. A card that lifts off the page is a
        // card the eye reads first, so more than one level would be a ranking
        // nobody chose.
        card: "0 1px 2px rgb(1 27 51 / 0.04), 0 4px 16px rgb(1 27 51 / 0.06)",
        lift: "0 2px 4px rgb(1 27 51 / 0.05), 0 12px 32px rgb(1 27 51 / 0.10)",
      },
      maxWidth: { reading: "42rem", measure: "34rem", wide: "96rem" },
      spacing: {
        // Chapter rhythm. Sections are separated by these, not by margins
        // chosen per component, so the vertical cadence is a system decision.
        chapter: "clamp(4rem, 9vh, 6.5rem)",
        beat: "clamp(2.25rem, 5vh, 3.5rem)",
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
