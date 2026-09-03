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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
