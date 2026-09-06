"""The Succession marketplace service.

**The chain is the source of truth.** Who is selling, what they committed to,
the price, the state and the escrow all come from ``ListingContract``. This
service adds only what the contract has no field for and no business holding —
the data-room counts, the reference valuation, the agent's display name — and
every one of those rows is supplied by the address the contract records as that
listing's seller.

Nothing here is seeded. There is no demo tenant, no synthetic catalogue and no
reset route: a listing exists because a real seller ran ``succession list``
against their own Sibyl store and paid gas to commit its root. If the
marketplace is empty, that is the true answer.

Why sellers are not in the browser
----------------------------------

Sibyl 0.8.0 is local-only — ``MemoryClient.local(path)`` is its sole
constructor and the package makes no network calls beyond a tier check. A
seller's memory is a SQLite file on their own disk, so no web page can read it
and there is no Sibyl account to connect. Listing therefore happens in the
seller's own terminal, which is also the only arrangement in which "plaintext
never leaves the seller before escrow" is a fact rather than a promise.

The key never passes through this service unescrowed. The ciphertext does, and
that is safe: it is AES-256-GCM and inert without the key. The key arrives only
after the seller has independently seen escrow funded on chain, and is handed on
only after this service checks the same thing itself.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from secrets import compare_digest
from typing import Any

from eth_utils import to_checksum_address
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from succession.publish import recover_seller_auth
from succession.reputation import (
    LINEAGE_TARGET,
    MIN_RESOLVED,
    SPAN_TARGET_DAYS,
    W_CONTINUITY,
    W_EARNINGS,
    W_INTEGRITY,
    W_LINEAGE,
    W_SPAN,
)
from succession.settlement import ListingState, SettlementError
from succession.smp import DATA_CATEGORIES, GENERATED_CATEGORIES

from .demo import demo_rows, is_demo
from .registry import MetadataRegistry

WORKDIR = Path(os.environ.get("SUCCESSION_WORKDIR", "marketplace-state"))

#: Origins allowed to call this service cross-origin. A deployed frontend has to
#: name itself; a wildcard would let any page drive someone else's service.
ALLOWED_ORIGINS = tuple(
    o.strip()
    for o in os.environ.get(
        "SUCCESSION_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
)

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


def api_token() -> str:
    """Admin token, read per request so configuration can arrive after import."""
    return os.environ.get("SUCCESSION_API_TOKEN", "")


app = FastAPI(title="Succession", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_admin(request: Request) -> None:
    """Gate the few routes that are neither public reads nor seller-authenticated.

    Most writes here authenticate as the *seller of a specific listing*, by
    signature, which is stronger than any shared secret. This is only for
    operational routes that belong to whoever runs the service.
    """
    token = api_token()
    if token:
        header = request.headers.get("authorization", "")
        scheme, _, presented = header.partition(" ")
        if scheme.lower() != "bearer" or not compare_digest(presented, token):
            raise HTTPException(401, "a valid bearer token is required")
        return
    client = request.client.host if request.client else ""
    if client not in _LOOPBACK:
        raise HTTPException(
            403,
            "this service accepts admin writes from localhost only; set "
            "SUCCESSION_API_TOKEN to allow remote access",
        )


ADMIN = [Depends(require_admin)]


# --- state ---------------------------------------------------------------


class Store:
    """The service's own durable state: metadata, and keys held in transit."""

    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        self._registry: MetadataRegistry | None = None
        # Content keys a seller has released, keyed by listing id, held until
        # the buyer collects them. In memory on purpose: a key on disk outlives
        # the sale it belongs to, and this one is only useful for a few minutes
        # between the seller seeing escrow and the buyer importing.
        self.released: dict[str, str] = {}

    @property
    def registry(self) -> MetadataRegistry:
        if self._registry is None:
            self._registry = MetadataRegistry(self.workdir / "marketplace.db")
        return self._registry


STORE = Store(WORKDIR)


def _deployment() -> dict[str, Any] | None:
    """The deployment record, re-read per request.

    Deploying happens while the service is already running, so a value cached at
    import would keep reporting no chain until someone restarted it.
    """
    path = Path(
        os.environ.get(
            "SUCCESSION_DEPLOYMENT",
            Path(__file__).resolve().parents[1] / "deployments" / "base-sepolia.json",
        )
    )
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return None


