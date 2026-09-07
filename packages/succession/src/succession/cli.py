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
from typing import Any

from .dataroom import build_preview
from .export import export_tenant
from .importer import import_package, verify_package
from .memory.sibyl import open_tenant
from .merkle import to_hex
from .smp import DATA_CATEGORIES, SMPPackage
from .valuation import value_tenant

KEY_ENV = "SUCCESSION_SIGNING_KEY"
#: The buyer signs with a different wallet to the seller, and conflating them
#: is how someone accidentally tries to buy their own listing.
BUYER_KEY_ENV = "SUCCESSION_BUYER_KEY"


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
    matches = to_hex(tree.root) == package.header.get("integrity_root")
    print(json.dumps({
        "header": package.header,
        "recomputed_root": to_hex(tree.root),
        "matches_header": matches,
        "categories": {c: len(v) for c, v in sorted(package.data.items())},
        "permissions": package.permissions,
    }, indent=2))
    # A package whose recomputed root disagrees with its own header is broken,
    # and used to exit 0 while saying so in JSON nobody scripts against.
    return 0 if matches else 1


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

    # Same ordering as the ABI lookup, and for the same reason: `parents[4]` is
    # the repo root from a checkout and the virtualenv root from an installed
    # package, so an installed CLI could never find a deployment record either.
    here = Path(__file__).resolve()
    candidates = [
        Path(args.deployment) if args.deployment else None,
        Path(os.environ["SUCCESSION_DEPLOYMENT"])
        if os.environ.get("SUCCESSION_DEPLOYMENT") else None,
        here.parents[4] / "deployments" / "base-sepolia.json",
        here.parent / "data" / "base-sepolia.json",
    ]
    record_path = next(
        (c for c in candidates if c is not None and c.is_file()),
        Path(args.deployment or "deployments/base-sepolia.json"),
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
        w3,
        contract_address=record["listing_contract"],
        seller_key=key,
        artifacts_path=getattr(args, "artifacts", None),
    )
    return backend, record


def cmd_list(args: argparse.Namespace) -> int:
    """List your own agent's memory for sale, on chain."""
    from .marketplace import MarketplaceError, publish_metadata
    from .publish import PublishError, publish_listing

    key = _require_key()

    # `--categories` with no values parses to an empty list, which used to mean
    # "sell nothing" and committed the empty-set sentinel root on chain. The
    # other handlers coerce it to None, meaning everything; this one did not.
    categories = args.categories or None
    scope = _parse_scope(getattr(args, "scope", None))
    if categories and scope is not None:
        # `build_package` silently prefers scope, so accepting both meant one
        # of the seller's two instructions was discarded without a word.
        raise SystemExit(
            "pass --categories or --scope, not both. --scope already names "
            "the categories it sells, with a percentage for each."
        )

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
            categories=categories,
            scope=scope,
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

    # Publish what the contract has no field for, and the ciphertext with it.
    # `claim` fetches the envelope before the key, so a listing whose envelope
    # never left the vault gives a paying buyer a 404 and nothing to decrypt.
    # The key is deliberately not sent here: it goes only once escrow is funded.
    try:
        package = getattr(asset.export, "package", None)
        publish_metadata(
            args.marketplace,
            stored,
            envelope=asset.envelope,
            preview=asset.preview.to_dict(),
            integrity=getattr(package, "integrity", None),
            provenance=getattr(package, "header", None),
            private_key=key,
        )
    except MarketplaceError as exc:
        print()
        print(f"listed on chain, but the marketplace did not accept it: {exc}")
        print("The commitment stands and the vault holds the package, so")
        print("nothing is lost. Publish it when the marketplace is reachable:")
        print(f"  succession publish --listing {stored.listing_id}")
        return 1

    print(f"  published to    {args.marketplace.rstrip('/')}")
    print()
    print("The key stays in your vault until you see escrow funded on chain:")
    print(f"  succession fulfil --listing {stored.listing_id}")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    """Publish a listing you already made on chain to a marketplace.

    The recovery path, and the only one there is. `succession list` commits the
    root and publishes in one go, but the commitment is the irreversible half:
    if the marketplace was unreachable at that moment, re-running `list` would
    try to list the same agent again and the contract would refuse it. So the
    publish half has to be separately callable.

    Everything it sends comes out of the seller's own vault, so this works days
    later, from the same machine, with no re-export and no new signature over
    the memory.
    """
    from .marketplace import MarketplaceError, publish_metadata
    from .publish import PublishError, SellerVault

    key = _require_key()
    vault = SellerVault(args.vault) if getattr(args, "vault", None) else SellerVault()

    try:
        stored = vault.read(args.listing)
        envelope = vault.envelope(args.listing)
    except PublishError as exc:
        raise SystemExit(str(exc)) from exc

    integrity, provenance = vault.proofs(args.listing)
    try:
        publish_metadata(
            args.marketplace,
            stored,
            envelope=envelope,
            integrity=integrity or None,
            provenance=provenance or None,
            private_key=key,
        )
    except MarketplaceError as exc:
        print(f"could not publish {args.listing}: {exc}", file=sys.stderr)
        return 1

    print(f"published {args.listing} to {args.marketplace.rstrip('/')}")
    print(f"  committed root  {stored.committed_root}")
    print(f"  proofs          {'yes' if integrity else 'none in vault'}")
    print()
    print("The key still stays with you until escrow is funded:")
    print(f"  succession fulfil --listing {args.listing}")
    return 0


