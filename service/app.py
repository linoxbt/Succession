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
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from secrets import compare_digest
from typing import Any

from eth_utils import to_checksum_address
from eth_account import Account
from eth_account.messages import encode_defunct, defunct_hash_message
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from starlette.concurrency import run_in_threadpool

from succession.auth import request_message, MAX_AGE
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
from succession.settlement import ListingState, ListingNotFound, SettlementError
from succession.smp import DATA_CATEGORIES, GENERATED_CATEGORIES

from .demo import demo_rows, is_demo
from .registry import MetadataRegistry
from .models import public_preview, Envelope, Manifest, Header, UNVERIFIED_BASIS

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


@app.middleware("http")
async def private_key_responses(request: Request, call_next):
    STORE.expire_keys()
    response = await call_next(request)
    if request.url.path.endswith("/key"):
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Vary"] = "X-Succession-Address, X-Succession-Signature"
    return response


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
        self.key_expiry: dict[str, float] = {}

    def expire_keys(self) -> None:
        for listing_id, expires in list(self.key_expiry.items()):
            if expires <= time.time():
                self.released.pop(listing_id, None)
                self.key_expiry.pop(listing_id, None)

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
        os.environ.get("SUCCESSION_DEPLOYMENT")
        or Path(__file__).resolve().parents[1] / "deployments" / "base-sepolia.json"
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

    @field_validator('preview')
    @classmethod
    def valid_preview(cls, value):
        public_preview(value)
        return value

    @field_validator('envelope','integrity','provenance')
    @classmethod
    def valid_documents(cls, value, info):
        if value:
            {'envelope':Envelope,'integrity':Manifest,'provenance':Header}[info.field_name].model_validate(value)
        return value


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
    except ListingNotFound as exc:
        raise HTTPException(404, f"no listing {listing_id!r} on chain: {exc}") from exc
    except SettlementError as exc:
        raise HTTPException(503, "could not read the listing from the chain; please retry") from exc


async def _authenticate(request: Request, listing_id: str, expected: str, chain, record) -> str:
    """Authenticate this exact request as an EOA or ERC-1271 contract wallet."""
    signature = request.headers.get("x-succession-signature", "")
    try:
        timestamp = int(request.headers.get("x-succession-timestamp", ""))
        nonce = request.headers.get("x-succession-nonce", "")
        address = to_checksum_address(request.headers.get("x-succession-address", ""))
        now = int(time.time())
        if timestamp < now - MAX_AGE or timestamp > now + 30 or not re.fullmatch(r"[a-fA-F0-9]{32,64}", nonce):
            raise ValueError("expired request or invalid nonce")
        if address != to_checksum_address(expected):
            raise HTTPException(403, "only the on-chain counterparty may authorize this operation")
        message = request_message(listing_id=listing_id, method=request.method,
            path=request.url.path, body=await request.body(), chain_id=int(record["chain_id"]),
            contract=record["listing_contract"], timestamp=timestamp, nonce=nonce)
        try:
            valid = to_checksum_address(Account.recover_message(encode_defunct(text=message), signature=signature)) == address
        except Exception:
            valid = False
        if not valid and chain.w3.eth.get_code(address):
            wallet = chain.w3.eth.contract(address=address, abi=[{
                "type":"function", "name":"isValidSignature", "stateMutability":"view",
                "inputs":[{"name":"hash","type":"bytes32"},{"name":"signature","type":"bytes"}],
                "outputs":[{"name":"magic","type":"bytes4"}]}])
            valid = bytes(wallet.functions.isValidSignature(defunct_hash_message(text=message), bytes.fromhex(signature.removeprefix("0x"))).call()) == bytes.fromhex("1626ba7e")
        if not valid:
            raise ValueError("invalid signature")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(401, "valid, unexpired request authorization is required") from exc
    if not STORE.registry.consume_nonce(address, nonce, expires=timestamp + MAX_AGE, now=now):
        raise HTTPException(401, "authorization has already been used; sign a new request")
    return address


# --- routes --------------------------------------------------------------