def _chain():
    """A read-only settlement backend against the deployed contract.

    No signing keys: this service never sends a transaction. Buyers pay from
    their own wallet and sellers list from their own terminal, so the only thing
    it needs the chain for is to read what actually happened.
    """
    record = _deployment()
    if record is None:
        raise HTTPException(
            503,
            "no contract deployed; this marketplace reads listings from chain "
            "and has no offline mode",
        )
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware

    from succession.chain import ChainSettlement

    rpc = os.environ.get("BASE_SEPOLIA_RPC_URL")
    if not rpc:
        raise HTTPException(503, "BASE_SEPOLIA_RPC_URL is not set")
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return ChainSettlement(w3, contract_address=record["listing_contract"]), record


#: Overridable so tests can drive the identical routes against an in-process
#: EVM. Nothing else about the code path changes — same contract bytecode, same
#: reads — which is what makes the tests worth anything.
CHAIN_PROVIDER = _chain


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- models --------------------------------------------------------------


class ListingPost(BaseModel):
    """What a seller publishes about a listing they have already made on chain."""

    listing_id: str
    agent_identity: str
    committed_root: str
    chain_id: int
    contract: str
    name: str = ""
    vertical: str = ""
    valuation: str = ""
    preview: dict[str, Any] = {}
    envelope: dict[str, Any] | None = None
    # The Merkle manifest and the signed provenance header. Optional because a
    # listing published before these existed is still a valid listing; the UI
    # shows what is there and says so when they are absent.
    integrity: dict[str, Any] = {}
    provenance: dict[str, Any] = {}


class KeyPost(BaseModel):
    """A content key a seller is releasing against funded escrow."""

    content_key: str

    @field_validator("content_key")
    @classmethod
    def _must_be_hex(cls, value: str) -> str:
        raw = value[2:] if value.startswith("0x") else value
        try:
            if len(bytes.fromhex(raw)) != 32:
                raise ValueError
        except ValueError:
            raise ValueError("content key must be 32 bytes of hex") from None
        return raw


def _seller_of(listing_id: str):
    """Read a listing from chain, or say plainly that it is not there."""
    chain, record = CHAIN_PROVIDER()
    try:
        return chain.get(listing_id), chain, record
    except SettlementError as exc:
        raise HTTPException(404, f"no listing {listing_id!r} on chain: {exc}") from exc


def _authenticate_seller(request: Request, listing_id: str, on_chain) -> str:
    """Prove the caller is the address the *contract* records as this seller.

    Checked against the chain rather than against anything stored here, so this
    service cannot be talked into believing in a seller the contract does not
    know about.
    """
    signature = request.headers.get("x-succession-signature", "")
    if not signature:
        raise HTTPException(401, "X-Succession-Signature is required")
    try:
        recovered = recover_seller_auth(listing_id, signature)
    except Exception as exc:  # noqa: BLE001 - any malformed signature is a 401
        raise HTTPException(401, f"signature could not be recovered: {exc}") from exc
    if to_checksum_address(recovered) != to_checksum_address(on_chain.seller):
        raise HTTPException(
            403,
            f"{recovered} is not the seller of {listing_id}; the contract records "
            f"{on_chain.seller}",
        )
    return recovered


# --- routes --------------------------------------------------------------


@app.post("/api/listings")
def post_listing(body: ListingPost, request: Request) -> dict[str, Any]:
    """Publish the parts of a listing the chain does not carry.

    The listing must already exist on chain and the caller must be its seller.
    Both are checked here rather than trusted, so this table cannot describe a
    sale that was never committed to.
    """
    on_chain, _chain_backend, record = _seller_of(body.listing_id)
    _authenticate_seller(request, body.listing_id, on_chain)

    if on_chain.hash_commitment.lower() != body.committed_root.lower():
        raise HTTPException(
            409,
            f"the contract commits {body.listing_id} to {on_chain.hash_commitment}, "
            f"not {body.committed_root}",
        )

    STORE.registry.put(
        listing_id=body.listing_id,
        seller=to_checksum_address(on_chain.seller),
        agent_identity=body.agent_identity,
        committed_root=on_chain.hash_commitment,
        chain_id=int(record.get("chain_id", body.chain_id)),
        contract=record.get("listing_contract", body.contract),
        name=body.name,
        vertical=body.vertical,
        valuation=body.valuation,
        preview=body.preview,
        envelope=body.envelope,
        integrity=body.integrity,
        provenance=body.provenance,
        posted_at=_now(),
    )
    return {"listing_id": body.listing_id, "published": True}


