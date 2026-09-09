# Succession web

The frontend is a read-only operator surface with three routes:

- `/app` — live API, chain, contract, evaluator, and finality status
- `/app/guide` — the seller, evaluator, and buyer CLI workflow
- `/app/terminal` — the recording checklist and exact demo commands

Browser wallet connections and marketplace listing screens are deliberately
absent. Keys and local Sibyl databases remain on the role-specific hosts; the
web app only reads `/api/health` and `/api/chain`.

Its visual system mirrors the Triacta frontend: Space Grotesk and Space Mono,
the same charcoal/cream themes and bronze accent, status ticker, landing-page
grid, collapsible dashboard sidebar, stat cards, evidence table, guide steps,
copy controls, breakpoints, spacing and type sizes. The font files are bundled
locally in `public/fonts`.

Run locally:

```bash
npm ci
npm run dev
```

Development proxies `/api` to `http://127.0.0.1:8000`. Production uses the
same-origin Vercel proxy configured in `vercel.json`. Set `VITE_API_URL` only
when the API is intentionally hosted on another origin.

Validate with `npm run build` and `npm run test:browser`.
