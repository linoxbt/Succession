"""Command-line entry points.

The pieces a real seller or buyer needs outside the UI: build and inspect a
package, verify one, and import it. Keys come from the environment, never from
an argument — a private key on a command line lands in shell history and in the
process table.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .dataroom import build_preview
from .export import export_tenant
from .importer import import_package, verify_package
from .memory.sibyl import open_tenant
from .merkle import to_hex
from .smp import DATA_CATEGORIES, SMPPackage
from .valuation import value_tenant

KEY_ENV = "SUCCESSION_SIGNING_KEY"


def _require_key() -> str:
    key = os.environ.get(KEY_ENV)
    if not key:
        raise SystemExit(
            f"set {KEY_ENV} to the private key holding the agent's ERC-8004 "
            "identity (it is read from the environment so it does not land in "
            "shell history)"
        )
    return key


def cmd_export(args: argparse.Namespace) -> int:
    source = open_tenant(args.db, args.tenant)
    result = export_tenant(
        source,
        agent_identity=args.agent,
        private_key=_require_key(),
        categories=args.categories or None,
    )
    result.package.write_dir(args.out)
    print(f"wrote {result.record_count} records to {args.out}")
    print(f"integrity root: {result.root_hex}")
    print(f"withheld non-transferable: {result.redaction.withheld_non_transferable}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    package = SMPPackage.read_dir(args.package)
    tree = package.tree()
    print(json.dumps({
        "header": package.header,
        "recomputed_root": to_hex(tree.root),
        "matches_header": to_hex(tree.root) == package.header.get("integrity_root"),
        "categories": {c: len(v) for c, v in sorted(package.data.items())},
        "permissions": package.permissions,
    }, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    package = SMPPackage.read_dir(args.package)
    try:
        signer = verify_package(
            package, committed_root=args.root, expected_signer=args.signer
        )
    except Exception as exc:  # noqa: BLE001 - the message is the whole output
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"OK — content and signature verify; signed by {signer}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    package = SMPPackage.read_dir(args.package)
    sink = open_tenant(args.db, args.tenant)
    try:
        result = import_package(
            package, sink, committed_root=args.root, expected_signer=args.signer
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"imported {result.total_records} records into {result.tenant_id}")
    print(f"re-derived root: {result.reimported_root}")
    print("VERIFIED" if result.verified else "UNVERIFIED")
    return 0 if result.verified else 1


def cmd_value(args: argparse.Namespace) -> int:
    source = open_tenant(args.db, args.tenant)
    print(json.dumps(value_tenant(source).to_dict(), indent=2))
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    source = open_tenant(args.db, args.tenant)
    preview = build_preview(source, agent_identity=args.agent)
    print(json.dumps(preview.to_dict(), indent=2))
    return 0


def _chain_backend(args: argparse.Namespace, key: str):
    """A settlement backend against the deployed contract.

    Deliberately has no local fallback. ``LocalSettlement`` mirrors the
    contract's state machine well enough that a seller could list against it and
    see every screen say "listed" while nothing had touched a chain — which is
    precisely the failure this project exists to make impossible. If there is no
    deployment record, listing stops.
    """
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware

    from .chain import ChainSettlement

    record_path = Path(
        args.deployment
        or os.environ.get("SUCCESSION_DEPLOYMENT")
        or Path(__file__).resolve().parents[4] / "deployments" / "base-sepolia.json"
    )
    if not record_path.is_file():
        raise SystemExit(
            f"no deployment record at {record_path}. Listing settles on chain and "
            "there is no offline mode for it — deploy first with\n"
            "  python scripts/deploy_base_sepolia.py"
        )
    record = json.loads(record_path.read_text("utf-8"))

    rpc = os.environ.get("BASE_SEPOLIA_RPC_URL")
    if not rpc:
        raise SystemExit("set BASE_SEPOLIA_RPC_URL to reach the chain")
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if not w3.is_connected():
        raise SystemExit(f"cannot reach {rpc}")

    backend = ChainSettlement(
        w3, contract_address=record["listing_contract"], seller_key=key
    )
    return backend, record


def cmd_list(args: argparse.Namespace) -> int:
    """List your own agent's memory for sale, on chain."""
    from .publish import PublishError, publish_listing

    key = _require_key()
    memory = open_tenant(args.db, args.tenant)
    backend, record = _chain_backend(args, key)

    try:
        stored, asset = publish_listing(
            memory,
            backend,
            agent_identity=args.agent,
            private_key=key,
            price=args.price,
            chain_id=int(record["chain_id"]),
            listing_contract=record["listing_contract"],
            categories=args.categories,
        )
    except PublishError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"listed  {stored.listing_id}")
    print(f"  agent           {stored.agent_identity}")
    print(f"  committed root  {stored.committed_root}")
    print(f"  price           {stored.price} ({stored.currency} minor units)")
    print(f"  categories      {', '.join(stored.categories)}")
    print(f"  records         {sum(asset.preview.to_dict()['counts'].values())}")
    print(f"  contract        {stored.listing_contract}")
    print()
    print("The encrypted package and its key are in your vault. The key is")
    print("released only when you see escrow funded on chain:")
    print(f"  succession fulfil --listing {stored.listing_id}")
    return 0