@app.get("/api/marketplace")
def marketplace() -> dict[str, Any]:
    """Every listing the contract has emitted, enriched where metadata exists.

    The index is the chain, not this service's own table. That is a correction
    of a real gap: enumerating only what sellers had posted here meant a listing
    made on chain without that extra step was real, settled, and invisible, and
    the marketplace showed nothing while six listings existed.

    So `Listed` events decide what exists and the contract decides its state,
    price and seller. Metadata adds the counts, valuation and display name it
    has no field for. A listing with no metadata still appears, described by
    what the chain knows about it, because a real sale nobody can see is worse
    than a sparse row.
    """
    try:
        chain, _record = CHAIN_PROVIDER()
    except HTTPException:
        # No chain configured. An empty marketplace is the honest answer;
        # inventing rows to fill the screen is the pattern this project argues
        # against. The demo listings ride in their own field, never in this one.
        return {
            "listings": [],
            "count": 0,
            "chain": False,
            "demo_listings": demo_rows(),
        }

    # Discovery is the union of both sources, because neither is guaranteed
    # complete. The log scan is bounded and can miss an old listing; the
    # metadata table only holds what sellers chose to publish. Taking both and
    # validating every candidate against the contract below means a listing has
    # to be missing from *both* to disappear, and anything either one invents is
    # dropped when the chain does not confirm it.
    discovered: list[str] = []
    try:
        discovered = chain.listed_ids()
    except Exception:  # noqa: BLE001 - a refused scan degrades, it does not blank
        discovered = []

    seen = set(discovered)
    listing_ids = list(discovered)
    for row in STORE.registry.all():
        if row["listing_id"] not in seen:
            seen.add(row["listing_id"])
            listing_ids.append(row["listing_id"])

    rows = []
    for listing_id in listing_ids:
        try:
            on_chain = chain.get(listing_id)
        except SettlementError:
            continue
        meta = STORE.registry.get(listing_id) or {}
        rows.append(_row_of(on_chain, meta))

    # Demo listings travel in their own field rather than mixed into this one.
    # Sharing the array would make every consumer, every route and every test
    # responsible for remembering to filter, and the first one to forget would
    # report volume nobody paid. `listings` and `count` mean real listings, as
    # they always have.
    return {
        "listings": rows,
        "count": len(rows),
        "chain": True,
        "demo_listings": demo_rows(),
    }


def _row_of(on_chain: Any, meta: dict[str, Any]) -> dict[str, Any]:
    """One marketplace row: the chain for truth, the metadata table for the rest.

    Assembled here rather than inline because three routes return this shape and
    two of them used to disagree about it. `/api/listing/{id}` omitted
    `has_envelope` and `has_metadata` and returned an empty `agent_identity`
    where the marketplace fell back to the on-chain value, which made a detail
    page render less than the row that linked to it.
    """
    return {
        "listing": on_chain.to_dict(),
        "preview": meta.get("preview", {}),
        "name": meta.get("name", ""),
        "vertical": meta.get("vertical", ""),
        "valuation": meta.get("valuation", ""),
        # The chain knows the agent even when nobody published metadata, so a
        # bare listing still says whose memory it is.
        "agent_identity": meta.get("agent_identity") or on_chain.agent_id,
        "has_envelope": bool(meta.get("has_envelope")),
        "has_metadata": bool(meta),
        # The Merkle manifest and the signed provenance header, when the seller
        # published them. Neither carries a record body: the manifest is roots
        # and counts, the header is the ownership chain and its signature.
        "integrity": meta.get("integrity") or {},
        "provenance": meta.get("provenance") or {},
        # Stated on every row, not only on the demo ones. A field that is
        # present-or-absent invites `row.demo === undefined` to read as false in
        # one place and as missing in another.
        "demo": False,
    }


