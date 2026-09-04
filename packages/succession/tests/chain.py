"""A local EVM for the contract tests.

Runs the *compiled* ``ListingContract`` bytecode in py-evm through web3's
EthereumTesterProvider, so these tests exercise the real Solidity — the same
artifact ``compile.js`` produces — rather than a Python re-description of it.
The suite skips itself if the artifacts have not been built.
"""

from __future__ import annotations

import json
import subprocess
from contextlib import contextmanager
from pathlib import Path

import pytest

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
ARTIFACTS = CONTRACTS / "out" / "artifacts.json"


def _sources_newer_than_artifacts() -> bool:
    """True if any .sol has been touched since the artifacts were compiled.

    Missing artifacts are obvious; *stale* ones are not. They produce failures
    that read as contract bugs — a call reverting for a rule the source no
    longer contains — and the only clue is that the source was edited, or a
    branch switched, since the last build. Cheaper to detect than to debug.
    """
    if not ARTIFACTS.exists():
        return True
    built = ARTIFACTS.stat().st_mtime
    # Only this project's own sources: `contracts/lib` holds forge-std, whose
    # thousands of files are not what compile.js builds and whose checkout
    # mtimes would trigger a rebuild on every run.
    return any(
        sol.stat().st_mtime > built
        for directory in ("src", "test")
        for sol in (CONTRACTS / directory).rglob("*.sol")
    )


def load_artifacts() -> dict:
    if _sources_newer_than_artifacts():
        # One attempt to build, so a fresh clone that has run `npm install` — or
        # a checkout that moved the contracts under a stale build — does not
        # need a separate manual step.
        try:
            subprocess.run(
                ["node", "compile.js"],
                cwd=CONTRACTS,
                check=True,
                capture_output=True,
                timeout=300,
            )
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"contract artifacts unavailable ({exc}); run `npm run build` in contracts/")
    return json.loads(ARTIFACTS.read_text())


def deploy(w3, artifacts: dict, name: str, *args, sender: str):
    artifact = artifacts[name]
    factory = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
    tx = factory.constructor(*args).transact({"from": sender})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    return w3.eth.contract(address=receipt["contractAddress"], abi=artifact["abi"])


def error_selectors(abi: list) -> dict[str, str]:
    """Map each custom error's 4-byte selector to its name."""
    from eth_utils import keccak

    out = {}
    for item in abi:
        if item.get("type") != "error":
            continue
        signature = f"{item['name']}({','.join(i['type'] for i in item['inputs'])})"
        out[keccak(text=signature)[:4].hex()] = item["name"]
    return out


@contextmanager
def reverts_with(contract, name: str):
    """Assert the block reverts with a specific custom error.

    eth-tester surfaces the raw revert payload rather than web3's typed
    ``ContractCustomError``, so the selector is decoded here. Matching on the
    error *name* rather than on "it reverted" is the point: a test that only
    checks for a revert passes when the contract rejects the call for entirely
    the wrong reason.
    """
    from eth_tester.exceptions import TransactionFailed

    selectors = error_selectors(contract.abi)
    with pytest.raises(TransactionFailed) as exc:
        yield
    data = _revert_payload(exc.value)
    selector = data[:4].hex()
    actual = selectors.get(selector, f"unknown selector 0x{selector}")
    assert actual == name, f"expected {name}, got {actual}"


def _revert_payload(exc: BaseException) -> bytes:
    """Pull the ABI-encoded revert data out of an eth-tester failure.

    eth-tester wraps it inconsistently: sometimes the raw ``bytes``, sometimes a
    message string with the bytes *repr* spliced in ("execution reverted:
    b\'Q\\xbd...\'"). Re-encoding that string directly yields the characters of
    the repr rather than the bytes it describes, which silently produces a
    wrong selector and a test that fails for the wrong reason.
    """
    import ast
    import re

    for arg in exc.args:
        if isinstance(arg, (bytes, bytearray)):
            return bytes(arg)
        if isinstance(arg, str):
            match = re.search(r"b['\"](?:[^'\"\\]|\\.)*['\"]", arg)
            if match:
                try:
                    value = ast.literal_eval(match.group(0))
                except (ValueError, SyntaxError):
                    continue
                if isinstance(value, bytes):
                    return value
    return b""
