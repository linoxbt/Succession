# Succession service

The service joins on-chain listing state with seller-authenticated metadata.
It persists metadata, ciphertext, replay nonces and a listing discovery index.
Content keys are authenticated, short-lived relay data held in RAM.

Run from the repository root:

```bash
pip install -e 'packages/succession[service,chain]'
uvicorn service.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Configure the RPC and deployment record and persist `SUCCESSION_WORKDIR`.
Python commands do not load `.env` automatically.

See [current operations](../docs/OPERATIONS.md) for authentication, recovery,
worker constraints and demo isolation, and [audit status](../docs/AUDIT_STATUS.md)
for release blockers. `/api/walkthrough/reset` starts a per-visitor synthetic
walkthrough; it never creates a marketplace listing.

| Route | Access and effect |
|---|---|
| GET /api/marketplace | Public chain listings and seller previews; discovery completeness included |
| GET /api/listing/{id} | Public listing detail; RPC failures are distinct from absence |
| POST /api/listings | Seller-signed metadata and ciphertext publication |
| GET /api/listing/{id}/envelope | Public encrypted package |
| POST /api/listing/{id}/key | Seller-signed key release against funded escrow |
| GET /api/listing/{id}/key/evaluator | Evaluator-signed key collection while escrow is funded; no-store |
| GET /api/listing/{id}/key | Buyer-signed key collection after evaluator settlement and finality; no-store |
| GET /api/chain | Verified connectivity, unavailable, or unconfigured |
| /api/walkthrough/* | Per-visitor isolated simulation, not live settlement |

Signatures bind method, path, raw body, deployment, expiry and a replay nonce.
`SUCCESSION_API_TOKEN` applies only to administrative routes, not to all writes.