@app.get("/api/listing/{listing_id}")
def listing(listing_id: str) -> dict[str, Any]:
    """One listing, in exactly the shape the marketplace returns for it.

    A demo listing resolves here too. Without that, opening one by URL would
    404 while the same row rendered fine in the grid, and a demo listing has an
    address like any other now that listings are addressable.
    """
    if is_demo(listing_id):
        for row in demo_rows():
            if row["listing"]["listing_id"] == listing_id:
                return row
        raise HTTPException(404, f"no demo listing {listing_id}")

    on_chain, _chain, _record = _seller_of(listing_id)
    return _row_of(on_chain, STORE.registry.get(listing_id) or {})


@app.get("/api/listing/{listing_id}/envelope")
def envelope(listing_id: str) -> dict[str, Any]:
    """The encrypted package. Public on purpose.

    AES-256-GCM with the listing id and its commitment bound in as additional
    data. Without the content key it is noise, so serving it before payment
    costs nothing and saves the buyer waiting on the seller's connection for the
    bytes as well as the key.
    """
    blob = STORE.registry.envelope(listing_id)
    if blob is None:
        raise HTTPException(404, f"no envelope published for {listing_id!r}")
    return blob


@app.post("/api/listing/{listing_id}/key")
def release_key(listing_id: str, body: KeyPost, request: Request) -> dict[str, Any]:
    """A seller releases the content key. Escrow is re-checked here, not trusted.

    The seller has already satisfied themselves that escrow is funded — that is
    what ``succession fulfil`` does. This service checks the same thing again
    before accepting the key, because a service that stored a key on the
    seller's say-so would be a service that could be talked into storing it
    early.
    """
    on_chain, _chain, _record = _seller_of(listing_id)
    _authenticate_seller(request, listing_id, on_chain)

    if on_chain.state is not ListingState.ESCROWED:
        raise HTTPException(
            409,
            f"{listing_id} is {on_chain.state.value}; a key is only accepted "
            "against funded escrow",
        )
    STORE.released[listing_id] = body.content_key
    return {"listing_id": listing_id, "accepted": True, "buyer": on_chain.buyer}


@app.get("/api/listing/{listing_id}/key")
def collect_key(listing_id: str) -> dict[str, Any]:
    """The buyer collects the key, once the seller has released it.

    Escrow is checked again on the way out. The window in which this service
    holds a usable key is the gap between the seller releasing it and the buyer
    importing, and it is bounded on both sides by the chain.
    """
    on_chain, _chain, _record = _seller_of(listing_id)
    if on_chain.state is not ListingState.ESCROWED:
        raise HTTPException(
            409, f"{listing_id} is {on_chain.state.value}; no key is available"
        )
    key = STORE.released.get(listing_id)
    if key is None:
        raise HTTPException(
            404,
            "the seller has not released the key yet; they release it once they "
            "have seen escrow funded on chain",
        )
    return {"listing_id": listing_id, "content_key": key}


@app.delete("/api/listings/{listing_id}", dependencies=ADMIN)
def unpublish(listing_id: str) -> dict[str, Any]:
    """Drop a listing's metadata. The chain is unaffected — cancel there."""
    STORE.registry.delete(listing_id)
    STORE.released.pop(listing_id, None)
    return {"listing_id": listing_id, "unpublished": True}


@app.get("/api/agents/{owner}")
def agents_of(owner: str) -> dict[str, Any]:
    """Which ERC-8004 agents an address holds.

    A buyer usually has more than one, and the memory has to land in a specific
    successor, so the console asks them to pick rather than guessing. This is
    what populates that list.

    The registry is not `ERC721Enumerable`, so holdings are reconstructed from
    `Transfer` logs and confirmed against `ownerOf`. The result can therefore be
    incomplete on a wallet whose agents were minted long ago, and `complete`
    says so: a short list and an empty wallet are different answers and the UI
    must not conflate them.
    """
    record = _deployment()
    if record is None:
        raise HTTPException(503, "no contract deployed; there is no registry to read")
    try:
        checked = to_checksum_address(owner)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, f"not a valid address: {owner!r}") from exc

    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware

    from succession.erc8004 import IdentityRegistry

    rpc = os.environ.get("BASE_SEPOLIA_RPC_URL")
    if not rpc:
        raise HTTPException(503, "BASE_SEPOLIA_RPC_URL is not set")
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    registry = IdentityRegistry(w3, address=record["identity_registry"])
    try:
        return registry.agents_of(checked, lookback_blocks=60_000)
    except Exception as exc:  # noqa: BLE001 - an RPC failure is a 503, not a 500
        raise HTTPException(503, f"could not read the registry: {exc}") from exc


