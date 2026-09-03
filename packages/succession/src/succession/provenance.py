"""The provenance header: origin, version, prior-owner chain, and a signature.

The spec's framing is the right one — a signature is what turns "a hash was
posted" into "the seller's own agent cryptographically attested to this exact
content." Two refinements on top of it, both deliberate:

**The signature covers the whole header, not just the root.** The spec says to
sign ``integrity_root``. Signing only the root leaves every other field in the
header unauthenticated: an attacker who intercepts a package can keep a valid
signature over a valid root while rewriting ``agent_identity`` to point at a
different, more valuable agent, or truncating ``provenance_chain`` to hide a
prior owner. The signed preimage here is the canonical header with the
``signature`` field removed, which contains the root and therefore still
satisfies the spec's requirement, while closing that gap. The on-chain
commitment stays the bare ``integrity_root``, so the contract-level comparison
is unchanged.

**The preimage is domain-separated.** It is prefixed with an
``SMP/1.0/provenance`` tag so a signature produced here can never be replayed as
a signature over some other Succession structure that happens to canonicalize to
the same bytes.

Signing is standard EIP-191 personal-sign (``eth-account``'s
``encode_defunct``), so the same signature verifies from ``viem``'s
``verifyMessage`` in the frontend and from ``ecrecover`` on-chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak, to_checksum_address

from .canonical import canonical_bytes, canonical_json
from .smp import SMP_VERSION

__all__ = [
    "DOMAIN",
    "ProvenanceEntry",
    "build_header",
    "signing_preimage",
    "sign_header",
    "verify_header",
    "append_owner",
    "SignatureError",
]

DOMAIN = f"SMP/{SMP_VERSION}/provenance"


class SignatureError(Exception):
    """The header's signature is missing, malformed, or from the wrong signer."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class ProvenanceEntry:
    """One link in the ownership chain."""

    owner: str
    acquired_at: str
    verified_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "acquired_at": self.acquired_at,
            "verified_hash": self.verified_hash,
        }


def build_header(
    *,
    agent_identity: str,
    integrity_root: str,
    memory_version: int,
    categories: list[str],
    permissions: dict[str, Any],
    provenance_chain: list[dict[str, Any]] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Assemble an unsigned provenance header.

    ``permissions_hash`` binds the disclosure record into the signed structure.
    The permissions document is generated rather than exported, so it sits
    outside the Merkle tree over the memory itself — without this field, the
    record of what was withheld would be the one part of the package nobody
    attested to.
    """
    return {
        "smp_version": SMP_VERSION,
        "agent_identity": agent_identity,
        "created_at": created_at or utc_now(),
        "memory_version": int(memory_version),
        "categories": sorted(categories),
        "provenance_chain": list(provenance_chain or []),
        "integrity_root": integrity_root,
        "permissions_hash": "0x" + keccak(canonical_bytes(permissions)).hex(),
        "signature": None,
    }


def signing_preimage(header: dict[str, Any]) -> str:
    """The exact text signed. Domain-tagged, canonical, signature field removed."""
    unsigned = {k: v for k, v in header.items() if k != "signature"}
    return f"{DOMAIN}\n{canonical_json(unsigned)}"


def sign_header(header: dict[str, Any], private_key: str) -> dict[str, Any]:
    """Return a copy of ``header`` with ``signature`` filled in."""
    signed = Account.sign_message(
        encode_defunct(text=signing_preimage(header)), private_key
    )
    return {**header, "signature": "0x" + signed.signature.hex().removeprefix("0x")}


def recover_signer(header: dict[str, Any]) -> str:
    signature = header.get("signature")
    if not signature:
        raise SignatureError("provenance header carries no signature")
    try:
        return Account.recover_message(
            encode_defunct(text=signing_preimage(header)), signature=signature
        )
    except Exception as exc:  # noqa: BLE001 - surface any malformed signature the same way
        raise SignatureError(f"signature could not be recovered: {exc}") from exc


def verify_header(header: dict[str, Any], expected_signer: str) -> str:
    """Check the header's signature against the address that should have signed it.

    Returns the recovered address. Raises :class:`SignatureError` on any
    mismatch — never returns a bool, so a caller cannot forget to check it.
    """
    recovered = recover_signer(header)
    if to_checksum_address(recovered) != to_checksum_address(expected_signer):
        raise SignatureError(
            f"provenance signed by {recovered}, expected {to_checksum_address(expected_signer)}"
        )
    return recovered


def append_owner(
    header: dict[str, Any], *, owner: str, verified_hash: str, acquired_at: str | None = None
) -> list[dict[str, Any]]:
    """The provenance chain a buyer's next export should carry.

    Called once per completed transfer, from the post-sale record step. The
    chain grows by exactly one entry per change of hands, which is why no
    separate lineage mechanism is needed.
    """
    return [
        *header.get("provenance_chain", []),
        ProvenanceEntry(
            owner=owner,
            acquired_at=acquired_at or utc_now(),
            verified_hash=verified_hash,
        ).to_dict(),
    ]