def cmd_fulfil(args: argparse.Namespace) -> int:
    """Release content keys for listings whose escrow has landed."""
    from .fulfil import watch

    key = _require_key()
    backend, _ = _chain_backend(args, key)
    results = watch(
        backend,
        interval=args.interval,
        once=args.once,
        listings=[args.listing] if args.listing else None,
    )
    return 0 if results or args.once else 0


def cmd_claim(args: argparse.Namespace) -> int:
    """Buyer side: collect the package you paid for, import it, re-hash it.

    The import happens here rather than in the browser for the same reason
    listing does — a Sibyl store is a local file, and the buyer's is on the
    buyer's machine. Re-hashing the *destination* is the step that makes the
    purchase checkable: it proves the importer wrote what it received and the
    engine coerced nothing on the way in.
    """
    import urllib.request

    from .envelope import SealedEnvelope, open_envelope
    from .importer import import_package

    def _get(path: str) -> dict:
        with urllib.request.urlopen(
            f"{args.marketplace.rstrip('/')}{path}", timeout=30
        ) as response:
            return json.load(response)

    backend, _ = _chain_backend(args, os.environ.get(KEY_ENV, "0x" + "11" * 32))
    listing = backend.get(args.listing)

    envelope = SealedEnvelope.from_dict(_get(f"/api/listing/{args.listing}/envelope"))
    key = bytes.fromhex(_get(f"/api/listing/{args.listing}/key")["content_key"])
    package = open_envelope(envelope, key)

    sink = open_tenant(args.db, args.tenant)
    result = import_package(
        package,
        sink,
        committed_root=listing.hash_commitment,
        expected_signer=listing.seller,
    )
    print(f"imported {result.total_records} records into {result.tenant_id}")
    print(f"  committed root  {listing.hash_commitment}")
    print(f"  re-derived root {result.reimported_root}")
    print(f"  {'VERIFIED' if result.verified else 'MISMATCH'}")
    if not result.verified:
        print()
        print("Do not confirm on chain. Submitting this root refunds you and the")
        print("sale is abandoned, which is the correct outcome for a bad delivery.")
        return 1
    print()
    print("Confirm on chain to release payment and take the identity:")
    print(f"  the root above, submitted to confirmTransfer({args.listing}, ...)")
    return 0



def cmd_prove(args: argparse.Namespace) -> int:
    """Prove, against your own store, that all six categories actually transfer.

    Runs a complete sale into a throwaway buyer store and compares the result
    category by category. Nothing is listed, nothing is sold, no chain is
    touched and no key is spent: this is the pipeline run end to end so you can
    see what would land, before you trust it with the real thing.

    The comparison is against the *buyer's re-export*, not against the bytes
    sent. Checking what was sent only proves the courier was honest.
    """
    import tempfile

    from .importer import import_package
    from .smp import DATA_CATEGORIES

    key = _require_key()
    source = open_tenant(args.db, args.tenant)
    export = export_tenant(
        source,
        agent_identity=args.agent,
        private_key=key,
        categories=args.categories or None,
    )

    from eth_account import Account

    signer = Account.from_key(key).address

    with tempfile.TemporaryDirectory() as tmp:
        # A separate file, not a second tenant in the same one. Two tenants in
        # one database would pass this and fail a real two-machine transfer.
        sink = open_tenant(Path(tmp) / "buyer.db", "prove-buyer")
        result = import_package(
            export.package,
            sink,
            committed_root=export.root_hex,
            expected_signer=signer,
        )
        back = export_tenant(
            sink,
            agent_identity=args.agent,
            private_key=key,
            categories=args.categories or None,
        )

    def subroots(package):
        return {
            e["category"]: (e["subroot"], e["leaf_count"])
            for e in (package.integrity or {}).get("categories", [])
        }

    sent, landed = subroots(export.package), subroots(back.package)
    selected = tuple(args.categories) if args.categories else DATA_CATEGORIES

    print(f"committed   {export.root_hex}")
    print(f"re-derived  {result.reimported_root}")
    print(f"verified    {'YES' if result.verified else 'NO'}")
    print()
    print(f"{'category':22}{'sent':>7}{'landed':>8}   subroot")
    failures = []
    for category in selected:
        a, b = sent.get(category), landed.get(category)
        if a is None:
            failures.append(f"{category}: nothing exported")
            print(f"{category:22}{0:>7}{0:>8}   EMPTY")
            continue
        same = a == b
        if not same:
            failures.append(f"{category}: subroot changed in transit")
        print(
            f"{category:22}{a[1]:>7}{(b[1] if b else 0):>8}   "
            f"{'identical' if same else 'CHANGED'}"
        )

    print()
    if failures or not result.verified:
        for line in failures:
            print(f"  {line}")
        print("NOT every category transferred intact.")
        return 1
    print(f"All {len(selected)} categories transferred intact.")
    return 0