@app.get("/api/chain")
def chain_status() -> dict[str, Any]:
    """Which contract this marketplace is reading, if any.

    A deployment record is the only thing that puts this service on chain. There
    is deliberately no flag for it, because a flag is something that can be set
    wrongly, and a marketplace that reported settled sales against no chain at
    all would be the one dishonest thing available here.
    """
    record = _deployment()
    if record is None:
        return {
            "mode": "none",
            "explanation": (
                "No contract deployed. This marketplace reads its listings from "
                "ListingContract and has no offline mode; deploy with "
                "scripts/deploy_base_sepolia.py."
            ),
            "chain_id": None,
            "deployment": None,
        }
    return {
        "mode": "chain",
        "explanation": "Reading listings from ListingContract on Base Sepolia.",
        "chain_id": record.get("chain_id"),
        "deployment": record,
    }


#: What each SMP directory carries, in one line. The names are not repeated
#: here: they come from ``smp.py`` so this table cannot describe a directory
#: the packager does not build, or miss one it does.
CATEGORY_NOTES: dict[str, str] = {
    "identity": "Who the agent is, and the ERC-8004 token that says so.",
    "relationships": "Counterparties it knows, and the edges between them.",
    "preferences": "Standing choices it has been taught to make.",
    "history": "What it did, including settled ACP jobs.",
    "commitments": "Obligations still outstanding at the moment of sale.",
    "learned-behaviors": "Heuristics it adapted rather than arrived with.",
    "provenance": "The chain of custody, written at build time.",
    "permissions": "Consent, per record, for what may change hands.",
    "integrity-proof": "The Merkle tree a buyer re-derives to check the sale.",
}

#: The three generated directories describe the package rather than the memory,
#: so they are not sold and not selectable. Listing them anyway is the point:
#: a buyer should be able to see what exists but is not on offer.
COMING_SOON = frozenset(GENERATED_CATEGORIES)


