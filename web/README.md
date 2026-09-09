# Succession web

Run `npm ci` and `npm run dev` in this directory. Development proxies `/api`
to `http://127.0.0.1:8000`. Build with `npm run build`; run the committed browser
regressions with `npm run test:browser` after installing Playwright Chromium.

The landing page loads independently of the console and wallet stack. Console
routes are overview, marketplace, listing detail, sell, claim, docs, and the
isolated synthetic walkthrough. Market or registry failures are shown to the
user; production never substitutes recorded listings.

`VITE_SERVICE=mock` is development-only; production builds reject it. Optional
`VITE_BASE_SEPOLIA_RPC_URL` and `VITE_REOWN_PROJECT_ID` are build-time settings.
The production Vercel configuration proxies `/api` to the Railway service at
`https://succession-production-7320.up.railway.app`; review that target and CSP
before deploying another environment.

The browser can fund escrow, cancel a listing, refund a funded sale, and reclaim
expired escrow. Only the configured evaluator may confirm delivery. Local file
export/import and certificate completion run through the CLI. A partial memory
scope still transfers the entire identity token. EOA buyers can use a local
signer. Contract-wallet buyers can download a single-use claim authorization
from the listing page; provider-specific live acceptance remains release work.

See [operations](../docs/OPERATIONS.md), [audit status](../docs/AUDIT_STATUS.md)
and [release acceptance](../docs/RELEASE_ACCEPTANCE_2026-09-09.md).
