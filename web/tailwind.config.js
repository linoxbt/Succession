/** ShelbyHost's visual tokens, expressed through the existing Tailwind build. */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)", foreground: "var(--foreground)",
        card: "var(--card)", "card-foreground": "var(--card-foreground)",
        primary: "var(--primary)", "primary-hover": "var(--primary-hover)", "primary-foreground": "var(--primary-foreground)",
        secondary: "var(--secondary)", "secondary-foreground": "var(--secondary-foreground)",
        muted: "var(--muted)", "muted-foreground": "var(--muted-foreground)",
        accent: "var(--accent)", success: "var(--success)", warning: "var(--warning)",
        destructive: "var(--destructive)", border: "var(--border)", input: "var(--input)", ring: "var(--ring)",
        sidebar: "var(--sidebar)", "sidebar-foreground": "var(--sidebar-foreground)",
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"], mono: ["JetBrains Mono", "ui-monospace", "monospace"] },
      boxShadow: { glow: "var(--shadow-glow)", panel: "var(--shadow-panel)" },
    },
  },
  plugins: [],
};