def _capability_model(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The nine directories, each with what the market currently offers of it.

    Read from ``category_transferability`` rather than ``counts``: that field is
    keyed by SMP directory and already split by consent, so the table can say
    what is actually for sale instead of how many records happen to exist.
    ``counts`` is keyed by source tier and would have silently summed to nothing
    here, which is the kind of zero that looks like an empty market rather than
    a wrong lookup.

    The figures come from the previews sellers published, so a directory reads
    zero when nothing describes it rather than when nothing exists. That
    distinction is what ``with_data_room`` reports beside it.
    """
    sellable: dict[str, int] = {}
    withheld: dict[str, int] = {}
    listed_in: dict[str, int] = {}

    for row in rows:
        breakdown = (row.get("preview") or {}).get("category_transferability") or {}
        for name, split in breakdown.items():
            if not isinstance(split, dict):
                continue
            try:
                ok = int(split.get("sellable", 0))
                no = int(split.get("withheld", 0))
            except (TypeError, ValueError):
                continue
            if ok <= 0 and no <= 0:
                continue
            sellable[name] = sellable.get(name, 0) + ok
            withheld[name] = withheld.get(name, 0) + no
            if ok > 0:
                listed_in[name] = listed_in.get(name, 0) + 1

    model = []
    for name in (*DATA_CATEGORIES, *GENERATED_CATEGORIES):
        model.append(
            {
                "category": name,
                "transferable": name not in COMING_SOON,
                "status": "coming-soon" if name in COMING_SOON else "live",
                "note": CATEGORY_NOTES.get(name, ""),
                "records_sellable": sellable.get(name, 0),
                "records_withheld": withheld.get(name, 0),
                "listings": listed_in.get(name, 0),
            }
        )
    return model


def _reputation_model() -> dict[str, Any]:
    """The weights the score is built from, read from the scorer itself.

    Published because a score whose weighting is private is an assertion. These
    are the same constants ``reputation.py`` computes with, so the screen cannot
    document a formula the code does not use.
    """
    return {
        "basis": (
            "Recomputed from the package on every read. Never stored, never "
            "supplied by the seller, so a buyer derives the same figure from "
            "the memory they received."
        ),
        "factors": [
            {
                "name": "integrity",
                "weight": str(W_INTEGRITY),
                "note": "Transfers whose delivered hash matched the commitment.",
            },
            {
                "name": "lineage",
                "weight": str(W_LINEAGE),
                "note": f"Verified handovers, saturating at {LINEAGE_TARGET}.",
            },
            {
                "name": "continuity",
                "weight": str(W_CONTINUITY),
                "note": "Whether owners grew the memory or sat on it.",
            },
            {
                "name": "earnings",
                "weight": str(W_EARNINGS),
                "note": f"Settled ACP outcomes, abstaining below {MIN_RESOLVED}.",
            },
            {
                "name": "span",
                "weight": str(W_SPAN),
                "note": f"Custody age, saturating at {SPAN_TARGET_DAYS} days.",
            },
        ],
        "grades": ["unproven", "early", "developing", "proven", "established"],
        "does_not_transfer": [
            {
                "item": "Virtuals ACP standing",
                "why": (
                    "The registry exposes reads, job initiation and evaluation. "
                    "It has no transfer call, so standing is re-earned by the "
                    "buyer. A signed handover attestation records the lineage "
                    "instead of pretending the registration moved."
                ),
            },
        ],
    }


@app.get("/api/overview")
def overview() -> dict[str, Any]:
    """Everything the service knows, in one read.

    A dashboard that assembles itself from five separate calls spends its first
    second half-drawn, and each call would repeat the same bounded log scan. So
    the aggregation happens here, once, where the chain read already is.

    Counts are derived from the listings themselves rather than tracked
    separately. A stored tally is a second source of truth that drifts from the
    first, and the whole argument of this project is that there is one.
    """
    record = _deployment()
    if record is None:
        return {
            "chain": False,
            "explanation": (
                "No contract deployed. Listings are read from ListingContract, "
                "so there is nothing to summarise."
            ),
            "totals": {},
            "listings": [],
            "demo_listings": demo_rows(),
            "deployment": None,
            # The capability model is a property of the software, not of the
            # chain, so it is answered even here. A dashboard that goes blank
            # when the contract is unset would hide what the app does behind a
            # configuration problem.
            "capabilities": _capability_model([]),
            "reputation_model": _reputation_model(),
        }

    body = marketplace()
    # `listings` is real rows by construction, so every total below is computed
    # from the actual market without needing to filter anything out.
    rows = body.get("listings", [])

    by_state: dict[str, int] = {}
    volume_settled = 0
    volume_open = 0
    agents: set[str] = set()
    sellers: set[str] = set()
    described = 0

    for row in rows:
        listing = row["listing"]
        state = listing.get("state", "unknown")
        by_state[state] = by_state.get(state, 0) + 1
        price = int(listing.get("price") or 0)
        if state == "confirmed":
            volume_settled += price
        elif state in ("open", "escrowed"):
            volume_open += price
        if row.get("agent_identity"):
            agents.add(str(row["agent_identity"]))
        if listing.get("seller"):
            sellers.add(listing["seller"])
        if row.get("has_metadata"):
            described += 1

    return {
        "chain": True,
        "explanation": "Read from ListingContract on Base Sepolia.",
        "totals": {
            "listings": len(rows),
            "by_state": by_state,
            # Minor units, like every other figure the API returns, so the
            # frontend formats money in exactly one place.
            "volume_settled": volume_settled,
            "volume_open": volume_open,
            "agents": len(agents),
            "sellers": len(sellers),
            # How many listings their seller actually described. The gap is
            # worth showing: it is the difference between a market and a ledger.
            "with_data_room": described,
        },
        "listings": rows,
        "demo_listings": demo_rows(),
        "deployment": record,
        "capabilities": _capability_model(rows),
        "reputation_model": _reputation_model(),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "workdir": str(STORE.workdir)}


# The scripted walkthrough, under its own prefix. It is mounted here and
# referenced nowhere else: no route above reads its state, and it never writes
# to the metadata registry the marketplace reads. Every response it returns is
# stamped ``simulated: true``.
from .walkthrough import router as walkthrough_router  # noqa: E402

app.include_router(walkthrough_router)
