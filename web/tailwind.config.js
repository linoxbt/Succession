/** Exact theme structure used by the Triacta frontend. */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)", surface: "var(--surface)", surface2: "var(--surface-2)",
        ink: "var(--ink)", muted: "var(--muted)", accent: "var(--accent)",
        "accent-dim": "var(--accent-dim)", line: "var(--line)", pass: "var(--pass)",
        partial: "var(--partial)", fail: "var(--fail)", "sev-high": "var(--sev-high)",
      },
      fontFamily: { display: ["var(--font-display)"], mono: ["var(--font-mono)"] },
    },
  },
  plugins: [],
};
