/**
 * The palette is Part 9's, unchanged, and it is used the way Part 9 requires:
 * colour encodes transaction state and nothing else. A screen with nothing
 * pending shows no colour beyond ink on vellum.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        vellum: "#F1EDE3",
        ink: "#23272B",
        escrow: "#2E4A6B",
        closed: "#3C6E4A",
        void: "#7A3B33",
        rule: "#CFC7B5",
      },
      fontFamily: {
        // Three families, each with exactly one job. The serif carries the
        // register of a closing document; the mono is for evidence only.
        serif: ['Spectral', 'Georgia', 'serif'],
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      keyframes: {
        // The one animated moment on the whole site.
        verify: {
          "0%": { transform: "scale(0.82)", opacity: "0" },
          "55%": { transform: "scale(1.08)", opacity: "1" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
      },
      animation: { verify: "verify 420ms cubic-bezier(0.2, 0.7, 0.3, 1) both" },
    },
  },
  plugins: [],
};
