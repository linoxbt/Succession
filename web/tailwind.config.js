/**
 * The design system, from Part 9 of the build spec.
 *
 * The reference point is a private M&A data room and an escrow closing
 * statement — not a consumer marketplace. This is a serious, slightly formal
 * transaction interface, closer in register to a stock transfer certificate
 * than a shopping cart. Every marketplace cliché is deliberately absent: no
 * product-grid cards, no star ratings, no cart-icon buy buttons, no confetti.
 *
 * The rule that governs every colour decision below: **colour is used only to
 * encode transaction state, never as page decoration.** A screen with nothing
 * pending shows no colour beyond ink on vellum. That is why the palette has
 * exactly three state colours and no brand accent — an accent would be
 * decoration by definition, since it would appear on screens where nothing is
 * happening.
 *
 * Three families, each with exactly one job:
 *   Spectral       headings, agent identity, and any monetary or hash figure
 *                  treated as a headline moment — the register of a closing
 *                  document.
 *   IBM Plex Sans  body copy, labels, interface chrome.
 *   IBM Plex Mono  hash strings and on-chain identifiers, and nothing else. A
 *                  hash is evidence, not a headline; it should look like a
 *                  fingerprint, distinct from every other numeral on the page.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Ground and ink
        vellum: "#F1EDE3",
        // A half-step off the page for the rare inset region. Not a card
        // surface: there are no cards.
        parchment: "#E8E3D6",
        ink: "#23272B",
        // Secondary and tertiary ink, mixed toward the page rather than grey,
        // so type never looks like it is floating on a different background.
        muted: "#5C6165",
        faint: "#8A8F93",
        rule: "#CFC8B8",
        hairline: "#DCD6C7",

        // State — the only colours on the page.
        escrow: "#2E4A6B", // funds held, awaiting confirmation
        closed: "#3C6E4A", // transfer confirmed, hash verified
        void: "#7A3B33", // mismatch, refund triggered
      },
      fontFamily: {
        serif: ['Spectral', 'Georgia', 'Times New Roman', 'serif'],
        sans: ['"IBM Plex Sans"', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        // A closing document's hierarchy: restrained, and set in the serif.
        document: ['clamp(1.75rem, 3.2vw, 2.75rem)', { lineHeight: '1.12', letterSpacing: '-0.015em' }],
        heading: ['clamp(1.25rem, 2vw, 1.6rem)', { lineHeight: '1.2', letterSpacing: '-0.01em' }],
        figure: ['clamp(1.5rem, 2.4vw, 2rem)', { lineHeight: '1.1', letterSpacing: '-0.01em' }],
      },
      maxWidth: { document: '58rem', column: '34rem' },
      keyframes: {
        // The one animated moment in the entire product, per the brief: a
        // brief, precise pulse on the hash-match checkmark when verification
        // completes. Nothing else moves.
        verify: {
          '0%': { transform: 'scale(0.82)', opacity: '0' },
          '55%': { transform: 'scale(1.06)', opacity: '1' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
      animation: {
        verify: 'verify 420ms cubic-bezier(0.22, 0.7, 0.25, 1) both',
      },
    },
  },
  plugins: [],
};
