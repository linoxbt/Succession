# Succession web

The frontend is a read-only product and documentation surface with three routes:

- `/app` — hosted API and settlement-network status
- `/app/guide` — installation through the first complete memory transfer
- `/app/docs` — architecture, deployment, protocol, command and operations reference

Browser wallet connections and marketplace listing screens are deliberately
absent. Keys and local Sibyl databases remain on the role-specific hosts; the
web app only reads `/api/health` and `/api/chain`.

Its visual system mirrors the ShelbyHost frontend from
`linoxbt/shelby-deploy-magic`: Inter and JetBrains Mono, warm cream surfaces,
pink and green accents, soft radial glows, editorial hero imagery, a fixed
desktop sidebar, compact utility bar, mobile bottom navigation, stat cards,
workflow panels, copy controls, and ShelbyHost's breakpoints and spacing.

Run locally:

```bash
npm ci
npm run dev
```

Development proxies `/api` to `http://127.0.0.1:8000`. Production uses the
same-origin Vercel proxy configured in `vercel.json`. Set `VITE_API_URL` only
when the API is intentionally hosted on another origin.

Validate with `npm run build` and `npm run test:browser`.
