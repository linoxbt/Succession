"""An MCP server, so an agent can reach its own memory's property layer.

Succession is a protocol for what happens to agent memory. It followed that an
agent should be able to drive it, not only a human at a terminal: inspect what
it holds, see what is sellable and what consent withholds, price it, verify a
package it was handed, and prove a transfer would carry every category intact.

**On the three tools that are not read-only.** `list`, `fulfil` and `claim`
spend money, release a decryption key, or permanently seal an agent. Sealing in
particular has no undo — that is a deliberate property of the protocol, not an
omission — so these refuse unless `SUCCESSION_MCP_ALLOW_WRITES=1` is set, and
they say so rather than failing obscurely. One environment variable turns them
on for an operator who means it. The gate is not security: anyone who can set
the variable could also run the CLI. It is there so an agent exploring its
tools cannot seal its own memory by accident.

Every tool returns structured data rather than the CLI's printed text, because
the caller here is a program.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

__all__ = ["build_server", "main", "writes_allowed"]

WRITE_GATE = "SUCCESSION_MCP_ALLOW_WRITES"

REFUSAL = (
    "This tool moves money, releases a decryption key, or permanently seals an "
    f"agent, and is disabled. Set {WRITE_GATE}=1 to enable it. Sealing has no "
    "undo: once a succession settles, the origin agent's writes are closed for "
    "good."
)


def writes_allowed() -> bool:
    return os.environ.get(WRITE_GATE, "").strip() in {"1", "true", "yes"}


def _open(db: str, tenant: str) -> Any:
    from ..memory.sibyl import open_tenant

    return open_tenant(Path(db).expanduser(), tenant)


def build_server() -> MCPServer:
    server = MCPServer(
        name="succession",
        version="0.2.0",
        instructions=(
            "The property layer for agent memory. Inspect what an agent holds, "
            "what of it may be sold, what it is worth, and whether a transfer "
            "would carry every category intact. Reading and verifying are "
            "always available; listing, fulfilling and claiming move money or "
            "seal an agent permanently and are disabled unless the operator "
            f"has set {WRITE_GATE}=1."
        ),
    )

    # --- what an agent holds --------------------------------------------

    @server.tool(
        description=(
            "What this agent actually has to sell, per SMP directory: how much "
            "is transferable, how much the seller withheld, and how much a "
            "counterparty never consented to move. The last of those cannot be "
            "sold at any price."
        )
    )
    def inventory(db: str, tenant: str) -> dict[str, Any]:
        from ..scope import take_inventory

        found = take_inventory(_open(db, tenant))
        return {
            "categories": {name: entry.to_dict() for name, entry in found.items()},
            "sellable_total": sum(e.sellable for e in found.values()),
            "withheld_without_consent": sum(
                e.withheld_without_consent for e in found.values()
            ),
        }

    @server.tool(
        description=(
            "The pre-purchase data room: aggregate counts, tenure, memory size "
            "and per-directory transferability. Never record bodies, which are "
            "released only after purchase and hash verification."
        )
    )
    def preview(db: str, tenant: str, agent: str) -> dict[str, Any]:
        from ..dataroom import build_preview

        return build_preview(_open(db, tenant), agent_identity=agent).to_dict()

    @server.tool(
        description=(
            "The reference valuation, with every factor's inputs, multiplier and "
            "explanation, so the figure can be recomputed by hand rather than "
            "taken on trust."
        )
    )
    def value(db: str, tenant: str) -> dict[str, Any]:
        from ..valuation import value_tenant

        return value_tenant(_open(db, tenant)).to_dict()

    # --- verification ----------------------------------------------------

    @server.tool(
        description=(
            "Prove, against this agent's own store, that a sale would carry "
            "every selected directory intact. Exports, imports into a throwaway "
            "store, re-exports, and compares Merkle subroots. Touches no chain "
            "and spends nothing. `scope` takes percentages, e.g. "
            "'relationships=60,history=100'."
        )
    )
    def prove(
        db: str, tenant: str, agent: str, private_key: str, scope: str | None = None
    ) -> dict[str, Any]:
        from ..export import export_tenant
        from ..importer import import_package
        from ..smp import DATA_CATEGORIES
        from eth_account import Account

        parsed = None
        if scope:
            from ..scope import SaleScope

            parsed = SaleScope.from_percentages(
                {
                    part.split("=")[0].strip(): int(part.split("=")[1])
                    for part in scope.split(",")
                    if "=" in part
                }
            )

        source = _open(db, tenant)
        exported = export_tenant(
            source, agent_identity=agent, private_key=private_key, scope=parsed
        )
        with tempfile.TemporaryDirectory() as tmp:
            sink = _open(str(Path(tmp) / "buyer.db"), "mcp-prove-buyer")
            import_package(
                exported.package, sink,
                committed_root=exported.root_hex,
                expected_signer=Account.from_key(private_key).address,
            )
            back = export_tenant(sink, agent_identity=agent, private_key=private_key)

        def roots(package: Any) -> dict[str, Any]:
            return {
                e["category"]: (e["subroot"], e["leaf_count"])
                for e in (package.integrity or {}).get("categories", [])
            }

        sent, landed = roots(exported.package), roots(back.package)
        selected = tuple(parsed.categories) if parsed else DATA_CATEGORIES
        per_category = {
            c: {
                "sent": sent.get(c, ("", 0))[1],
                "landed": landed.get(c, ("", 0))[1],
                "subroot_identical": sent.get(c) == landed.get(c) and c in sent,
            }
            for c in selected
        }
        return {
            "committed_root": exported.root_hex,
            "categories": per_category,
            "all_intact": all(v["subroot_identical"] for v in per_category.values()),
        }

    @server.tool(
        description=(
            "Check every claim Succession makes about itself, against a memory "
            "the check builds itself. Needs no store, no chain and no network "
            "unless `marketplace` is given, which additionally compares every "
            "published Merkle root to its on-chain commitment."
        )
    )
    def audit(marketplace: str | None = None) -> dict[str, Any]:
        from ..audit import run_audit

        results = run_audit(marketplace=marketplace)
        return {
            "checks": [r.to_dict() for r in results],
            "passed": sum(1 for r in results if r.status == "passed"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "skipped": sum(1 for r in results if r.status == "skipped"),
        }

    # --- the market ------------------------------------------------------

    @server.tool(
        description=(
            "Listings on a marketplace, read from the contract. Demonstration "
            "rows are returned separately and are never counted in any figure."
        )
    )
    def marketplace_listings(marketplace: str) -> dict[str, Any]:
        from ..marketplace import MarketplaceError, get

        try:
            body = get(marketplace, "/api/marketplace")
        except MarketplaceError as exc:
            return {"error": str(exc)}
        return {
            "listings": body.get("listings", []),
            "demo_listings": body.get("demo_listings", []),
            "chain": body.get("chain", False),
        }

    @server.tool(
        description=(
            "What has happened on the contract: listings, escrow, settlements, "
            "refunds, cancellations and seals, newest first, each with its "
            "transaction."
        )
    )
    def activity(marketplace: str, limit: int = 50) -> dict[str, Any]:
        from ..marketplace import MarketplaceError, get

        try:
            return get(marketplace, f"/api/activity?limit={limit}")
        except MarketplaceError as exc:
            return {"error": str(exc)}

    # --- the transacting three -------------------------------------------

    @server.tool(
        description=(
            "Sell this agent's memory: export, hash, encrypt, commit the root on "
            "Base and publish to a marketplace. IRREVERSIBLE once settled — the "
            "origin agent is sealed permanently. Disabled unless "
            f"{WRITE_GATE}=1."
        )
    )
    def list_for_sale(
        db: str, tenant: str, agent: str, price: int,
        private_key: str, marketplace: str, scope: str | None = None,
    ) -> dict[str, Any]:
        if not writes_allowed():
            return {"refused": REFUSAL}
        from .. import cli

        argv = [
            "list", "--db", db, "--tenant", tenant, "--agent", agent,
            "--price", str(price), "--marketplace", marketplace,
        ]
        if scope:
            argv += ["--scope", scope]
        os.environ["SUCCESSION_SIGNING_KEY"] = private_key
        return {"exit_code": cli.main(argv)}

    @server.tool(
        description=(
            "Release content keys for listings whose escrow has landed on chain. "
            f"Hands a decryption key to a buyer. Disabled unless {WRITE_GATE}=1."
        )
    )
    def fulfil(
        private_key: str, marketplace: str, listing: str | None = None
    ) -> dict[str, Any]:
        if not writes_allowed():
            return {"refused": REFUSAL}
        from .. import cli

        argv = ["fulfil", "--once", "--marketplace", marketplace]
        if listing:
            argv += ["--listing", listing]
        os.environ["SUCCESSION_SIGNING_KEY"] = private_key
        return {"exit_code": cli.main(argv)}

    @server.tool(
        description=(
            "Collect memory you funded escrow for, import it into your own "
            "store, and re-derive the root from what landed. Writes into the "
            f"destination tenant. Disabled unless {WRITE_GATE}=1."
        )
    )
    def claim(
        db: str, tenant: str, listing: str, marketplace: str
    ) -> dict[str, Any]:
        if not writes_allowed():
            return {"refused": REFUSAL}
        from .. import cli

        return {
            "exit_code": cli.main([
                "claim", "--db", db, "--tenant", tenant,
                "--listing", listing, "--marketplace", marketplace,
            ])
        }

    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
