# Current handoff — 9 September 2026

Work in `/root/succession`. The user requested fixes for every audit finding,
regression checks, and an honest final production-readiness review. Preserve
existing staged changes. The remediated release is deployed and live acceptance
evidence is recorded in [RELEASE_ACCEPTANCE_2026-09-09.md](RELEASE_ACCEPTANCE_2026-09-09.md).

Read [AUDIT_STATUS.md](AUDIT_STATUS.md) for the finding ledger,
[OPERATIONS.md](OPERATIONS.md) for supported flows and recovery, and
[TECHNICAL_REVIEW_2026-09-07.md](TECHNICAL_REVIEW_2026-09-07.md) for the historical
baseline. This replaces the obsolete handoff claiming all code was complete.

## Remaining release work

- Establish real Virtuals ACP job acceptance. ERC-8004 registration/transfer and
  the dedicated evaluator are accepted live, but external ACP jobs are not.
- Design an operator-approved ERC-1271 authorization tool if contract-wallet
  support is required. The EOA CLI path and local ERC-1271 regression are complete.
- Establish operational finality, backups, monitoring and sustained-load limits
  before accepting production assets. See [ROADMAP.md](ROADMAP.md).

## Local verification

From the repository root:

```bash
.venv/bin/python -m pytest packages/succession/tests
/root/.foundry/bin/forge test --root contracts
.venv/bin/python scripts/generate_reference.py
```

In `web/`, run `npm run build` and `npm run test:browser`. Browser regressions
cover the read-only dashboard, guide, terminal runbook and route recovery; the
EOA CLI path has separate live acceptance evidence.
CI also checks the generated ABI, packaged wheel and clean Docker image.

Keep the audit status current as checks complete. Historical testnet transactions
and simulated walkthrough settlement must remain clearly identified.
