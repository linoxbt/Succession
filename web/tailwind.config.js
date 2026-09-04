/**
 * Two surfaces, one system.
 *
 * The dashboard is built to read like an internal operations console at a
 * company that moves real money — X's admin surface is the reference: near-black
 * ground, hairline dividers, dense tables, one accent used only for state.
 * The landing page is the same palette at a different scale: enormous type,
 * almost no words, and a lot of air.
 *
 * Colour is never decoration here. It marks transaction state and nothing else.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Ground
        base: "#000000",
        panel: "#0E1013",
        raised: "#16181C",
        line: "#22262B",
        hairline: "#1A1D21",
        // Type
        primary: "#E7E9EA",
        secondary: "#8B949E",
        faint: "#5A6169",
        // State — the only colours on the page
        accent: "#1D9BF0",
        good: "#00BA7C",
        bad: "#F4212E",
        warn: "#E3B341",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        // Landing display sizes: tight tracking, tight leading.
        display: ['clamp(2.75rem, 7.5vw, 6.5rem)', { lineHeight: '0.94', letterSpacing: '-0.04em' }],
        headline: ['clamp(1.9rem, 4vw, 3.25rem)', { lineHeight: '1.02', letterSpacing: '-0.03em' }],
        lede: ['clamp(1.05rem, 1.6vw, 1.35rem)', { lineHeight: '1.5', letterSpacing: '-0.01em' }],
      },
      maxWidth: { content: '1180px' },
      keyframes: {
        rise: { from: { opacity: '0', transform: 'translateY(10px)' }, to: { opacity: '1', transform: 'none' } },
      },
      animation: { rise: 'rise 520ms cubic-bezier(0.22,0.7,0.3,1) both' },
    },
  },
  plugins: [],
};
