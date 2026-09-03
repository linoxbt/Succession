"""Deterministic demo identities.

These keys are hardcoded, published in this repository, and therefore
**worthless**. They exist so the test suite and the local demo can produce the
same addresses and the same signatures on every machine, which is what makes a
committed root reproducible across the two-machine rehearsal.

Never fund them. Never use them on any network, testnet included beyond a
throwaway faucet balance. A real seller signs with the key that holds the
agent's ERC-8004 identity, supplied through the environment — see
``succession.cli``.
"""

from __future__ import annotations

from eth_account import Account

__all__ = ["SELLER", "BUYER", "DemoIdentity"]


class DemoIdentity:
    def __init__(self, label: str, private_key: str, agent_id: str) -> None:
        self.label = label
        self.private_key = private_key
        self.address = Account.from_key(private_key).address
        self.agent_id = agent_id

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<DemoIdentity {self.label} {self.address} {self.agent_id}>"


SELLER = DemoIdentity("seller", "0x" + "11" * 32, "erc8004:84532:0417")
BUYER = DemoIdentity("buyer", "0x" + "22" * 32, "erc8004:84532:1183")
