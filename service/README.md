# Succession service

A thin HTTP layer over the `succession` package, backing the marketplace UI.

```bash
pip install -e "../packages/succession[test,service]"
uvicorn service.app:app --reload --port 8000
```

Then `POST /api/demo/reset` to seed the seller and post the listing.

Every route delegates to the library — none of them reimplements a rule. The
preview route in particular returns exactly what `build_preview` produces, so
there is no second, more talkative code path for the UI to leak through.

## Run it with one worker

**`--workers` above 1 will not work, and the failure is not subtle.** Encrypted
envelopes and content keys live in process memory, deliberately: writing a
content key next to its ciphertext would defeat escrowing it in the first place.
So the listing state a request needs exists only in the worker that ran
`/api/demo/reset`, and a request routed elsewhere gets

```
409  no listing in this process; POST /api/demo/reset
```

which is confusing rather than wrong. Run a single worker, or scale by giving
each instance its own `SUCCESSION_WORKDIR` and pinning clients to one. Durable
envelope storage is on the roadmap; until it exists this is a real constraint,
not a tuning preference.

## Writes are gated, reads are not

| | |
|---|---|
| `SUCCESSION_API_TOKEN` **set** | Every mutating route needs `Authorization: Bearer <token>`, from anywhere including localhost. |
| **unset**, request from loopback | Allowed, so a local run needs no configuration. |
| **unset**, request from elsewhere | Refused with a 403 that names the fix. |

The default is the safe one on purpose: a service deployed without a token
cannot be written to at all, rather than being writable by everyone. Reads — the
data room, the marketplace, the chain status — stay open, because a buyer is
meant to be able to inspect a listing before paying for it.

Generate a token with `openssl rand -hex 32`.

Set `SUCCESSION_ALLOWED_ORIGINS` to the deployed frontend's origin if it calls
this service cross-origin. If it is proxied through the same origin instead (see
the `/api` block in `netlify.toml`), leave it alone — same-origin needs no CORS
grant, and that is the better arrangement.

## Routes

Reads are public; writes authenticate as the **seller of a specific listing**,
by signature, checked against what the contract records rather than against
anything stored here.

| | |
|---|---|
| `GET /api/marketplace` | Every listing: the contract for truth, the registry for counts and valuation |
| `GET /api/listing/{id}` | One listing, same join |
| `POST /api/listings` | A seller publishes metadata + ciphertext. Signature must recover to the on-chain seller |
| `GET /api/listing/{id}/envelope` | The ciphertext. Public — AES-256-GCM and inert without the key |
| `POST /api/listing/{id}/key` | The seller releases the key. Refused unless the chain says `Escrowed` |
| `GET /api/listing/{id}/key` | The buyer collects it. Escrow re-checked on the way out |
| `GET /api/chain` | Which contract is being read, if any |

`/api/walkthrough/*` is the scripted sample-agent sale. Separate module,
separate prefix, `LocalSettlement`, and every response carries
`simulated: true`. Nothing in the marketplace reads its state.

## On-chain mode

`GET /api/chain` reports `none` until `deployments/base-sepolia.json` exists.
A deployment file is the only thing that switches it, and there is deliberately
no flag that does — a flag is something that can be set wrongly, and reporting
`LocalSettlement` as a real settlement is the one dishonest thing this codebase
could do.
