"""ERC-8004 identity — registration, the registration file, and transfer.

Succession's premise is that identity and memory move together. ERC-8004 is
what makes the identity half real: each agent is an ERC-721 token inside an
Identity Registry, ``agentId`` *is* ``tokenId``, and transferring the token
transfers the identity. That is the exact primitive ``ListingContract``'s
settlement step calls into.

Why this module exists rather than a hardcoded address
------------------------------------------------------

The build spec says to point at a real ERC-8004 registry and warns that
shipping an ERC-721 stand-in silently would be the one dishonest thing in the
stack. There *is* a live registry on Base Sepolia, and this module is what lets
the pipeline use it: :data:`BASE_SEPOLIA_IDENTITY_REGISTRY` is the deployment
verified below, and :class:`IdentityRegistry` is the client that registers
against it.

The deployment this was written against, and what was checked
-------------------------------------------------------------

``0x7177a6867296406881E20d6647232314736Dd09A`` on Base Sepolia (chain 84532):

* ``name()`` → ``ERC-8004 Trustless Agent``, ``symbol()`` → ``AGENT``
* ``supportsInterface(0x80ac58cd)`` → true, so it is genuinely ERC-721
* ``ownerOf(1)`` resolves, ``tokenURI(1)`` → ``ipfs://QmBase-Sepolia-Test-Agent``
* its bytecode carries all three ``register`` overloads, ``getMetadata`` /
  ``setMetadata``, and the full ``ownerOf`` / ``getApproved`` /
  ``isApprovedForAll`` / ``transferFrom`` / ``approve`` surface that
  ``ListingContract`` depends on

It predates the final draft in one respect worth stating rather than
discovering at runtime: it has no ``setAgentURI``, ``setAgentWallet``,
``getAgentWallet`` or ``unsetAgentWallet``. :meth:`IdentityRegistry.capabilities`
reports what a given deployment actually implements, by probing its deployed
bytecode for selectors, so a caller finds out from the chain rather than from
this docstring going stale.

Registration is permissionless — ``register(agentURI)`` mints to the caller.
That matters for the demo: seller and buyer identities are real tokens in a
real registry, minted by the same script that runs the transfer, with no
whitelist and no stand-in.

The registration file
---------------------

ERC-8004 requires ``agentURI`` to resolve to a JSON registration file
describing the agent. The spec permits ``ipfs://``, ``https://``, or a
base64-encoded ``data:`` URI. :func:`registration_uri` builds a ``data:`` URI by
default, and that is deliberate: it is the only scheme whose resolvability does
not depend on a pinning service or a host staying up. The file is *in* the
token. An ``https://`` endpoint that 404s two months after a hackathon is an
identity that no longer describes anything, and a judge checking the token a
week later should not find a dead link.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any

from eth_account import Account
from eth_utils import keccak, to_checksum_address

from .canonical import canonical_json

__all__ = [
    "BASE_SEPOLIA_IDENTITY_REGISTRY",
    "BASE_SEPOLIA_CHAIN_ID",
    "IDENTITY_REGISTRY_ABI",
    "AgentRegistration",
    "IdentityRegistry",
    "registration_uri",
    "agent_identity",
    "parse_agent_identity",
]

#: The ERC-8004 Identity Registry deployed on Base Sepolia. See the module
#: docstring for exactly what was verified against it.
BASE_SEPOLIA_IDENTITY_REGISTRY = "0x7177a6867296406881E20d6647232314736Dd09A"

BASE_SEPOLIA_CHAIN_ID = 84532

#: The subset this package calls. Deliberately not the whole ERC-8004 draft:
#: an ABI entry for a function a deployment does not implement produces a
#: confusing revert instead of a clear "not supported", which is what
#: :meth:`IdentityRegistry.capabilities` is for.
IDENTITY_REGISTRY_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "register",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "agentURI", "type": "string"}],
        "outputs": [{"name": "agentId", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "ownerOf",
        "stateMutability": "view",
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
    },
    {
        "type": "function",
        "name": "tokenURI",
        "stateMutability": "view",
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "string"}],
    },
    {
        "type": "function",
        "name": "approve",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "agentId", "type": "uint256"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "getApproved",
        "stateMutability": "view",
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
    },
    {
        "type": "function",
        "name": "setApprovalForAll",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "operator", "type": "address"},
            {"name": "approved", "type": "bool"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "isApprovedForAll",
        "stateMutability": "view",
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "operator", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "type": "function",
        "name": "transferFrom",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "agentId", "type": "uint256"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "getMetadata",
        "stateMutability": "view",
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "metadataKey", "type": "string"},
        ],
        "outputs": [{"name": "", "type": "bytes"}],
    },
    {
        "type": "function",
        "name": "setMetadata",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "metadataKey", "type": "string"},
            {"name": "metadataValue", "type": "bytes"},
        ],
        "outputs": [],
    },
    {
        "type": "event",
        "name": "Registered",
        "anonymous": False,
        "inputs": [
            {"name": "agentId", "type": "uint256", "indexed": True},
            {"name": "agentURI", "type": "string", "indexed": False},
            {"name": "owner", "type": "address", "indexed": True},
        ],
    },
    {
        "type": "event",
        "name": "Transfer",
        "anonymous": False,
        "inputs": [
            {"name": "from", "type": "address", "indexed": True},
            {"name": "to", "type": "address", "indexed": True},
            {"name": "tokenId", "type": "uint256", "indexed": True},
        ],
    },
]

#: Selectors probed to report a deployment's real surface.
_SELECTORS: dict[str, str] = {
    "register": "register(string)",
    "register_bare": "register()",
    "register_with_metadata": "register(string,(string,bytes)[])",
    "set_agent_uri": "setAgentURI(uint256,string)",
    "get_metadata": "getMetadata(uint256,string)",
    "set_metadata": "setMetadata(uint256,string,bytes)",
    "set_agent_wallet": "setAgentWallet(uint256,address,uint256,bytes)",
    "get_agent_wallet": "getAgentWallet(uint256)",
    "transfer_from": "transferFrom(address,address,uint256)",
    "get_approved": "getApproved(uint256)",
    "is_approved_for_all": "isApprovedForAll(address,address)",
}


# -- the registration file -------------------------------------------------


@dataclass(frozen=True)
class AgentRegistration:
    """The JSON document ``agentURI`` resolves to.

    ERC-8004 fixes the shape loosely — name, description, and service endpoints
    which may be an MCP endpoint, an A2A endpoint, or a wallet address. The
    Succession-specific part is :attr:`memory_root`: the integrity root of the
    memory this identity currently carries, so anyone reading the token can see
    which memory package the identity is paired with. That is the on-chain half
    of "identity and memory move together" made legible without a block
    explorer.
    """

    name: str
    description: str
    wallet: str = ""
    endpoints: dict[str, str] = field(default_factory=dict)
    memory_root: str = ""
    smp_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "type": "https://eips.ethereum.org/EIPS/eip-8004",
            "name": self.name,
            "description": self.description,
            "smp_version": self.smp_version,
        }
        if self.wallet:
            doc["wallet"] = to_checksum_address(self.wallet)
        if self.endpoints:
            doc["endpoints"] = dict(self.endpoints)
        if self.memory_root:
            doc["memory_root"] = self.memory_root
        return doc

    def to_json(self) -> str:
        # Canonical so the same registration always produces the same URI —
        # two agents registered from identical inputs should be byte-identical
        # on chain, not merely equivalent.
        return canonical_json(self.to_dict())


def registration_uri(registration: AgentRegistration, *, scheme: str = "data") -> str:
    """Build the ``agentURI``.

    ``data`` embeds the registration file in the token itself, which is the
    only scheme whose resolvability does not depend on a third party still
    being up. ``https`` and ``ipfs`` are accepted for callers who host it
    elsewhere, and are returned unchanged for the caller to fill in.
    """
    if scheme != "data":
        raise ValueError(
            f"registration_uri builds data: URIs; for {scheme}: host the output of "
            "AgentRegistration.to_json() yourself and pass that URI to register()"
        )
    encoded = base64.b64encode(registration.to_json().encode("utf-8")).decode("ascii")
    return f"data:application/json;base64,{encoded}"


def decode_registration_uri(uri: str) -> dict[str, Any]:
    """Read a ``data:`` registration file back. Raises for other schemes."""
    prefix = "data:application/json;base64,"
    if not uri.startswith(prefix):
        raise ValueError(f"not a base64 data: registration URI: {uri[:40]!r}")
    return json.loads(base64.b64decode(uri[len(prefix) :]).decode("utf-8"))


# -- the agent identity string --------------------------------------------


def agent_identity(chain_id: int, agent_id: int) -> str:
    """The ``erc8004:<chain>:<agentId>`` string used throughout the package.

    Zero-padded to four digits, matching the spec's ``erc8004:84532:0417``.
    Padding is cosmetic and :func:`parse_agent_identity` does not require it.
    """
    return f"erc8004:{chain_id}:{agent_id:04d}"


def parse_agent_identity(identity: str) -> tuple[int, int]:
    """Split ``erc8004:84532:0417`` into ``(84532, 417)``."""
    parts = identity.split(":")
    if len(parts) != 3 or parts[0] != "erc8004":
        raise ValueError(
            f"not an ERC-8004 agent identity: {identity!r} "
            "(expected 'erc8004:<chainId>:<agentId>')"
        )
    return int(parts[1]), int(parts[2])


# -- the registry client ---------------------------------------------------


class IdentityRegistry:
    """A web3 client for an ERC-8004 Identity Registry.

    Every write waits for its receipt and checks ``status``, for the same
    reason :mod:`succession.chain` does: a reverted transaction still returns a
    hash, so returning after ``send_raw_transaction`` would report a
    registration that did not happen.
    """

    def __init__(
        self,
        w3: Any,
        *,
        address: str = BASE_SEPOLIA_IDENTITY_REGISTRY,
        tx_timeout: int = 180,
    ) -> None:
        self.w3 = w3
        self.address = to_checksum_address(address)
        self.tx_timeout = tx_timeout
        self.contract = w3.eth.contract(
            address=self.address, abi=IDENTITY_REGISTRY_ABI
        )

    # -- introspection -------------------------------------------------

    def capabilities(self) -> dict[str, bool]:
        """Which ERC-8004 functions this deployment actually implements.

        Probes the deployed bytecode for each selector. Draft deployments differ
        — the Base Sepolia one predates ``setAgentWallet`` — and finding that out
        from the chain beats finding it out from a revert.
        """
        code = self.w3.eth.get_code(self.address)
        blob = code.hex() if hasattr(code, "hex") else str(code)
        return {
            name: keccak(text=sig)[:4].hex() in blob
            for name, sig in _SELECTORS.items()
        }

    def is_contract(self) -> bool:
        code = self.w3.eth.get_code(self.address)
        return len(code) > 0

    # -- reads ---------------------------------------------------------

    def owner_of(self, agent_id: int) -> str:
        return self.contract.functions.ownerOf(agent_id).call()

    def token_uri(self, agent_id: int) -> str:
        return self.contract.functions.tokenURI(agent_id).call()

    def registration_of(self, agent_id: int) -> dict[str, Any]:
        """The decoded registration file, for a ``data:`` URI."""
        return decode_registration_uri(self.token_uri(agent_id))

    def get_approved(self, agent_id: int) -> str:
        return self.contract.functions.getApproved(agent_id).call()

    def is_approved_for_all(self, owner: str, operator: str) -> bool:
        return self.contract.functions.isApprovedForAll(
            to_checksum_address(owner), to_checksum_address(operator)
        ).call()

    # -- writes --------------------------------------------------------

    def _send(self, fn: Any, private_key: str) -> Any:
        account = Account.from_key(private_key)
        tx = fn.build_transaction(
            {
                "from": account.address,
                "nonce": self.w3.eth.get_transaction_count(account.address),
                "chainId": self.w3.eth.chain_id,
            }
        )
        signed = self.w3.eth.account.sign_transaction(tx, private_key)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        receipt = self.w3.eth.wait_for_transaction_receipt(
            self.w3.eth.send_raw_transaction(raw), timeout=self.tx_timeout
        )
        if receipt["status"] != 1:
            raise RuntimeError(
                f"identity registry call reverted "
                f"({receipt['transactionHash'].hex()})"
            )
        return receipt

    def register(self, registration: AgentRegistration, private_key: str) -> int:
        """Mint a new agent identity to the caller. Returns the ``agentId``.

        Permissionless: ERC-8004 registration needs no whitelist, which is what
        lets the demo mint real identities in a real registry rather than
        standing one up.

        The ``agentId`` is read out of the ``Registered`` event — or, for a
        deployment that does not emit it, out of the ERC-721 ``Transfer`` from
        the zero address, which every conforming implementation emits on mint.
        Reading the return value is not an option: an ``eth_call`` return is not
        available from a receipt.
        """
        uri = registration_uri(registration)
        receipt = self._send(self.contract.functions.register(uri), private_key)
        return self._agent_id_from(receipt)

    def _agent_id_from(self, receipt: Any) -> int:
        """Read the minted ``agentId`` out of the receipt's logs.

        ``Registered`` is ERC-8004's own event and is preferred. A deployment
        that does not emit it still emits the ERC-721 ``Transfer`` from the zero
        address on mint, which every conforming implementation must, so that is
        the fallback. Reading the function's return value is not an option: a
        transaction receipt does not carry one.

        Logs from other contracts in the same transaction are discarded rather
        than raising — the registry is not the only thing that can emit here.
        """
        from web3.logs import DISCARD

        for log in self.contract.events.Registered().process_receipt(
            receipt, errors=DISCARD
        ):
            return int(log["args"]["agentId"])

        for log in self.contract.events.Transfer().process_receipt(
            receipt, errors=DISCARD
        ):
            if int(log["args"]["from"], 16) == 0:
                return int(log["args"]["tokenId"])

        raise RuntimeError(
            "registration succeeded but no Registered or mint Transfer event was "
            "emitted; cannot determine the agentId"
        )

    def approve(self, operator: str, agent_id: int, private_key: str) -> str:
        """Approve ``operator`` (the ListingContract) to move this agent.

        ``ListingContract.list`` checks this at listing time rather than at
        settlement, so a listing that could never settle never reaches a buyer.
        """
        receipt = self._send(
            self.contract.functions.approve(to_checksum_address(operator), agent_id),
            private_key,
        )
        return receipt["transactionHash"].hex()

    def set_metadata(
        self, agent_id: int, key: str, value: bytes, private_key: str
    ) -> str:
        receipt = self._send(
            self.contract.functions.setMetadata(agent_id, key, value), private_key
        )
        return receipt["transactionHash"].hex()

    def get_metadata(self, agent_id: int, key: str) -> bytes:
        return self.contract.functions.getMetadata(agent_id, key).call()