@app.post("/api/listings")
async def post_listing(body: ListingPost, request: Request) -> dict[str, Any]:
    """Publish the parts of a listing the chain does not carry.

    The listing must already exist on chain and the caller must be its seller.
    Both are checked here rather than trusted, so this table cannot describe a
    sale that was never committed to.
    """
    on_chain, _chain_backend, record = await run_in_threadpool(_seller_of, body.listing_id)
    await _authenticate(request, body.listing_id, on_chain.seller, _chain_backend, record)

    if on_chain.hash_commitment.lower() != body.committed_root.lower():
        raise HTTPException(
            409,
            f"the contract commits {body.listing_id} to {on_chain.hash_commitment}, "
            f"not {body.committed_root}",
        )

    from succession.erc8004 import parse_agent_identity
    from succession.provenance import verify_header
    try:
        identity_chain, token = parse_agent_identity(body.agent_identity)
        actual_token = int(str(on_chain.agent_id).split(':')[-1])
        if identity_chain != int(record['chain_id']) or token != actual_token:
            raise ValueError('identity differs from the contract')
        if body.chain_id != int(record['chain_id']) or body.contract.lower() != record['listing_contract'].lower():
            raise ValueError('deployment differs from the contract')
        if body.preview.get('agent_identity') not in (None, '', body.agent_identity):
            raise ValueError('preview names a different identity')
        if body.envelope and (body.envelope['listing_id'] != body.listing_id or body.envelope['hash_commitment'].lower() != on_chain.hash_commitment.lower()):
            raise ValueError('envelope describes a different asset')
        if body.integrity and body.integrity['root'].lower() != on_chain.hash_commitment.lower():
            raise ValueError('manifest describes a different root')
        if body.provenance:
            verify_header(body.provenance, on_chain.seller)
            if body.provenance['agent_identity'] != body.agent_identity or body.provenance['integrity_root'].lower() != on_chain.hash_commitment.lower():
                raise ValueError('signed header describes a different asset')
    except Exception as exc:
        raise HTTPException(422, f'inconsistent listing metadata: {exc}') from exc

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
    discovery = {'complete': False}
    try:
        from .chain_index import discover
        discovered, discovery = discover(chain, STORE.registry.db_path, _record)
    except Exception as exc:
        raise HTTPException(503, 'Could not read the listing index from chain; please retry.') from exc

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
        except ListingNotFound:
            continue
        except SettlementError as exc:
            raise HTTPException(503, 'Could not refresh on-chain listing state; please retry.') from exc
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
        "discovery": discovery,
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
    try:
        preview = public_preview(meta.get('preview') or {})
    except (ValueError, TypeError):
        preview = {}
    documents = {}
    for name, model in [('integrity', Manifest), ('provenance', Header)]:
        try:
            document = meta.get(name) or {}
            if document:
                model.model_validate(document)
            documents[name] = document
        except (ValueError, TypeError):
            documents[name] = {}
    listing_data = on_chain.to_dict()
    for field in ('price', 'escrow_balance'):
        if abs(listing_data[field]) > 2**53 - 1:
            listing_data[field] = str(listing_data[field])
    return {
        "listing": listing_data,
        "preview": preview,
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
        "integrity": documents['integrity'],
        "provenance": documents['provenance'],
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
async def release_key(listing_id: str, body: KeyPost, request: Request) -> dict[str, Any]:
    """A seller releases the content key. Escrow is re-checked here, not trusted.

    The seller has already satisfied themselves that escrow is funded — that is
    what ``succession fulfil`` does. This service checks the same thing again
    before accepting the key, because a service that stored a key on the
    seller's say-so would be a service that could be talked into storing it
    early.
    """
    on_chain, _chain, _record = await run_in_threadpool(_seller_of, listing_id)
    await _authenticate(request, listing_id, on_chain.seller, _chain, _record)
    STORE.expire_keys()

    if on_chain.state not in (ListingState.ESCROWED, ListingState.CONFIRMED):
        raise HTTPException(
            409,
            f"{listing_id} is {on_chain.state.value}; a key is accepted only "
            "while escrow is funded or after evaluator settlement",
        )
    STORE.released[listing_id] = body.content_key
    # Long enough for post-settlement buyer recovery. The seller watcher
    # republishes after relay restarts and while reconciling confirmation.
    STORE.key_expiry[listing_id] = time.time() + 86_400
    return {"listing_id": listing_id, "accepted": True, "buyer": on_chain.buyer,
            "stage": on_chain.state.value}


@app.get("/api/listing/{listing_id}/key/evaluator")
async def collect_evaluator_key(listing_id: str, request: Request) -> dict[str, Any]:
    """Release plaintext only to the configured evaluator before settlement."""
    on_chain, chain, record = await run_in_threadpool(_seller_of, listing_id)
    STORE.expire_keys()
    if on_chain.state is not ListingState.ESCROWED:
        raise HTTPException(409, f"{listing_id} is {on_chain.state.value}; evaluation requires funded escrow")
    evaluator = await run_in_threadpool(lambda: chain.arbiter)
    if not evaluator or evaluator == "0x0000000000000000000000000000000000000000":
        raise HTTPException(503, "this deployment has no evaluator")
    await _authenticate(request, listing_id, evaluator, chain, record)
    key = STORE.released.get(listing_id)
    if key is None:
        raise HTTPException(404, "the seller has not released the evaluator key yet")
    return {"listing_id": listing_id, "content_key": key}


@app.get("/api/listing/{listing_id}/key")
async def collect_key(listing_id: str, request: Request) -> dict[str, Any]:
    """The buyer collects the key only after evaluator settlement.

    Escrow is checked again on the way out. The window in which this service
    holds a usable key is the gap between the seller releasing it and the buyer
    importing, and it is bounded on both sides by the chain.
    """
    on_chain, _chain, _record = await run_in_threadpool(_seller_of, listing_id)
    STORE.expire_keys()
    if on_chain.state is not ListingState.CONFIRMED:
        if on_chain.state is ListingState.REFUNDED:
            STORE.released.pop(listing_id, None)
            STORE.key_expiry.pop(listing_id, None)
        raise HTTPException(
            409, f"{listing_id} is {on_chain.state.value}; the buyer key is available only after evaluator settlement"
        )
    try:
        await run_in_threadpool(
            _chain.confirmed_receipt,
            listing_id,
            from_block=int(_record.get("deployment_block", 0)),
        )
    except SettlementError as exc:
        raise HTTPException(
            425,
            "evaluator settlement is mined but has not reached the configured finality depth",
        ) from exc
    await _authenticate(request, listing_id, on_chain.buyer, _chain, _record)
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
    try:
        chain, _ = CHAIN_PROVIDER()
        actual_chain = chain.w3.eth.chain_id
        if actual_chain != int(record['chain_id']):
            raise ValueError('wrong network')
        if not chain.w3.eth.get_code(record['listing_contract']):
            raise ValueError('no deployed contract')
        head = chain.w3.eth.block_number
    except Exception:
        return {'mode': 'unavailable', 'explanation': 'Deployment configured, but chain or contract health could not be verified.',
                'chain_id': record.get('chain_id'), 'deployment': record}
    return {
        "mode": "chain",
        "head_block": head,
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
        "basis": UNVERIFIED_BASIS,
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
            "volume_settled": str(volume_settled) if volume_settled > 2**53 - 1 else volume_settled,
            "volume_open": str(volume_open) if volume_open > 2**53 - 1 else volume_open,
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


@app.get("/api/activity")
def activity(limit: int = 100) -> dict[str, Any]:
    """What has happened, as opposed to what is true now.

    Every other read here reports current state. This reports the events that
    produced it: when a listing was made, when escrow landed, who bought, which
    transaction settled it, and whether a listing that now reads `refunded` was
    refunded or cancelled. That last one cannot be answered any other way,
    because `cancel()` writes the same state a refund does and differs only in
    the event it emits.

    On-chain events only. A demonstration listing emits nothing, so this ledger
    is structurally incapable of reporting one, which is a stronger guarantee
    than remembering to filter.
    """
    try:
        chain, record = CHAIN_PROVIDER()
    except HTTPException:
        return {
            "chain": False,
            "explanation": (
                "No contract deployed. Activity is read from contract events, "
                "so there is nothing to report."
            ),
            "events": [],
            "count": 0,
        }

    try:
        events = chain.activity(limit=max(1, min(limit, 250)))
    except Exception as exc:  # noqa: BLE001 - a refused scan degrades, not 500s
        return {
            "chain": True,
            "explanation": f"The log scan did not complete ({exc}).",
            "events": [],
            "count": 0,
        }

    return {
        "chain": True,
        "explanation": "Read from ListingContract events on Base Sepolia.",
        "events": events,
        "count": len(events),
        "explorer": record.get("explorer", ""),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "workdir": str(STORE.workdir)}


# The scripted walkthrough, under its own prefix. It is mounted here and
# referenced nowhere else: no route above reads its state, and it never writes
# to the metadata registry the marketplace reads. Every response it returns is
# stamped ``simulated: true``.
from .walkthrough import session_middleware, router as walkthrough_router  # noqa: E402

app.middleware("http")(session_middleware)
app.include_router(walkthrough_router)

from .request_limits import RequestSizeLimit  # noqa: E402
app.add_middleware(RequestSizeLimit)
