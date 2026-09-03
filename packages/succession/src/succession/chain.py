"""The on-chain SettlementBackend — the real ListingContract, over web3.

``LocalSettlement`` mirrors the contract's state machine so the pipeline can be
exercised without a funded wallet. This is the other implementation of the same
:class:`~succession.settlement.SettlementBackend` interface, and it is the one
that makes the claim true: escrow, the hash comparison, the identity transfer,
and the seal all happen in ``ListingContract.sol`` on Base.

Both satisfy one interface on purpose. The transfer orchestrator does not know
which it is talking to, so swapping the chain in changes nothing above this
line — and the two cannot quietly diverge into a more forgiving local contract,
because the same state-machine tests run against both.

Two things this file is careful about:

**Every write waits for its receipt and checks ``status``.** A transaction that
reverts still returns a hash, so a backend that returns after ``send_raw_
transaction`` reports success for a sale that did not happen.

**Settlement reads its outcome from the emitted event, not from the arguments
it sent.** ``confirmTransfer`` refunds rather than reverting on a hash
mismatch, so the transaction succeeds either way; only the log says which
happened. Assuming the happy path here would report a released escrow on a
refund.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address

from .merkle import from_hex, to_hex
from .settlement import Listing, ListingState, SettlementError, SettlementReceipt

__all__ = ["ChainSettlement", "load_artifact", "ATTESTATION_DOMAIN"]

#: Must match ``ListingContract.attestationDigest``'s domain tag exactly.
ATTESTATION_DOMAIN = "Succession/1.0/listing-attestation"

_ARTIFACTS = (
    Path(__file__).resolve().parents[4] / "contracts" / "out" / "artifacts.json"
)

#: Solidity ``State`` enum, in declaration order.
_STATES = (
    None,
    ListingState.OPEN,
    ListingState.ESCROWED,
    ListingState.CONFIRMED,
    ListingState.REFUNDED,
)


def load_artifact(name: str, path: str | Path | None = None) -> dict[str, Any]:
    source = Path(path) if path else _ARTIFACTS
    if not source.exists():
        raise SettlementError(
            f"contract artifacts not found at {source}; run `npm run build` in contracts/"
        )
    artifacts = json.loads(source.read_text())
    if name not in artifacts:
        raise SettlementError(f"no artifact named {name!r} in {source}")
    return artifacts[name]


def listing_id_to_bytes32(listing_id: str) -> bytes:
    """Encode a human listing id as the contract's ``bytes32`` key.

    UTF-8, right-padded — so ``listing-0417`` reads back legibly in a block
    explorer instead of as an opaque hash. Anything that does not fit is a
    caller error rather than a silent truncation, because two listings whose
    ids differ only past byte 32 would collide on one storage slot.
    """
    raw = listing_id.encode("utf-8")
    if len(raw) > 32:
        raise SettlementError(
            f"listing id {listing_id!r} is {len(raw)} bytes; the contract key is 32"
        )
    return raw.ljust(32, b"\x00")


def bytes32_to_listing_id(raw: bytes) -> str:
    return bytes(raw).rstrip(b"\x00").decode("utf-8", errors="replace")


class ChainSettlement:
    """Drives ``ListingContract`` on Base (or any EVM) through web3.py."""

    def __init__(
        self,
        w3: Any,
        *,
        contract_address: str,
        seller_key: str | None = None,
        buyer_key: str | None = None,
        artifacts_path: str | Path | None = None,
        tx_timeout: int = 180,
    ) -> None:
        self.w3 = w3
        self.tx_timeout = tx_timeout
        listing_abi = load_artifact("ListingContract", artifacts_path)["abi"]
        self.contract = w3.eth.contract(
            address=to_checksum_address(contract_address), abi=listing_abi
        )
        self._keys: dict[str, str] = {}
        for key in (seller_key, buyer_key):
            if key:
                self._keys[Account.from_key(key).address.lower()] = key

    # -- identities ----------------------------------------------------

    def register_key(self, private_key: str) -> str:
        address = Account.from_key(private_key).address
        self._keys[address.lower()] = private_key
        return address

    def _key_for(self, address: str) -> str:
        key = self._keys.get(address.lower())
        if key is None:
            raise SettlementError(
                f"no signing key registered for {address}; pass it to the "
                "constructor or call register_key()"
            )
        return key

    # -- transactions --------------------------------------------------

    def _send(self, fn: Any, sender: str) -> Any:
        """Sign, send, wait, and insist the receipt says the call succeeded."""
        sender = to_checksum_address(sender)
        tx = fn.build_transaction(
            {
                "from": sender,
                "nonce": self.w3.eth.get_transaction_count(sender),
                "chainId": self.w3.eth.chain_id,
            }
        )
        signed = self.w3.eth.account.sign_transaction(tx, self._key_for(sender))
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        tx_hash = self.w3.eth.send_raw_transaction(raw)
        receipt = self.w3.eth.wait_for_transaction_receipt(
            tx_hash, timeout=self.tx_timeout
        )
        if receipt["status"] != 1:
            raise SettlementError(
                f"transaction {tx_hash.hex()} reverted on chain"
            )
        return receipt

    def attest(self, listing_id: str, agent_id: int, commitment: str, key: str) -> bytes:
        """Sign the listing attestation the contract recovers.

        The digest binds the chain id and the contract address as well as the
        sale terms, so a signature cannot be replayed onto another listing,
        another deployment, or another chain.
        """
        digest = self.contract.functions.attestationDigest(
            listing_id_to_bytes32(listing_id), agent_id, from_hex(commitment)
        ).call()
        return Account.sign_message(encode_defunct(digest), key).signature

    # -- SettlementBackend ---------------------------------------------

    def list_asset(
        self,
        *,
        listing_id: str,
        agent_id: str,
        seller: str,
        seller_signature: str,
        hash_commitment: str,
        price: int,
        currency: str = "USDC",
        categories: tuple[str, ...] = (),
        valuation_reference: str = "",
        token_id: int | None = None,
    ) -> Listing:
        """Post the listing on chain.

        ``agent_id`` is the ERC-8004 identity string (``erc8004:84532:0417``);
        the contract wants the bare token id, so it is parsed out here unless
        given explicitly. ``seller_signature`` is the *provenance header*
        signature, which the contract cannot verify — it signs a document the
        EVM never sees. The on-chain attestation is a separate signature over a
        digest the contract can rebuild, produced here.
        """
        tid = token_id if token_id is not None else _token_id_of(agent_id)
        attestation = self.attest(
            listing_id, tid, hash_commitment, self._key_for(seller)
        )
        self._send(
            self.contract.functions.list(
                listing_id_to_bytes32(listing_id),
                tid,
                from_hex(hash_commitment),
                price,
                attestation,
            ),
            seller,
        )
        return self.get(listing_id)

    def get(self, listing_id: str) -> Listing:
        try:
            raw = self.contract.functions.getListing(
                listing_id_to_bytes32(listing_id)
            ).call()
        except Exception as exc:  # noqa: BLE001 - the revert means "no such listing"
            raise SettlementError(f"no such listing: {listing_id!r} ({exc})") from exc

        seller, buyer, agent_id, commitment, price, _deadline, state, delivered = raw
        return Listing(
            listing_id=listing_id,
            agent_id=str(agent_id),
            seller=seller,
            seller_signature="",
            hash_commitment=to_hex(commitment),
            price=int(price),
            state=_STATES[int(state)] or ListingState.OPEN,
            buyer="" if int(buyer, 16) == 0 else buyer,
            escrow_balance=int(price) if _STATES[int(state)] is ListingState.ESCROWED else 0,
            delivered_hash=to_hex(delivered) if int.from_bytes(delivered, "big") else "",
            sealed=bool(self.contract.functions.isSealed(int(agent_id)).call()),
        )

    def buy(self, listing_id: str, *, buyer: str, amount: int) -> Listing:
        """Fund escrow. The token approval is the caller's to arrange."""
        listing = self.get(listing_id)
        if amount != listing.price:
            raise SettlementError(
                f"escrow must be exactly the asking price ({listing.price}), got {amount}"
            )
        self._send(self.contract.functions.buy(listing_id_to_bytes32(listing_id)), buyer)
        return self.get(listing_id)

    def confirm_transfer(
        self, listing_id: str, *, delivered_hash: str, buyer_identity: str
    ) -> SettlementReceipt:
        """Submit the re-derived root; the contract releases or refunds.

        The outcome is read from the emitted event rather than assumed. A hash
        mismatch refunds instead of reverting, so the transaction succeeds
        either way and only the log distinguishes them.
        """
        listing = self.get(listing_id)
        if listing.state is not ListingState.ESCROWED:
            raise SettlementError(
                f"listing {listing_id!r} is {listing.state.value}; nothing is escrowed"
            )
        receipt = self._send(
            self.contract.functions.confirmTransfer(
                listing_id_to_bytes32(listing_id), from_hex(delivered_hash)
            ),
            listing.buyer,
        )
        return self._receipt_from_logs(listing, receipt)

    def refund(
        self, listing_id: str, *, reason: str, delivered_hash: str = ""
    ) -> SettlementReceipt:
        listing = self.get(listing_id)
        receipt = self._send(
            self.contract.functions.refund(
                listing_id_to_bytes32(listing_id), reason[:200]
            ),
            listing.buyer or listing.seller,
        )
        return self._receipt_from_logs(listing, receipt)

    def _receipt_from_logs(self, listing: Listing, receipt: Any) -> SettlementReceipt:
        from web3.logs import DISCARD

        tx_hash = receipt["transactionHash"].hex()
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash
        block = self.w3.eth.get_block(receipt["blockNumber"])
        settled_at = _iso(block["timestamp"])

        confirmed = self.contract.events.TransferConfirmed().process_receipt(
            receipt, errors=DISCARD
        )
        if confirmed:
            args = confirmed[0]["args"]
            return SettlementReceipt(
                listing_id=listing.listing_id,
                outcome="released",
                amount=int(args["amountReleased"]),
                paid_to=listing.seller,
                identity_transferred_to=args["buyer"],
                sealed_agent=str(args["agentId"]),
                reference=tx_hash,
                settled_at=settled_at,
            )

        refunded = self.contract.events.Refunded().process_receipt(
            receipt, errors=DISCARD
        )
        if refunded:
            args = refunded[0]["args"]
            return SettlementReceipt(
                listing_id=listing.listing_id,
                outcome="refunded",
                amount=int(args["amount"]),
                paid_to=args["buyer"],
                identity_transferred_to="",
                sealed_agent="",
                reference=tx_hash,
                settled_at=settled_at,
            )

        raise SettlementError(
            f"transaction {tx_hash} emitted neither TransferConfirmed nor Refunded"
        )

    # -- convenience ---------------------------------------------------

    def approve_payment(self, token_address: str, owner: str, amount: int) -> str:
        """Approve the listing contract to pull ``amount`` from ``owner``."""
        token = self.w3.eth.contract(
            address=to_checksum_address(token_address), abi=_ERC20_APPROVE_ABI
        )
        receipt = self._send(
            token.functions.approve(self.contract.address, amount), owner
        )
        return receipt["transactionHash"].hex()

    def approve_identity(self, registry_address: str, owner: str, agent_id: int) -> str:
        """Approve the listing contract to move the agent's identity token."""
        registry = self.w3.eth.contract(
            address=to_checksum_address(registry_address), abi=_ERC721_APPROVE_ABI
        )
        receipt = self._send(
            registry.functions.approve(self.contract.address, agent_id), owner
        )
        return receipt["transactionHash"].hex()


def _token_id_of(agent_identity: str) -> int:
    """``erc8004:84532:0417`` -> ``417``."""
    tail = agent_identity.rsplit(":", 1)[-1]
    try:
        return int(tail)
    except ValueError as exc:
        raise SettlementError(
            f"cannot read an ERC-8004 token id from {agent_identity!r}"
        ) from exc


def _iso(timestamp: int) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_ERC20_APPROVE_ABI = [
    {
        "name": "approve",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    }
]

_ERC721_APPROVE_ABI = [
    {
        "name": "approve",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "tokenId", "type": "uint256"},
        ],
        "outputs": [],
    }
]