def cmd_listings(args: argparse.Namespace) -> int:
    """What this seller has listed, from their own vault."""
    from .publish import SellerVault

    rows = SellerVault().all()
    if not rows:
        print("no listings in your vault")
        return 0
    for row in rows:
        print(f"{row.listing_id}  {row.agent_identity}  {row.price} {row.currency}")
        print(f"  root {row.committed_root}  chain {row.chain_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="succession")
    sub = parser.add_subparsers(dest="command", required=True)

    def tenant_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--db", type=Path, required=True, help="Sibyl store path")
        p.add_argument("--tenant", required=True, help="tenant id")

    p = sub.add_parser("export", help="build and sign an SMP package")
    tenant_args(p)
    p.add_argument("--agent", required=True, help="ERC-8004 identity, e.g. erc8004:84532:0417")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--categories", nargs="*", choices=DATA_CATEGORIES,
                   help="partial succession: transfer only these")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("inspect", help="describe a package without importing it")
    p.add_argument("package", type=Path)
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("verify", help="check a package against a commitment")
    p.add_argument("package", type=Path)
    p.add_argument("--root", required=True, help="the root committed on-chain")
    p.add_argument("--signer", required=True, help="the seller's address")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("import", help="import a package into a fresh tenant")
    p.add_argument("package", type=Path)
    tenant_args(p)
    p.add_argument("--root", required=True)
    p.add_argument("--signer", required=True)
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("value", help="compute the reference valuation")
    tenant_args(p)
    p.set_defaults(func=cmd_value)

    p = sub.add_parser("preview", help="compute the data-room preview")
    tenant_args(p)
    p.add_argument("--agent", required=True)
    p.set_defaults(func=cmd_preview)

    def deployment_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--deployment",
            type=Path,
            default=None,
            help="path to the deployment record (default: deployments/base-sepolia.json)",
        )

    p = sub.add_parser("list", help="list your agent's memory for sale, on chain")
    tenant_args(p)
    deployment_arg(p)
    p.add_argument("--agent", required=True,
                   help="the ERC-8004 identity you hold, e.g. erc8004:84532:417")
    p.add_argument("--price", type=int, required=True,
                   help="asking price in the payment token's minor units (USDC has 6)")
    p.add_argument("--categories", nargs="*", choices=DATA_CATEGORIES,
                   help="partial succession: sell only these")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("fulfil", help="release content keys once escrow is funded")
    deployment_arg(p)
    p.add_argument("--listing", default=None, help="just this one (default: all)")
    p.add_argument("--interval", type=int, default=30, help="seconds between polls")
    p.add_argument("--once", action="store_true", help="check once and exit")
    p.set_defaults(func=cmd_fulfil)

    p = sub.add_parser("claim", help="collect, import and verify memory you bought")
    tenant_args(p)
    deployment_arg(p)
    p.add_argument("--listing", required=True, help="the listing you funded escrow on")
    p.add_argument("--marketplace", default=os.environ.get(
        "SUCCESSION_MARKETPLACE", "http://127.0.0.1:8000"
    ), help="marketplace base URL")
    p.set_defaults(func=cmd_claim)

    p = sub.add_parser(
        "prove", help="prove every category transfers, against your own store"
    )
    tenant_args(p)
    p.add_argument("--agent", required=True)
    p.add_argument("--categories", nargs="*", choices=DATA_CATEGORIES,
                   help="check only these (default: all six)")
    p.set_defaults(func=cmd_prove)

    p = sub.add_parser("listings", help="what you have listed")
    p.set_defaults(func=cmd_listings)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
