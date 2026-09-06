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


def await_chain_state(w3: Any, receipt: Any, tries: int = 25) -> None:
    """Block until the node we are talking to has caught up to a mined write.

    A receipt proves a transaction was mined. It does not prove that the next
    RPC call will see its effect: public endpoints are load balanced across
    nodes, and the very next `eth_call` or `eth_estimate_gas` is routinely
    served by one a block or two behind. That produced two different failures
    here, both against state that was demonstrably already on chain, and both
    invisible to the test suite because py-evm mines and serves from a single
    in-process chain.

    Waiting for the reported head to reach the receipt's block is the honest
    fix. Retrying the failed read would hide a real lag behind a loop, and
    pre-supplying a gas limit to dodge the estimate would hide it behind a
    guess.
    """
    import time

    target = receipt["blockNumber"]
    for attempt in range(tries):
        try:
            if w3.eth.block_number >= target:
                return
        except Exception:  # noqa: BLE001 - a transient RPC error is worth retrying
            pass
        time.sleep(min(0.3 * (attempt + 1), 2.5))
    # Not fatal on its own: the caller's next read may still succeed.


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

def _plain(value: Any) -> Any:
    """Make a decoded event argument JSON-safe without losing what it is."""
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return value


def _listing_of(args: Any) -> str:
    """The listing an event belongs to, or empty for one that names an agent.

    `AgentSealed` is keyed by agent id rather than by listing, so it has no
    listing to report. Returning empty rather than inventing one keeps the
    caller from joining a seal onto the wrong sale.
    """
    raw = dict(args).get("listingId")
    if raw is None:
        return ""
    return bytes32_to_listing_id(bytes(raw))



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
                # "pending" counts transactions this sender has in the mempool
                # as well as those already mined. Every send here waits for its
                # receipt, so "latest" was correct in practice — but a second
                # backend sharing this key, or any future concurrency, would
                # build two transactions on the same nonce and one would be
                # dropped. Asking for pending costs nothing and removes the trap.
                "nonce": self.w3.eth.get_transaction_count(sender, "pending"),
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
        # Every caller here reads back what it just wrote.
        await_chain_state(self.w3, receipt)
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

        # Unpacked positionally, so the order here is the struct's order in
        # ListingContract.sol. `escrowed` is last and was added after the rest;
        # a field appended there is invisible to this line until it is named.
        (
            seller,
            buyer,
            agent_id,
            commitment,
            price,
            _deadline,
            state,
            delivered,
            escrowed,
        ) = raw
        return Listing(
            listing_id=listing_id,
            agent_id=str(agent_id),
            seller=seller,
            seller_signature="",
            hash_commitment=to_hex(commitment),
            price=int(price),
            state=_STATES[int(state)] or ListingState.OPEN,
            buyer="" if int(buyer, 16) == 0 else buyer,
            # What the contract actually holds for this listing, not what it was
            # asked for — the two differ if a token ever shorts the transfer.
            escrow_balance=int(escrowed),
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
        self,
        listing_id: str,
        *,
        delivered_hash: str,
        buyer_identity: str,
        caller: str | None = None,
    ) -> SettlementReceipt:
        """Submit the re-derived root; the contract releases or refunds.

        The outcome is read from the emitted event rather than assumed. A hash
        mismatch refunds instead of reverting, so the transaction succeeds
        either way and only the log distinguishes them.

        ``caller`` selects who submits. It defaults to the buyer, which is the
        self-reported path the contract's own docstring calls out as the known
        adversarial edge; passing the arbiter is what closes it, and the
        contract already accepts either. The receipt records which one it was.
        """
        listing = self.get(listing_id)
        if listing.state is not ListingState.ESCROWED:
            raise SettlementError(
                f"listing {listing_id!r} is {listing.state.value}; nothing is escrowed"
            )
        sender = caller or listing.buyer
        confirmed_by = self._role_of(listing, sender)
        receipt = self._send(
            self.contract.functions.confirmTransfer(
                listing_id_to_bytes32(listing_id), from_hex(delivered_hash)
            ),
            sender,
        )
        return self._receipt_from_logs(listing, receipt, confirmed_by=confirmed_by)

    @property
    def arbiter(self) -> str:
        """The address the deployed contract accepts alongside the buyer."""
        return self.contract.functions.arbiter().call()

    def _role_of(self, listing: Listing, caller: str) -> str:
        """Mirror the contract's ``NotAuthorised`` check, before spending gas."""
        if listing.buyer and caller.lower() == listing.buyer.lower():
            return "buyer"
        if caller.lower() == self.arbiter.lower():
            return "arbiter"
        raise SettlementError(
            f"{caller} is neither the buyer nor the arbiter of listing "
            f"{listing.listing_id!r}; confirmTransfer would revert with NotAuthorised"
        )

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

    def cancel(self, listing_id: str, *, seller: str | None = None) -> Listing:
        """Withdraw an unfunded listing. Mirrors ``LocalSettlement.cancel``.

        No receipt: nothing settled and no money moved, so there is nothing to
        record beyond the listing's new state.
        """
        listing = self.get(listing_id)
        self._send(
            self.contract.functions.cancel(listing_id_to_bytes32(listing_id)),
            seller or listing.seller,
        )
        return self.get(listing_id)

    # -- discovery -----------------------------------------------------

    #: The public Base Sepolia endpoint refuses `eth_getLogs` over wider spans
    #: with a 413. Measured, not guessed: 50,000 fails and 10,000 succeeds.
    LOG_SPAN = 9_000

    #: The events that constitute the ledger, in the order a sale emits them.
    #: `Cancelled` is here for a reason that is easy to miss: `cancel()` writes
    #: state `Refunded`, so a cancellation and a genuine refund are
    #: indistinguishable from the listing struct alone. Only the event separates
    #: them, which makes this scan the sole way to report either honestly.
    ACTIVITY_EVENTS = (
        "Listed",
        "Escrowed",
        "TransferConfirmed",
        "Refunded",
        "Cancelled",
        "AgentSealed",
    )

    def activity(
        self,
        *,
        lookback_blocks: int = 120_000,
        span: int | None = None,
        limit: int = 250,
    ) -> list[dict[str, Any]]:
        """Every state change the contract has emitted, newest first.

        The listing views answer "what is true now". This answers "what
        happened", which is a different question and the only one that can say
        when a sale settled, who bought it, and in which transaction.

        Paged and bounded exactly as `listed_ids` is, and for the same measured
        reason: the public endpoint refuses wide ranges with a 413. Windows walk
        backwards from the head so a scan that stops early has returned the most
        recent activity rather than an arbitrary slice, and one refused window is
        skipped rather than being allowed to empty the whole ledger.

        Decoded through the contract's own event ABIs rather than by matching raw
        topics, because the arguments are the point here; `listed_ids` only ever
        needed the indexed id.
        """
        head = self.w3.eth.block_number
        step = span or self.LOG_SPAN
        floor = max(0, head - lookback_blocks)

        raw: list[Any] = []
        upper = head
        while upper > floor and len(raw) < limit:
            lower = max(floor, upper - step)
            for name in self.ACTIVITY_EVENTS:
                try:
                    raw.extend(
                        getattr(self.contract.events, name)().get_logs(
                            from_block=lower, to_block=upper
                        )
                    )
                except Exception:  # noqa: BLE001 - a refused window is not fatal
                    continue
            upper = lower

        # Newest first. Ordering on (block, log index) rather than on the block
        # alone keeps two events from one transaction — a confirm and its seal —
        # in the order the contract actually emitted them.
        raw.sort(key=lambda log: (log["blockNumber"], log["logIndex"]), reverse=True)
        raw = raw[:limit]

        # One timestamp lookup per block rather than per log. A settled sale
        # emits three events in the same block, and asking three times is three
        # round trips for one answer.
        stamps: dict[int, int] = {}
        for number in {log["blockNumber"] for log in raw}:
            try:
                stamps[number] = self.w3.eth.get_block(number)["timestamp"]
            except Exception:  # noqa: BLE001 - a missing stamp is not a missing event
                continue

        return [
            {
                "event": log["event"],
                "listing_id": _listing_of(log["args"]),
                "block": log["blockNumber"],
                "timestamp": stamps.get(log["blockNumber"]),
                "tx": log["transactionHash"].hex()
                if hasattr(log["transactionHash"], "hex")
                else str(log["transactionHash"]),
                "args": {k: _plain(v) for k, v in dict(log["args"]).items()},
            }
            for log in raw
        ]

    def listed_ids(
        self, *, lookback_blocks: int = 120_000, span: int | None = None
    ) -> list[str]:
        """Every listing id the contract has emitted a `Listed` event for.

        The marketplace previously enumerated only what sellers had posted to
        its own metadata table, which meant a listing made on chain without that
        extra step was real, settled, and invisible. The chain is the source of
        truth for what exists, so this is what the marketplace should read, and
        metadata is an enrichment on top rather than the index itself.

        Bounded and paged for the same reason the registry scan is: the endpoint
        refuses wide ranges. Newest first, so a truncated scan returns the most
        recent listings rather than an arbitrary slice.
        """
        head = self.w3.eth.block_number
        step = span or self.LOG_SPAN
        topic = self.w3.keccak(text="Listed(bytes32,address,uint256,bytes32,uint256)")

        seen: list[str] = []
        already: set[str] = set()
        upper = head
        floor = max(0, head - lookback_blocks)

        while upper > floor:
            lower = max(floor, upper - step)
            try:
                logs = self.w3.eth.get_logs(
                    {
                        "address": self.contract.address,
                        "fromBlock": lower,
                        "toBlock": upper,
                        "topics": [topic],
                    }
                )
                # Within a window, newest last; reversed keeps the overall list
                # in newest-first order as windows walk backwards.
                for log in reversed(logs):
                    listing_id = bytes32_to_listing_id(bytes(log["topics"][1]))
                    if listing_id and listing_id not in already:
                        already.add(listing_id)
                        seen.append(listing_id)
            except Exception:  # noqa: BLE001 - one refused window is not fatal
                pass
            upper = lower

        return seen

    def _receipt_from_logs(
        self, listing: Listing, receipt: Any, *, confirmed_by: str = "buyer"
    ) -> SettlementReceipt:
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
                confirmed_by=confirmed_by,
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
                confirmed_by=confirmed_by,
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
