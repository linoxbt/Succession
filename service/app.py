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
from succession.settlement import ListingState, SettlementError

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
        posted_at=_now(),
    )
    return {"listing_id": body.listing_id, "published": True}


@app.get("/api/marketplace")
def marketplace() -> dict[str, Any]:
    """Every listing, joined: the contract for truth, the registry for the rest.

    A listing whose chain read fails is dropped rather than shown from metadata
    alone — a row rendered from this table while the contract said otherwise
    would be the marketplace inventing a sale.
    """
    try:
        chain, _record = CHAIN_PROVIDER()
    except HTTPException:
        # No chain configured yet. An empty marketplace is the honest answer;
        # inventing rows to fill the screen is the thing this project argues
        # against.
        return {"listings": [], "count": 0, "chain": False}

    rows = []
    for meta in STORE.registry.all():
        try:
            on_chain = chain.get(meta["listing_id"])
        except SettlementError:
            continue
        rows.append(
            {
                "listing": on_chain.to_dict(),
                "preview": meta["preview"],
                "name": meta["name"],
                "vertical": meta["vertical"],
                "valuation": meta["valuation"],
                "agent_identity": meta["agent_identity"],
                "has_envelope": meta["has_envelope"],
            }
        )
    return {"listings": rows, "count": len(rows), "chain": True}


@app.get("/api/listing/{listing_id}")
def listing(listing_id: str) -> dict[str, Any]:
    on_chain, _chain, _record = _seller_of(listing_id)
    meta = STORE.registry.get(listing_id)
    return {
        "listing": on_chain.to_dict(),
        "preview": (meta or {}).get("preview", {}),
        "name": (meta or {}).get("name", ""),
        "vertical": (meta or {}).get("vertical", ""),
        "valuation": (meta or {}).get("valuation", ""),
        "agent_identity": (meta or {}).get("agent_identity", ""),
    }


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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "workdir": str(STORE.workdir)}


# The scripted walkthrough, under its own prefix. It is mounted here and
# referenced nowhere else: no route above reads its state, and it never writes
# to the metadata registry the marketplace reads. Every response it returns is
# stamped ``simulated: true``.
from .walkthrough import router as walkthrough_router  # noqa: E402

app.include_router(walkthrough_router)