def cmd_fulfil(args: argparse.Namespace) -> int:
    """Release content keys for listings whose escrow has landed.

    The key has to actually go somewhere. `release_for` decides *whether* it may
    leave the vault, guarding on the chain's own state and on the commitment
    matching what was listed; this decides *how*, which is a POST to the
    marketplace the buyer will collect from. Keeping the two apart is what makes
    only the first one security-critical.

    Exit status is the seller's only signal here, so it reports delivery rather
    than intent. This command used to return 0 unconditionally — the expression
    was `0 if results or args.once else 0`, both branches identical — while
    `watch` caught the delivery failure and logged it. A seller could watch it
    say "key released", exit clean, and leave a paying buyer with nothing.
    """
    from .fulfil import DeliveryError, watch
    from .marketplace import MarketplaceError, deliver_key

    key = _require_key()
    backend, _ = _chain_backend(args, key)
    base = args.marketplace.rstrip("/")
    failures: list[str] = []

    def deliver(stored: Any, content_key: bytes, buyer: str) -> None:
        try:
            deliver_key(base, stored.listing_id, content_key, private_key=key)
        except MarketplaceError as exc:
            failures.append(f"{stored.listing_id}: {exc}")
            # Raised so `release_for` does not report a release that did not
            # happen, and so `watch` retries on the next poll. Nothing was
            # consumed: the key is still in the vault and the contract still
            # decides whether it may leave.
            raise DeliveryError(str(exc)) from exc

    print(f"delivering released keys to {base}")
    results = watch(
        backend,
        deliver=deliver,
        interval=args.interval,
        once=args.once,
        listings=[args.listing] if args.listing else None,
    )

    if failures:
        print()
        for failure in failures:
            print(f"  undelivered  {failure}")
        print("The buyer cannot claim until a key reaches the marketplace.")
        return 1
    if args.once and not results:
        # Nothing was ready. That is a true answer rather than a failure: no
        # buyer has funded escrow yet.
        return 0
    return 0


def _buyer_backend(args: argparse.Namespace, key: str):
    """A settlement backend that signs as the buyer rather than the seller.

    Every chain command until now signed as a seller, because the buyer's half
    lived in the browser. That left the terminal unable to finish a sale it
    could otherwise drive end to end, which is a strange place to stop for a
    product whose memory transfer is entirely terminal.
    """
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware

    from .chain import ChainSettlement

    record_path = _deployment_path(args)
    if record_path is None:
        raise SystemExit(
            "no deployment record found. Buying settles on chain and has no "
            "offline mode; pass --deployment or set SUCCESSION_DEPLOYMENT."
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
        w3,
        contract_address=record["listing_contract"],
        buyer_key=key,
        artifacts_path=getattr(args, "artifacts", None),
    )
    return backend, record


