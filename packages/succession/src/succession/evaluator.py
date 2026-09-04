"""The Evaluator: an independent third party that re-derives what it is told.

The hole this closes
--------------------

``confirmTransfer`` is normally called by the buyer, who asserts the hash they
derived from what they received. ``ListingContract``'s own docstring states the
consequence plainly: a dishonest buyer can submit a wrong hash, trigger the
automatic refund, and keep the decrypted package. No on-chain logic can close
that, because the chain cannot see the delivered bytes.

The designed answer — Part 4's "optional but strong for a technical judge", and
the top correctness item on the roadmap — is a third party that re-derives the
root *itself* and confirms on its own authority. The contract has always
accepted an ``arbiter`` alongside the buyer; this module is the agent that
occupies that role.

This is deliberately the same trust pattern Virtuals ACP already uses for job
quality, pointed at delivery integrity instead: the counterparties do not have
to trust each other, because a third party with no stake in the outcome checks
the claim against the artifact.

What "independent" has to mean to be worth anything
---------------------------------------------------

An evaluator that accepts the buyer's number and signs it has added a signature
and no information. So this one is not given a root to check. It is given the
buyer's store, and it runs the *export pipeline* over it to produce a root of
its own — the same code path the seller ran, against the destination rather
than the source. Only then does it compare.

Three findings come out of a full evaluation, and they answer different
questions:

* ``root`` — does the memory that actually landed in the buyer's tenant hash to
  what the seller committed to before a buyer existed?
* ``signature`` — did the agent being sold attest to that content, or merely
  some key?
* ``preview`` — were the data-room figures the buyer decided on true of the
  memory they received? A seller who overstates the asset and delivers it
  intact passes the first two checks and has still misrepresented the sale.

The verdict is signed with the evaluator's own key, domain-separated so it can
never be replayed as a provenance signature. A verdict is evidence a buyer can
show a third party, which it would not be if the evaluator merely acted on it.

What it still does not solve, stated rather than hidden
-------------------------------------------------------

The evaluator has to read the buyer's imported store to re-derive anything, so
the buyer can refuse it access. That is not a hole in the mechanism so much as
its boundary: a buyer who refuses the evaluator gets no arbiter confirmation,
and the escrow sits until it expires and ``reclaimExpired`` returns their money.
Which is the correct outcome — the seller is no worse off than before the sale,
and nobody was paid for a delivery nobody was allowed to check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address

from .canonical import canonical_json
from .dataroom import build_preview
from .export import build_package
from .merkle import from_hex, to_hex
from .provenance import SignatureError, recover_signer
from .settlement import SettlementError, SettlementReceipt
from .smp import SMPPackage

__all__ = [
    "EVALUATION_DOMAIN",
    "Finding",
    "Verdict",
    "Evaluator",
    "verify_verdict",
]

#: Domain tag for the evaluator's signature. Distinct from the provenance
#: domain so a verdict can never be replayed as a seller attestation, or the
#: reverse.
EVALUATION_DOMAIN = "SMP/1.0/evaluation"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Finding:
    """One check the evaluator performed, and what it found.

    ``expected`` and ``observed`` are carried even when they agree, so a verdict
    reads as a record of what was checked rather than only of what went wrong.
    A finding with no values is a finding nobody can audit.
    """

    check: str
    passed: bool
    expected: str
    observed: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "passed": self.passed,
            "expected": self.expected,
            "observed": self.observed,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Verdict:
    """A signed, independently-derived opinion on one delivery."""

    listing_id: str
    committed_root: str
    evaluator_root: str
    findings: tuple[Finding, ...]
    evaluator: str
    evaluated_at: str
    signature: str = ""

    @property
    def verified(self) -> bool:
        return all(f.passed for f in self.findings)

    @property
    def failures(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if not f.passed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "committed_root": self.committed_root,
            "evaluator_root": self.evaluator_root,
            "verified": self.verified,
            "findings": [f.to_dict() for f in self.findings],
            "evaluator": self.evaluator,
            "evaluated_at": self.evaluated_at,
            "signature": self.signature,
        }

    def signing_preimage(self) -> str:
        """The exact text signed. Domain-tagged, canonical, signature removed."""
        body = {k: v for k, v in self.to_dict().items() if k != "signature"}
        return f"{EVALUATION_DOMAIN}\n{canonical_json(body)}"

    def summary(self) -> str:
        if self.verified:
            return (
                f"Independently verified. Re-derived root "
                f"{self.evaluator_root} matches the listing commitment."
            )
        first = self.failures[0]
        return (
            f"Failed {first.check}: expected {first.expected}, "
            f"observed {first.observed}."
        )


def verify_verdict(verdict: Verdict, *, expected_evaluator: str = "") -> str:
    """Recover the signer of a verdict, optionally pinning who it must be.

    Raises :class:`~succession.provenance.SignatureError` rather than returning
    a bool, for the same reason ``verify_header`` does: a caller cannot forget
    to check a raised exception.
    """
    if not verdict.signature:
        raise SignatureError("verdict carries no signature")
    try:
        recovered = Account.recover_message(
            encode_defunct(text=verdict.signing_preimage()),
            signature=verdict.signature,
        )
    except Exception as exc:  # noqa: BLE001 - any malformed signature, one way
        raise SignatureError(f"verdict signature could not be recovered: {exc}") from exc

    if expected_evaluator and to_checksum_address(recovered) != to_checksum_address(
        expected_evaluator
    ):
        raise SignatureError(
            f"verdict signed by {recovered}, expected "
            f"{to_checksum_address(expected_evaluator)}"
        )
    return recovered


class Evaluator:
    """A third-party agent that re-derives a delivery and settles on its finding.

    Holds the key behind the address the ``ListingContract`` was deployed with
    as its ``arbiter``. It has no stake in either side of the sale, which is the
    only thing that makes its confirmation worth more than the buyer's.
    """

    def __init__(self, private_key: str, *, name: str = "succession-evaluator") -> None:
        self._key = private_key
        self.address = Account.from_key(private_key).address
        self.name = name

    # -- the individual checks -----------------------------------------

    def re_derive_root(
        self,
        sink: Any,
        *,
        categories: Sequence[str] | None = None,
        category_map: dict[str, str] | None = None,
    ) -> str:
        """Run the export pipeline over the buyer's store and hash the result.

        This is the whole basis of the evaluator's independence: it does not
        check a number it was handed, it produces one. Same canonicalization,
        same Merkle construction, same category routing the seller used — over
        the destination rather than the source.
        """
        package, _ = build_package(
            sink, categories=categories, category_map=category_map
        )
        return to_hex(package.tree().root)

    def check_root(self, committed_root: str, observed_root: str) -> Finding:
        try:
            matched = from_hex(committed_root) == from_hex(observed_root)
        except ValueError as exc:
            return Finding(
                check="integrity-root",
                passed=False,
                expected=committed_root,
                observed=observed_root,
                detail=f"malformed digest: {exc}",
            )
        return Finding(
            check="integrity-root",
            passed=matched,
            expected=committed_root,
            observed=observed_root,
            detail=(
                "Re-derived from the buyer's own store by the evaluator, not "
                "taken from the buyer's assertion."
            )
            if matched
            else (
                "The memory in the buyer's tenant does not hash to the root "
                "committed at listing time."
            ),
        )

    def check_signature(self, package: SMPPackage, expected_signer: str) -> Finding:
        """Confirm the agent being sold attested to this exact content."""
        try:
            recovered = recover_signer(package.header)
        except SignatureError as exc:
            return Finding(
                check="seller-signature",
                passed=False,
                expected=expected_signer,
                observed="",
                detail=str(exc),
            )
        matched = to_checksum_address(recovered) == to_checksum_address(expected_signer)
        return Finding(
            check="seller-signature",
            passed=matched,
            expected=to_checksum_address(expected_signer),
            observed=to_checksum_address(recovered),
            detail=(
                "The signature covers the whole provenance header, so agent "
                "identity and the owner chain are authenticated too."
            )
            if matched
            else "The package was signed by a key other than the listed agent's.",
        )

    def check_preview(
        self, source: Any, claimed: dict[str, Any], *, agent_identity: str = ""
    ) -> list[Finding]:
        """Re-derive the data-room figures and compare them to what was shown.

        The spec's suggested use of an evaluator is exactly this: independently
        re-derive the redacted preview stats as a check against seller-supplied
        numbers. A sale can be perfectly intact and still have been sold on a
        false prospectus, and only this check catches that.

        ``source`` must be **the seller's tenant** — the store the data room
        actually described. Pointing this at the buyer's post-import store
        instead looks equivalent and is not: records the seller marked
        non-transferable are withheld from the package by design, so an
        entirely honest sale delivers a store that is legitimately smaller than
        the one the preview was computed over. An evaluator that compared those
        two would report fraud on every correct transfer, which is worse than
        not checking at all — a check that cries wolf gets switched off.

        This is therefore a *pre-purchase* audit, run while the seller's tenant
        is still readable, which is also when its finding is worth something:
        it tells a buyer whether to fund escrow, not whether to regret having
        done so.
        """
        observed = build_preview(source, agent_identity=agent_identity).to_dict()
        findings: list[Finding] = []
        for field_name in ("counts", "memory_size_bytes", "tenure_days"):
            if field_name not in claimed:
                continue
            want, got = claimed[field_name], observed.get(field_name)
            findings.append(
                Finding(
                    check=f"preview:{field_name}",
                    passed=want == got,
                    expected=canonical_json(want),
                    observed=canonical_json(got),
                    detail=(
                        ""
                        if want == got
                        else "The data room overstated or understated the asset."
                    ),
                )
            )
        return findings

    def audit_listing(
        self,
        source: Any,
        claimed_preview: dict[str, Any],
        *,
        listing_id: str,
        committed_root: str = "",
        agent_identity: str = "",
    ) -> Verdict:
        """Pre-purchase: are the data room's figures true of the seller's store?

        Produces a signed verdict a buyer can read before funding escrow. It
        deliberately does not re-derive the integrity root: at this point the
        package has not been delivered, and the only root available would be
        the seller's own — checking a seller's number against the same seller's
        store proves nothing about delivery.
        """
        verdict = Verdict(
            listing_id=listing_id,
            committed_root=committed_root,
            evaluator_root="",
            findings=tuple(
                self.check_preview(
                    source, claimed_preview, agent_identity=agent_identity
                )
            ),
            evaluator=self.address,
            evaluated_at=_utc_now(),
        )
        return self.sign(verdict)

    # -- the full evaluation -------------------------------------------

    def evaluate(
        self,
        *,
        listing_id: str,
        committed_root: str,
        buyer_sink: Any,
        package: SMPPackage | None = None,
        expected_signer: str = "",
        categories: Sequence[str] | None = None,
        category_map: dict[str, str] | None = None,
    ) -> Verdict:
        """Post-delivery: does the buyer's store hash to the commitment?

        ``categories`` must match the sale's scope. A partial sale commits a
        root over exactly the categories sold, so re-deriving over all six would
        produce a mismatch on an honest delivery — the evaluator would then be
        the thing causing the false refund it exists to prevent.

        The data-room audit is deliberately *not* folded in here; it runs
        against the seller's tenant before purchase, via :meth:`audit_listing`.
        See :meth:`check_preview` for why the two cannot share a source.
        """
        selected = (
            list(categories)
            if categories is not None
            else (list(package.data.keys()) if package is not None else None)
        )
        observed_root = self.re_derive_root(
            buyer_sink, categories=selected, category_map=category_map
        )

        findings = [self.check_root(committed_root, observed_root)]
        if package is not None and expected_signer:
            findings.append(self.check_signature(package, expected_signer))

        verdict = Verdict(
            listing_id=listing_id,
            committed_root=committed_root,
            evaluator_root=observed_root,
            findings=tuple(findings),
            evaluator=self.address,
            evaluated_at=_utc_now(),
        )
        return self.sign(verdict)

    def sign(self, verdict: Verdict) -> Verdict:
        signed = Account.sign_message(
            encode_defunct(text=verdict.signing_preimage()), self._key
        )
        return Verdict(
            listing_id=verdict.listing_id,
            committed_root=verdict.committed_root,
            evaluator_root=verdict.evaluator_root,
            findings=verdict.findings,
            evaluator=verdict.evaluator,
            evaluated_at=verdict.evaluated_at,
            signature="0x" + signed.signature.hex().removeprefix("0x"),
        )

    # -- settlement ----------------------------------------------------

    def settle(
        self,
        settlement: Any,
        verdict: Verdict,
        *,
        buyer_identity: str,
    ) -> SettlementReceipt:
        """Submit the evaluator's own root as the arbiter.

        Note which root is submitted: :attr:`Verdict.evaluator_root`, never the
        buyer's. That substitution is the entire point — the contract settles
        against a number a disinterested party derived from the delivered
        memory, so a buyer's false claim of mismatch no longer reaches it.

        A failed verdict is *not* silently turned into a refund here. The
        contract refunds on a mismatched hash by itself, and submitting the
        evaluator's mismatching root produces exactly that outcome through the
        contract's own logic rather than through a second, parallel refund path
        that could disagree with it.
        """
        if verdict.listing_id != getattr(
            settlement.get(verdict.listing_id), "listing_id", verdict.listing_id
        ):  # pragma: no cover - defensive; get() raises for an unknown listing
            raise SettlementError(f"no listing {verdict.listing_id!r}")

        return settlement.confirm_transfer(
            verdict.listing_id,
            delivered_hash=verdict.evaluator_root,
            buyer_identity=buyer_identity,
            caller=self.address,
        )
