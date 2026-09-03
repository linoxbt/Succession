"""The Succession Certificate.

Pure presentation. Every field below is already produced by a step somewhere
else in the pipeline — the header, the tree, the import result, the seal — so
this module adds no new data plumbing, which is exactly what the spec asks for.
It renders, and it does not compute.

Deliberately a text/JSON artifact rather than a styled PDF. A certificate whose
value is "this hash matched that hash" gains nothing from typesetting, and the
build time is better spent on the thing being certified.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

__all__ = ["SuccessionCertificate"]


def _abbrev(value: str, head: int = 10, tail: int = 8) -> str:
    if len(value) <= head + tail + 1:
        return value
    return f"{value[:head]}…{value[-tail:]}"


@dataclass(frozen=True)
class SuccessionCertificate:
    asset_id: str
    origin_agent: str
    successor_agent: str
    memory_version: int
    records_transferred: int
    integrity_hash: str
    transfer_date: str
    status: str
    categories: tuple[str, ...] = ()
    seller_signature: str = ""
    seller_tenant_sealed_at: str = ""
    settlement_reference: str = ""

    @classmethod
    def from_transfer(
        cls,
        *,
        header: dict[str, Any],
        import_result: Any,
        transfer_date: str,
        successor_agent: str,
        seal_record: Any = None,
        settlement_reference: str = "",
    ) -> "SuccessionCertificate":
        agent = header["agent_identity"]
        return cls(
            asset_id="#" + agent.rsplit(":", 1)[-1],
            origin_agent=agent,
            successor_agent=successor_agent,
            memory_version=header["memory_version"],
            records_transferred=import_result.total_records,
            integrity_hash=import_result.committed_root,
            transfer_date=transfer_date,
            status="VERIFIED" if import_result.verified else "UNVERIFIED",
            categories=tuple(header.get("categories", ())),
            seller_signature=header.get("signature") or "",
            seller_tenant_sealed_at=(
                getattr(seal_record, "sealed_at", "") if seal_record else ""
            ),
            settlement_reference=settlement_reference,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_asset": self.asset_id,
            "origin_agent": self.origin_agent,
            "successor_agent": self.successor_agent,
            "memory_version": self.memory_version,
            "records_transferred": self.records_transferred,
            "integrity_hash": self.integrity_hash,
            "categories_transferred": list(self.categories),
            "seller_signature": self.seller_signature,
            "seller_tenant_sealed_at": self.seller_tenant_sealed_at,
            "settlement_reference": self.settlement_reference,
            "transfer_date": self.transfer_date,
            "transfer_status": self.status,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2) + "\n"

    def to_text(self) -> str:
        rows = [
            ("Memory asset", self.asset_id),
            ("Origin agent", self.origin_agent),
            ("Successor agent", self.successor_agent),
            ("Memory version", str(self.memory_version)),
            ("Records transferred", f"{self.records_transferred:,}"),
            ("Categories", ", ".join(self.categories) or "all"),
            ("Integrity hash", _abbrev(self.integrity_hash)),
            ("Seller signature", _abbrev(self.seller_signature)),
        ]
        if self.seller_tenant_sealed_at:
            rows.append(("Origin tenant sealed", self.seller_tenant_sealed_at))
        if self.settlement_reference:
            rows.append(("Settlement", _abbrev(self.settlement_reference)))
        rows.extend(
            [("Transfer date", self.transfer_date), ("Transfer status", self.status)]
        )

        width = max(len(label) for label, _ in rows)
        body = "\n".join(f"{label.ljust(width)}   {value}" for label, value in rows)
        rule = "─" * (width + 3 + max(len(v) for _, v in rows))
        return f"SUCCESSION CERTIFICATE\n{rule}\n{body}\n{rule}\n"
