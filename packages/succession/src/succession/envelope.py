"""Sealed delivery: the package travels encrypted, the key travels on escrow.

Step 3 of the export/hash/import pipeline: "transmit the package to the buyer
over an encrypted channel, with the decryption key released only once escrow
clears." Encrypting the package itself, rather than relying on the transport,
is what makes that sentence enforceable — TLS protects the package from a
stranger, but the thing being defended against here is the buyer receiving the
asset and then declining to pay.

AES-256-GCM, with the listing's hash commitment bound in as additional
authenticated data. That binding is the part worth explaining: it means a
ciphertext prepared for one listing cannot be decrypted under another listing's
context, so a seller cannot fund a cheap listing and be handed the package from
an expensive one. Tampering with either the ciphertext or the listing it claims
to belong to fails the GCM tag rather than producing plausible garbage.

The content key is random per package and is escrowed alongside the payment.
The Merkle commitment is over the *plaintext* package, so encryption is
completely orthogonal to integrity verification — the buyer decrypts, then
verifies exactly as they would have without it.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from Crypto.Cipher import AES

from .canonical import canonical_bytes
from .smp import SMPPackage

__all__ = ["SealedEnvelope", "seal_package", "open_envelope", "EnvelopeError"]

KEY_BYTES = 32
NONCE_BYTES = 12


class EnvelopeError(Exception):
    """The envelope could not be opened: wrong key, wrong listing, or tampered."""


@dataclass(frozen=True)
class SealedEnvelope:
    """An encrypted SMP package. Safe to hand to the buyer before payment."""

    listing_id: str
    hash_commitment: str
    nonce: bytes
    ciphertext: bytes
    tag: bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "hash_commitment": self.hash_commitment,
            "nonce": self.nonce.hex(),
            "ciphertext": self.ciphertext.hex(),
            "tag": self.tag.hex(),
        }

    @classmethod
    def from_dict(cls, blob: dict[str, Any]) -> "SealedEnvelope":
        return cls(
            listing_id=blob["listing_id"],
            hash_commitment=blob["hash_commitment"],
            nonce=bytes.fromhex(blob["nonce"]),
            ciphertext=bytes.fromhex(blob["ciphertext"]),
            tag=bytes.fromhex(blob["tag"]),
        )

    @property
    def size_bytes(self) -> int:
        return len(self.ciphertext)


def _aad(listing_id: str, hash_commitment: str) -> bytes:
    return canonical_bytes(
        {"listing_id": listing_id, "hash_commitment": hash_commitment}
    )


def seal_package(
    package: SMPPackage,
    *,
    listing_id: str,
    hash_commitment: str,
    key: bytes | None = None,
) -> tuple[SealedEnvelope, bytes]:
    """Encrypt a package. Returns ``(envelope, content_key)``.

    The content key is the seller's to escrow — it must not be released until
    the settlement layer says the buyer's funds are held.
    """
    key = key or os.urandom(KEY_BYTES)
    if len(key) != KEY_BYTES:
        raise EnvelopeError(f"content key must be {KEY_BYTES} bytes")
    nonce = os.urandom(NONCE_BYTES)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(_aad(listing_id, hash_commitment))
    plaintext = json.dumps(package.to_dict(), separators=(",", ":")).encode("utf-8")
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return (
        SealedEnvelope(
            listing_id=listing_id,
            hash_commitment=hash_commitment,
            nonce=nonce,
            ciphertext=ciphertext,
            tag=tag,
        ),
        key,
    )


def open_envelope(envelope: SealedEnvelope, key: bytes) -> SMPPackage:
    """Decrypt a package. Raises :class:`EnvelopeError` on any authentication failure."""
    cipher = AES.new(key, AES.MODE_GCM, nonce=envelope.nonce)
    cipher.update(_aad(envelope.listing_id, envelope.hash_commitment))
    try:
        plaintext = cipher.decrypt_and_verify(envelope.ciphertext, envelope.tag)
    except ValueError as exc:
        raise EnvelopeError(
            "envelope failed authentication — wrong content key, wrong listing, "
            "or the ciphertext was modified in transit"
        ) from exc

    blob = json.loads(plaintext)
    data = {
        k: v
        for k, v in blob.items()
        if k not in ("provenance", "permissions", "integrity-proof")
    }
    return SMPPackage(
        data=data,
        header=blob["provenance"],
        permissions=blob["permissions"],
        integrity=blob["integrity-proof"],
    )