def cmd_market(args: argparse.Namespace) -> int:
    """What is for sale, read from a marketplace.

    The seller could always see their own listings with `succession listings`;
    a buyer had no way to see anyone else's without opening the web app. That
    made the terminal half of the product buyer-hostile for no reason, since
    the marketplace serves the same JSON either way.
    """
    from .marketplace import MarketplaceError, get

    try:
        body = get(args.marketplace, "/api/marketplace")
    except MarketplaceError as exc:
        raise SystemExit(f"could not read the marketplace: {exc}") from exc

    rows = body.get("listings", [])
    if args.state:
        rows = [r for r in rows if r["listing"]["state"] == args.state]

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    if not body.get("chain"):
        print("No contract is being read, so there is no live market.")
    if not rows:
        print("No listings match." if args.state else "No listings yet.")
        demo = body.get("demo_listings") or []
        if demo:
            print(f"({len(demo)} demonstration listings exist and are not for sale.)")
        return 0

    print(f"{len(rows)} listing{'' if len(rows) == 1 else 's'}")
    print()
    for row in rows:
        listing = row["listing"]
        preview = row.get("preview") or {}
        inventory = preview.get("inventory") or {}
        sellable = sum(int(v.get("sellable", 0)) for v in inventory.values())
        price = int(listing.get("price") or 0) / 1_000_000

        print(f"  {listing['listing_id']}   {listing['state']}")
        print(f"    agent    {row.get('agent_identity') or listing.get('agent_id')}")
        print(f"    price    {price:,.2f} {listing.get('currency', 'USDC')}")
        if sellable:
            print(f"    memory   {sellable:,} records across {len(inventory)} directories")
        elif not row.get("has_metadata"):
            print("    memory   on chain and undescribed; the seller published no data room")
        if row.get("integrity", {}).get("root"):
            agrees = (
                row["integrity"]["root"].lower()
                == listing["hash_commitment"].lower()
            )
            print(f"    proof    manifest {'matches' if agrees else 'DISAGREES WITH'} the chain")
        print()

    print("Inspect one before paying:")
    print(f"  succession show --listing {rows[0]['listing']['listing_id']}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """One listing's data room, in full, before any money moves."""
    from .marketplace import MarketplaceError, get

    try:
        row = get(args.marketplace, f"/api/listing/{args.listing}")
    except MarketplaceError as exc:
        raise SystemExit(f"could not read {args.listing}: {exc}") from exc

    if args.json:
        print(json.dumps(row, indent=2))
        return 0

    listing = row["listing"]
    preview = row.get("preview") or {}
    print(f"{args.listing}   {listing['state']}")
    print(f"  agent          {row.get('agent_identity') or listing.get('agent_id')}")
    print(f"  seller         {listing.get('seller')}")
    print(f"  price          {int(listing.get('price') or 0) / 1_000_000:,.2f} "
          f"{listing.get('currency', 'USDC')}")
    print(f"  committed root {listing.get('hash_commitment')}")

    inventory = preview.get("inventory") or {}
    if inventory:
        print()
        print("  What transfers")
        for name, entry in sorted(inventory.items()):
            withheld = int(entry.get("withheld_without_consent", 0))
            note = f", {withheld} withheld without consent" if withheld else ""
            print(f"    {name:<20} {entry.get('sellable', 0):>5} records{note}")

    valuation = preview.get("valuation") or {}
    if valuation:
        print()
        print(f"  Valuation      {valuation.get('amount')} {valuation.get('currency')}")
        for factor in valuation.get("factors", []):
            print(f"    x {factor['value']:<9} {factor['name']}")

    manifest = row.get("integrity") or {}
    if manifest.get("root"):
        agrees = manifest["root"].lower() == listing["hash_commitment"].lower()
        print()
        print(f"  Merkle root    {manifest['root']}")
        print(f"  {'matches' if agrees else 'DISAGREES WITH'} the commitment on chain")
    else:
        print()
        print("  No Merkle manifest published; the per-directory subroots cannot")
        print("  be checked before purchase. The commitment above still binds.")

    print()
    print("Fund escrow, which is the first irreversible step:")
    print(f"  succession buy --listing {args.listing}")
    return 0


def cmd_buy(args: argparse.Namespace) -> int:
    """Fund escrow from the terminal, approval included.

    Two transactions, and the command says so before sending either. The money
    is held by the contract, not paid: it reaches the seller only when a
    matching hash is confirmed, and returns to you if it is not or if the
    confirmation window expires.
    """
    from eth_account import Account

    from .settlement import SettlementError

    key = _require_buyer_key()
    backend, record = _buyer_backend(args, key)
    buyer = Account.from_key(key).address

    try:
        listing = backend.get(args.listing)
    except SettlementError as exc:
        raise SystemExit(str(exc)) from exc

    if listing.state.value != "open":
        raise SystemExit(
            f"{args.listing} is {listing.state.value}, not open. Only an open "
            "listing can be funded."
        )
    if listing.seller.lower() == buyer.lower():
        raise SystemExit("you are the seller of this listing; the contract refuses self-purchase")

    price = int(listing.price)
    print(f"listing {args.listing}")
    print(f"  seller  {listing.seller}")
    print(f"  price   {price / 1_000_000:,.2f} {listing.currency}")
    print(f"  buyer   {buyer}")
    print()

    if not args.yes:
        print("This sends two transactions: an ERC-20 approval, then buy().")
        print("Funding escrow is irreversible from your side; the money is")
        print("released to the seller on a matching hash, or returned to you.")
        print()
        print("Re-run with --yes to send them.")
        return 1

    token = record.get("payment_token")
    if not token:
        raise SystemExit("the deployment record names no payment token")

    print("approving the payment token…")
    tx = backend.approve_payment(token, buyer, price)
    print(f"  approved  {tx}")

    print("funding escrow…")
    try:
        listing = backend.buy(args.listing, buyer=buyer, amount=price)
    except SettlementError as exc:
        raise SystemExit(f"buy failed: {exc}") from exc

    print(f"  escrowed  {listing.escrow_balance / 1_000_000:,.2f} {listing.currency}")
    print()
    print("The seller releases the content key once they see this on chain.")
    print("Then collect and verify what you paid for:")
    print(f"  succession claim --listing {args.listing} --db <your store> --tenant <successor>")
    return 0


def cmd_confirm(args: argparse.Namespace) -> int:
    """Submit the root you re-derived, and settle or refund on it.

    This is the transaction that moves ownership. Submitting a root that does
    not match refunds you and abandons the sale, which is the correct outcome
    for a bad delivery and an expensive mistake to make on a good one, so the
    root is not defaulted and has to be passed.
    """
    from eth_account import Account

    from .settlement import SettlementError

    key = _require_buyer_key()
    backend, _record = _buyer_backend(args, key)
    buyer = Account.from_key(key).address

    listing = backend.get(args.listing)
    if listing.state.value != "escrowed":
        raise SystemExit(
            f"{args.listing} is {listing.state.value}; there is nothing escrowed "
            "to settle."
        )

    matches = args.root.lower() == listing.hash_commitment.lower()
    print(f"listing {args.listing}")
    print(f"  committed  {listing.hash_commitment}")
    print(f"  submitting {args.root}")
    print(f"  {'match' if matches else 'MISMATCH — this will refund you and abandon the sale'}")
    print()
    if not args.yes:
        print("Re-run with --yes to send it.")
        return 1

    try:
        receipt = backend.confirm_transfer(
            args.listing, delivered_hash=args.root, buyer_identity=buyer, caller=buyer
        )
    except SettlementError as exc:
        raise SystemExit(f"confirmTransfer failed: {exc}") from exc

    body = receipt.to_dict()
    print(f"  outcome    {body['outcome']}")
    print(f"  amount     {int(body['amount']) / 1_000_000:,.2f}")
    print(f"  reference  {body['reference']}")
    if body["outcome"] == "released":
        print()
        print("Paid, identity transferred, and the seller's copy sealed.")
    else:
        print()
        print("Refunded. The seller keeps their memory and you keep your money.")
    return 0


def _require_buyer_key() -> str:
    key = os.environ.get(BUYER_KEY_ENV)
    if not key:
        raise SystemExit(
            f"set {BUYER_KEY_ENV} to the private key of the wallet that will pay. "
            "It is read from the environment so it does not land in shell history "
            "or the process table."
        )
    return key


def cmd_claim(args: argparse.Namespace) -> int:
    """Buyer side: collect the package you paid for, import it, re-hash it.

    The import happens here rather than in the browser for the same reason
    listing does — a Sibyl store is a local file, and the buyer's is on the
    buyer's machine. Re-hashing the *destination* is the step that makes the
    purchase checkable: it proves the importer wrote what it received and the
    engine coerced nothing on the way in.

    Every failure below is caught and explained. `import_package` raises on a
    bad re-derivation rather than returning a result, so the guidance about not
    confirming on chain used to sit behind a condition that could never be true,
    and a buyer holding a corrupt package got a traceback instead of being told
    what to do about it. That guidance is the most important output this command
    has: confirming a mismatch is how a buyer loses their money.
    """
    from .envelope import SealedEnvelope, open_envelope
    from .importer import IntegrityMismatch, import_package
    from .marketplace import MarketplaceError, get

    backend, _ = _chain_backend(args, os.environ.get(KEY_ENV, "0x" + "11" * 32))
    listing = backend.get(args.listing)
    base = args.marketplace.rstrip("/")

    try:
        envelope = SealedEnvelope.from_dict(
            get(base, f"/api/listing/{args.listing}/envelope")
        )
        key = bytes.fromhex(get(base, f"/api/listing/{args.listing}/key")["content_key"])
    except MarketplaceError as exc:
        print(f"could not collect {args.listing}: {exc}", file=sys.stderr)
        if exc.status == 404:
            print(file=sys.stderr)
            print(
                "A 404 here means the seller has not published this part yet. "
                "The envelope is uploaded when they run `succession list`, and "
                "the key only once they have seen your escrow on chain with "
                "`succession fulfil`. Your funds are held by the contract "
                "either way, and are reclaimable after the confirmation "
                "window.",
                file=sys.stderr,
            )
        return 1

    package = open_envelope(envelope, key)
    sink = open_tenant(args.db, args.tenant)

    try:
        result = import_package(
            package,
            sink,
            committed_root=listing.hash_commitment,
            expected_signer=listing.seller,
        )
    except IntegrityMismatch as exc:
        print(f"the delivered memory does not match the commitment: {exc}")
        print()
        print("Do not confirm on chain. Submitting this root refunds you and the")
        print("sale is abandoned, which is the correct outcome for a bad delivery.")
        return 1

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


def cmd_inventory(args: argparse.Namespace) -> int:
    """What this agent actually has to sell, category by category.

    Read from the store rather than assumed from the category list, because an
    agent that has never written a preference cannot sell preferences and
    offering the category anyway produces a listing whose directory exports
    empty.
    """
    from .scope import take_inventory

    source = open_tenant(args.db, args.tenant)
    inventory = take_inventory(source)

    print(f"{'category':22}{'sellable':>9}{'withheld':>10}{'depth':>11}   offerable")
    for category, entry in inventory.items():
        withheld = entry.withheld_by_seller + entry.withheld_without_consent
        print(
            f"{category:22}{entry.sellable:>9}{withheld:>10}{entry.depth:>11}   "
            f"{'yes' if entry.offerable else 'NO — nothing to sell'}"
        )

    offerable = [c for c, e in inventory.items() if e.offerable]
    print()
    print(f"{len(offerable)} of {len(inventory)} categories can be offered.")
    if len(offerable) < len(inventory):
        print("An empty category cannot be listed: it would export an empty directory.")
    print()
    print("Sell a share of each with --scope, for example:")
    print(f"  succession list --scope {offerable[0] if offerable else 'history'}=60,history=100 …")
    return 0


def _parse_scope(raw: str | None):
    """``relationships=60,history=100`` into a SaleScope."""
    from .scope import SaleScope

    if not raw:
        return None
    percentages: dict[str, int] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise SystemExit(
                f"bad --scope entry {part!r}; expected category=percent, "
                "for example relationships=60"
            )
        category, _, percent = part.partition("=")
        try:
            value = int(percent)
        except ValueError:
            raise SystemExit(f"bad percent in --scope entry {part!r}") from None
        if not 0 <= value <= 100:
            raise SystemExit(f"--scope percent must be 0-100, got {value}")
        name = category.strip()
        # `--categories` gets this for free from argparse's `choices`; --scope
        # is a free-form string, so a typo used to travel all the way into
        # `SMPPackage.from_records` and surface as a traceback.
        if name not in DATA_CATEGORIES:
            raise SystemExit(
                f"unknown --scope category {name!r}; expected one of "
                f"{', '.join(DATA_CATEGORIES)}"
            )
        percentages[name] = value
    return SaleScope.from_percentages(percentages)


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
    scope = _parse_scope(getattr(args, "scope", None))
    if args.categories and scope is not None:
        raise SystemExit("pass --categories or --scope, not both")

    source = open_tenant(args.db, args.tenant)
    export = export_tenant(
        source,
        agent_identity=args.agent,
        private_key=key,
        categories=args.categories or None,
        scope=scope,
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
        # The buyer's store holds only what the scope selected, so re-exporting
        # it whole is right: applying the scope again would take a percentage of
        # a percentage and compare unequal sets.
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
    if args.categories:
        selected = tuple(args.categories)
    elif scope is not None:
        selected = tuple(scope.categories)
    else:
        selected = DATA_CATEGORIES

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


def cmd_status(args: argparse.Namespace) -> int:
    """What this installation is actually connected to, and what it is not.

    Four systems, and they connect in different ways that are easy to conflate:
    Sibyl through a local SQLite file, Base over JSON-RPC, the marketplace over
    HTTP, and Virtuals ACP over its own contracts. This prints the state of each
    rather than leaving someone to infer it from a failure three commands later.
    """
    from .memory.credentials import load_credentials

    print("Sibyl")
    creds = load_credentials()
    print(f"  {creds.describe()}")
    print("  memory is a local SQLite file; the SDK has no sync endpoint, so")
    print("  nothing about a store crosses the network in either direction.")
    if getattr(args, "db", None):
        store = Path(args.db).expanduser()
        if not store.is_file():
            print(f"  store {store} (absent)")
        else:
            print(f"  store {store}")
            health = open_tenant(store, args.tenant or "default").store_health()
            cap = health.get("capacity") or {}
            if cap:
                pct = float(cap.get("pct_used") or 0) * 100
                print(
                    f"  capacity  {cap.get('db_size_bytes', 0):,} of "
                    f"{cap.get('soft_cap_bytes', 0):,} bytes ({pct:.1f}%)"
                    + ("  AT OR ABOVE CAP" if cap.get("at_or_above_cap") else "")
                )
            if health.get("schema_version") is not None:
                print(f"  schema    v{health['schema_version']}")
            pending = health.get("pending_skill_proposals")
            if pending:
                print(
                    f"  {pending} skill proposal(s) unresolved — a buyer inherits "
                    "the decision you did not make"
                )
            elif pending is None:
                print("  skill proposals and linting are paid-tier features")

    print()
    print("Base")
    record_path = _deployment_path(args)
    if record_path is None:
        print("  no deployment record found; chain commands will stop rather than pretend")
    else:
        record = json.loads(record_path.read_text("utf-8"))
        print(f"  contract  {record.get('listing_contract')}")
        print(f"  registry  {record.get('identity_registry')} "
              f"({'real' if not record.get('identity_registry_is_mock') else 'mock'})")
        print(f"  chain id  {record.get('chain_id')}")
    rpc = os.environ.get("BASE_SEPOLIA_RPC_URL")
    print(f"  rpc       {rpc if rpc else 'BASE_SEPOLIA_RPC_URL is not set'}")

    print()
    print("Marketplace")
    print(f"  {args.marketplace}")
    from .marketplace import MarketplaceError, get

    try:
        chain = get(args.marketplace, "/api/chain")
        print(f"  reachable, mode {chain.get('mode')}")
    except MarketplaceError as exc:
        print(f"  unreachable: {exc}")

    print()
    print("Virtuals ACP")
    from .acp import LiveACP

    missing = [name for name in LiveACP.ENV if not os.environ.get(name)]
    if missing:
        print(f"  not connected; missing {', '.join(missing)}")
        print("  Registration needs a whitelisted wallet from Virtuals. Until then")
        print("  a listing carries no ACP history and task_performance scores from")
        print("  the journal instead, which the data room states rather than hides.")
    else:
        print("  credentials present; run `succession-acp status` to fetch")
    return 0


def _deployment_path(args: argparse.Namespace) -> Path | None:
    """The deployment record, by the same search the chain commands use."""
    here = Path(__file__).resolve()
    for candidate in (
        Path(args.deployment) if getattr(args, "deployment", None) else None,
        Path(os.environ["SUCCESSION_DEPLOYMENT"])
        if os.environ.get("SUCCESSION_DEPLOYMENT") else None,
        here.parents[4] / "deployments" / "base-sepolia.json",
        here.parent / "data" / "base-sepolia.json",
    ):
        if candidate is not None and candidate.is_file():
            return candidate
    return None


def cmd_audit(args: argparse.Namespace) -> int:
    """Check every claim this project makes, and exit non-zero if one fails.

    Runs against a memory it builds itself, so it needs no repository, no
    frontend, no wallet and no network. Pass --marketplace to additionally
    compare every published Merkle root against its on-chain commitment.
    """
    from .audit import run_audit

    results = run_audit(marketplace=getattr(args, "marketplace", None) if
                        getattr(args, "check_chain", False) else None)

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        mark = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}
        print("Succession, self-audit")
        print()
        for result in results:
            print(f"  [{mark.get(result.status, '????')}]  {result.name}")
            print(f"          {result.claim}")
            print(f"          {result.detail}")
            for key, value in result.evidence.items():
                print(f"            {key}: {value}")
            print()

    failed = [r for r in results if r.status == "failed"]
    skipped = [r for r in results if r.status == "skipped"]
    passed = [r for r in results if r.status == "passed"]
    if not args.json:
        print(f"{len(passed)} passed, {len(failed)} failed, {len(skipped)} skipped")
        if skipped:
            print("A skipped check is not a passed one.")
    return 1 if failed else 0


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


GUIDE = """succession — the property layer for agent memory

Start here
  succession status                  what this install is connected to
  succession audit                   check every claim this project makes

Selling, from your own machine
  succession inventory --db … --tenant …        what is sellable, per directory
  succession prove --db … --tenant … --agent …  prove a sale would carry it all
  succession list --db … --tenant … --agent … --price …   commit the root on Base
  succession fulfil                             release the key once escrow lands

Buying
  succession market                  what is for sale
  succession show --listing …        one listing's data room, before paying
  succession buy --listing …         fund escrow
  succession claim --listing … --db … --tenant …   collect, import, re-derive
  succession confirm --listing … --root …          settle on what you derived

Keys come from the environment, never from an argument:
  SUCCESSION_SIGNING_KEY   the seller's wallet
  SUCCESSION_BUYER_KEY     the buyer's wallet
  SUCCESSION_MARKETPLACE   which marketplace to publish to and read from
  BASE_SEPOLIA_RPC_URL     how to reach the chain

`succession <command> --help` for any one of them."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="succession",
        description="The property layer for agent memory.",
    )
    # A bare `succession` used to print a usage line and exit 2, which tells a
    # first-time reader the names of nineteen commands and nothing about which
    # one to run. Required=False plus the guide below is friendlier and costs
    # nothing, since every real invocation still routes through a subparser.
    sub = parser.add_subparsers(dest="command")

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
        artifacts_arg(p)

    def artifacts_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--artifacts",
            type=Path,
            default=None,
            help="contract ABI json (env: SUCCESSION_ARTIFACTS)",
        )

    def marketplace_arg(p: argparse.ArgumentParser) -> None:
        """Where the seller publishes and the buyer collects.

        The three commands that cross the network share one flag and one
        environment variable, because a sale where the seller published to one
        marketplace and the buyer read from another is a sale that silently
        does not complete.
        """
        p.add_argument(
            "--marketplace",
            default=os.environ.get(
                "SUCCESSION_MARKETPLACE", "http://127.0.0.1:8000"
            ),
            help="marketplace base URL (env: SUCCESSION_MARKETPLACE)",
        )

    p = sub.add_parser("list", help="list your agent's memory for sale, on chain")
    tenant_args(p)
    deployment_arg(p)
    marketplace_arg(p)
    p.add_argument("--agent", required=True,
                   help="the ERC-8004 identity you hold, e.g. erc8004:84532:417")
    p.add_argument("--price", type=int, required=True,
                   help="asking price in the payment token's minor units (USDC has 6)")
    p.add_argument("--categories", nargs="*", choices=DATA_CATEGORIES,
                   help="partial succession: sell only these, in whole")
    p.add_argument("--scope", default=None,
                   help="sell a share of each, e.g. relationships=60,history=100")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser(
        "publish", help="publish an already-listed agent to a marketplace"
    )
    deployment_arg(p)
    marketplace_arg(p)
    p.add_argument("--listing", required=True, help="the listing id to publish")
    p.add_argument("--vault", type=Path, default=None,
                   help="seller vault directory (env: SUCCESSION_VAULT)")
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("fulfil", help="release content keys once escrow is funded")
    deployment_arg(p)
    p.add_argument("--listing", default=None, help="just this one (default: all)")
    p.add_argument("--interval", type=int, default=30, help="seconds between polls")
    p.add_argument("--once", action="store_true", help="check once and exit")
    marketplace_arg(p)
    p.set_defaults(func=cmd_fulfil)

    p = sub.add_parser("claim", help="collect, import and verify memory you bought")
    tenant_args(p)
    deployment_arg(p)
    p.add_argument("--listing", required=True, help="the listing you funded escrow on")
    marketplace_arg(p)
    p.set_defaults(func=cmd_claim)

    p = sub.add_parser(
        "inventory", help="what this agent actually has to sell, per category"
    )
    tenant_args(p)
    p.set_defaults(func=cmd_inventory)

    p = sub.add_parser(
        "prove", help="prove every category transfers, against your own store"
    )
    tenant_args(p)
    p.add_argument("--agent", required=True)
    p.add_argument("--categories", nargs="*", choices=DATA_CATEGORIES,
                   help="check only these (default: all six)")
    # Without this, the shape the Sell page actually generates — a percentage
    # of each directory — could not be proved at all. `prove` could only ever
    # certify whole-category sales, which is not what most sellers list.
    p.add_argument("--scope", default=None,
                   help="prove a partial sale, e.g. relationships=60,history=100")
    p.set_defaults(func=cmd_prove)

    p = sub.add_parser("market", help="what is for sale")
    marketplace_arg(p)
    p.add_argument("--state", default=None,
                   choices=["open", "escrowed", "confirmed", "refunded"],
                   help="only listings in this state")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=cmd_market)

    p = sub.add_parser("show", help="one listing's data room, before paying")
    marketplace_arg(p)
    p.add_argument("--listing", required=True, help="the listing to inspect")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("buy", help="fund escrow for a listing")
    deployment_arg(p)
    p.add_argument("--listing", required=True, help="the listing to fund")
    p.add_argument("--yes", action="store_true",
                   help="send the transactions rather than describing them")
    p.set_defaults(func=cmd_buy)

    p = sub.add_parser("confirm", help="settle on the root you re-derived")
    deployment_arg(p)
    p.add_argument("--listing", required=True, help="the listing to settle")
    p.add_argument("--root", required=True,
                   help="the root succession claim re-derived from your own store")
    p.add_argument("--yes", action="store_true", help="send the transaction")
    p.set_defaults(func=cmd_confirm)

    p = sub.add_parser(
        "status", help="what this installation is connected to"
    )
    deployment_arg(p)
    marketplace_arg(p)
    p.add_argument("--db", type=Path, default=None, help="a store to report on")
    p.add_argument("--tenant", default=None, help="which tenant, with --db")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser(
        "audit", help="check every claim this project makes about itself"
    )
    marketplace_arg(p)
    p.add_argument("--check-chain", action="store_true",
                   help="also compare published roots to their on-chain commitments")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("listings", help="what you have listed")
    p.set_defaults(func=cmd_listings)

    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        print(GUIDE)
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
