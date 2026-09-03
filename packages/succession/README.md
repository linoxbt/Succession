# `succession` — the SMP pipeline

The Python core of Succession: export a tenant's memory into a Succession
Memory Package, hash and sign it, import it into a fresh tenant, and prove the
result matches what was committed on-chain.

See the [repository README](../../README.md) for the full picture. Quick start:

```bash
pip install -e ".[dev]"
pytest
```
