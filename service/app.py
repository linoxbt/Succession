"""The Succession service: data room, transfer, and the two agent chat views.

A thin HTTP layer over the pipeline — every route delegates to
:mod:`succession`, and none of them reimplements a rule. In particular the
preview route returns exactly what :func:`succession.dataroom.build_preview`
produces, so there is no second, more talkative code path for the UI to leak
through.

State lives in ``SUCCESSION_WORKDIR`` (default ``./demo-state``). Reset the demo
with ``POST /api/demo/reset``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from succession.agent import Agent
from succession.catalog import CATALOG, NOW, seed_archetype
from succession.demokeys import BUYER, SELLER
from succession.memory.sibyl import open_tenant
from succession.seal import SealRegistry, TenantSealed, guard
from succession.seed import seed_seller
from succession.settlement import LocalSettlement, SettlementError
from succession.transfer import execute_transfer, list_asset
from succession.valuation import value_tenant

WORKDIR = Path(os.environ.get("SUCCESSION_WORKDIR", "demo-state"))
LISTING_ID = os.environ.get("SUCCESSION_LISTING_ID", "listing-0417")

#: What the featured seller asks against their own reference valuation.
FEATURED_ASK_RATIO = os.environ.get("SUCCESSION_ASK_RATIO", "1.12")


def _derived_price(memory: Any, ratio: str) -> int:
    """Asking price in minor units, from the tenant's computed valuation."""
    from decimal import ROUND_HALF_UP, Decimal

    amount = value_tenant(memory, now=NOW).amount * Decimal(ratio)
    return int(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 1_000_000)

SELLER_TENANT = "tenant-seller"
BUYER_TENANT = "tenant-buyer"

app = FastAPI(title="Succession", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- state ---------------------------------------------------------------


class Store:
    """Handles onto the demo's stores. Reopened per request; SQLite is cheap."""

    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        # Encrypted envelopes and content keys are held in memory only, keyed by
        # listing id. Persisting a content key next to its ciphertext would
        # defeat the entire point of escrowing it.
        self.listed: dict[str, Any] = {}
        # Which tenant backs which listing, so a marketplace row can be opened.
        self.tenants: dict[str, str] = {}

    @property
    def featured(self) -> Any:
        """The listing the single-listing routes act on."""
        return self.listed.get(LISTING_ID)

    @property
    def settlement(self) -> LocalSettlement:
        return LocalSettlement(self.workdir / "settlement.db")

    @property
    def seals(self) -> SealRegistry:
        return SealRegistry(self.workdir / "seals.db")

    def seller(self):
        return open_tenant(self.workdir / "seller.db", SELLER_TENANT)

    def buyer(self):
        return open_tenant(self.workdir / "buyer.db", BUYER_TENANT)

    def tenant(self, listing_id: str):
        """Open the store behind a listing."""
        name = self.tenants.get(listing_id)
        if name is None:
            raise HTTPException(404, f"no tenant for listing {listing_id!r}")
        return open_tenant(self.workdir / f"{name}.db", name)


STORE = Store(WORKDIR)


# --- models --------------------------------------------------------------


class ResetRequest(BaseModel):
    categories: list[str] | None = None
    #: Absolute asking price, in minor units. Left unset the featured listing
    #: is priced off its own computed valuation like every other listing —
    #: a fixed price drifts from the valuation until the marketplace shows a
    #: spread that means nothing.
    price: int | None = None
    marketplace: bool = True


class BuyRequest(BaseModel):
    buyer_address: str = BUYER.address


class MessageRequest(BaseModel):
    message: str


class WriteAttemptRequest(BaseModel):
    category: str = "commitment"
    name: str = "quote-NW-4472"
    body: dict[str, Any] = {"lane": "Duluth to Kansas City", "quoted_rate_usd": 2400}


# --- routes --------------------------------------------------------------


@app.post("/api/demo/reset")
def reset(request: ResetRequest) -> dict[str, Any]:
    """Wipe state, seed every agent, and post the whole marketplace.

    Clears any persisted outcome first: a reset that left the previous sale's
    certificate on disk would show a settled transfer against a listing that
    has just been re-created.

    Each listing is a real export of a real store: the root, record count,
    memory size and valuation are computed by the pipeline, never written down.
    A marketplace of hardcoded rows would be the exact pattern this project
    argues against.
    """
    import shutil

    if STORE.workdir.exists():
        shutil.rmtree(STORE.workdir)
    STORE.workdir.mkdir(parents=True, exist_ok=True)
    STORE.listed, STORE.tenants = {}, {}

    # The featured listing — the one the transfer walkthrough acts on.
    seller = STORE.seller()
    seed_seller(seller)
    STORE.tenants[LISTING_ID] = SELLER_TENANT
    featured_price = request.price or _derived_price(seller, FEATURED_ASK_RATIO)
    STORE.listed[LISTING_ID] = list_asset(
        seller,
        STORE.settlement,
        listing_id=LISTING_ID,
        agent_identity=SELLER.agent_id,
        seller_address=SELLER.address,
        private_key=SELLER.private_key,
        price=featured_price,
        categories=request.categories,
    )

    # The rest of the market.
    if request.marketplace:
        for archetype in CATALOG:
            memory = open_tenant(
                STORE.workdir / f"{archetype.tenant_id}.db", archetype.tenant_id
            )
            seed_archetype(memory, archetype)
            STORE.tenants[archetype.listing_id] = archetype.tenant_id
            # Price off the agent's own computed valuation, so the asking price
            # and the reference figure can never contradict each other.
            price = archetype.asking_price(value_tenant(memory, now=NOW).amount)
            STORE.listed[archetype.listing_id] = list_asset(
                memory,
                STORE.settlement,
                listing_id=archetype.listing_id,
                agent_identity=archetype.agent_identity,
                seller_address=SELLER.address,
                private_key=SELLER.private_key,
                price=price,
            )

    return {
        "listing_id": LISTING_ID,
        "committed_root": STORE.listed[LISTING_ID].committed_root,
        "listings": len(STORE.listed),
    }


@app.get("/api/marketplace")
def marketplace() -> dict[str, Any]:
    """Every listing, with its computed preview.

    Aggregate figures only, exactly as the single-listing preview returns them —
    a marketplace must not become a second, more talkative path to record
    bodies.
    """
    from succession.catalog import archetype_by_slug

    rows = []
    for listing in STORE.settlement.list_all():
        held = STORE.listed.get(listing.listing_id)
        if held is None:
            continue
        vertical, name = "Freight", "Meridian Logistics Co."
        tenant = STORE.tenants.get(listing.listing_id, "")
        if tenant.startswith("tenant-") and tenant != SELLER_TENANT:
            try:
                a = archetype_by_slug(tenant.removeprefix("tenant-"))
                vertical, name = a.vertical, a.name
            except KeyError:
                pass
        rows.append(
            {
                "listing": listing.to_dict(),
                "preview": held.preview.to_dict(),
                "name": name,
                "vertical": vertical,
                "featured": listing.listing_id == LISTING_ID,
            }
        )

    return {"listings": rows, "count": len(rows)}


@app.get("/api/listing")
def listing() -> dict[str, Any]:
    try:
        record = STORE.settlement.get(LISTING_ID)
    except SettlementError as exc:
        raise HTTPException(404, str(exc)) from exc
    return record.to_dict()


@app.get("/api/listing/preview")
def preview() -> dict[str, Any]:
    """The data room: aggregate statistics only, no record bodies."""
    if STORE.featured is None:
        raise HTTPException(409, "no listing in this process; POST /api/demo/reset")
    return STORE.featured.preview.to_dict()


@app.post("/api/listing/buy")
def buy(request: BuyRequest) -> dict[str, Any]:
    try:
        record = STORE.settlement.buy(
            LISTING_ID, buyer=request.buyer_address, amount=STORE.settlement.get(LISTING_ID).price
        )
    except SettlementError as exc:
        raise HTTPException(409, str(exc)) from exc
    return record.to_dict()


@app.post("/api/listing/transfer")
def transfer() -> dict[str, Any]:
    """Deliver, re-key, verify, settle, seal, and record."""
    if STORE.featured is None:
        raise HTTPException(409, "no listing in this process; POST /api/demo/reset")
    try:
        outcome = execute_transfer(
            listing_id=LISTING_ID,
            settlement=STORE.settlement,
            seals=STORE.seals,
            envelope=STORE.featured.envelope,
            content_key=STORE.featured.content_key,
            seller_tenant_id=SELLER_TENANT,
            buyer_sink=STORE.buyer(),
            buyer_identity=BUYER.agent_id,
            buyer_address=BUYER.address,
            expected_signer=SELLER.address,
        )
    except SettlementError as exc:
        raise HTTPException(409, str(exc)) from exc

    payload = outcome.to_dict()
    if outcome.certificate is not None:
        payload["certificate_text"] = outcome.certificate.to_text()
    _save_outcome(payload)
    return payload


def _outcome_path() -> Path:
    return STORE.workdir / "outcomes" / f"{LISTING_ID}.json"


def _save_outcome(payload: dict[str, Any]) -> None:
    """Persist what the transfer produced, so a reload can recover it.

    The settlement receipt is already durable in ``settlement.db``, but the
    certificate is assembled from the package header, which lives only in this
    process. Without this, reloading the page after a completed sale showed an
    empty ledger and no confirmation screen for a transfer that genuinely
    happened — the UI claiming, in effect, that nothing had occurred.

    Written after settlement rather than before, so a file only ever exists for
    a sale that actually reached an outcome.
    """
    path = _outcome_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@app.get("/api/listing/outcome")
def listing_outcome() -> dict[str, Any]:
    """The settled outcome, if this listing reached one.

    404 is the meaningful answer for a sale that has not settled — it is what
    lets the console distinguish "not yet" from "failed", which the two states
    on the confirmation screen depend on telling apart.
    """
    path = _outcome_path()
    if not path.is_file():
        raise HTTPException(404, f"listing {LISTING_ID!r} has not settled")
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(500, f"outcome record unreadable: {exc}") from exc


@app.get("/api/seal/{tenant_id}")
def seal_status(tenant_id: str) -> dict[str, Any]:
    record = STORE.seals.get(tenant_id)
    return {"tenant_id": tenant_id, "sealed": record is not None,
            "record": record.to_dict() if record else None}


@app.post("/api/seller/write-attempt")
def seller_write_attempt(request: WriteAttemptRequest) -> dict[str, Any]:
    """Try to write to the seller's tenant. After a sale this must be rejected.

    Exposed as a route rather than left to the CLI because it is the demo beat
    that answers "what stops the seller from keeping a copy", and it should be
    visible on the same screen as everything else.
    """
    guarded = guard(STORE.seller(), STORE.seals)
    try:
        guarded.client.set_entity(request.category, request.name, request.body)
    except TenantSealed as exc:
        return {"accepted": False, "reason": str(exc)}
    return {
        "accepted": True,
        "reason": "tenant is not sealed; the sale has not completed",
    }


@app.post("/api/agent/{side}/message")
def agent_message(side: str, request: MessageRequest) -> dict[str, Any]:
    """The chat view, for either agent."""
    if side == "seller":
        memory = STORE.seller()
    elif side == "buyer":
        memory = STORE.buyer()
    else:
        raise HTTPException(404, "side must be 'seller' or 'buyer'")

    if side == "buyer" and memory.is_empty():
        return {
            "text": (
                "I have no memory yet. This agent has not been booted against a "
                "transferred store."
            ),
            "recalled": False,
            "citations": [],
        }
    return Agent(memory).respond(request.message).to_dict()


@app.get("/api/agent/{side}/provenance")
def agent_provenance(side: str) -> dict[str, Any]:
    memory = STORE.buyer() if side == "buyer" else STORE.seller()
    try:
        return memory.client.get_entity("provenance", "acquisition")["body"]
    except Exception:  # noqa: BLE001 - absence is the meaningful answer here
        raise HTTPException(404, "no acquisition record for this agent") from None


@app.get("/api/chain")
def chain() -> dict[str, Any]:
    """What settlement backend is actually in use, and where.

    The frontend needs this to decide whether the buyer can pay from their own
    wallet, and — more importantly — so it can say which backend settled a sale
    instead of letting the two look identical. ``LocalSettlement`` mirrors the
    contract's state machine faithfully enough that a screen showing only the
    outcome could not tell them apart, and a demo that quietly presented the
    mirror as the chain would be exactly the dishonesty this project exists to
    avoid.

    A deployment file is the only thing that makes on-chain mode available.
    There is no configuration flag that turns it on without one, because a flag
    is something that can be set wrongly.
    """
    record = _deployment()
    if record is None:
        return {
            "mode": "local",
            "explanation": (
                "Settling through LocalSettlement, an in-process mirror of "
                "ListingContract's state machine. No transaction reaches Base. "
                "Deploy with scripts/deploy_base_sepolia.py to settle on chain."
            ),
            "chain_id": None,
            "deployment": None,
        }
    return {
        "mode": "chain",
        "explanation": (
            "Settling on Base Sepolia through the deployed ListingContract."
        ),
        "chain_id": record.get("chain_id"),
        "deployment": record,
    }


def _deployment() -> dict[str, Any] | None:
    """Read the deployment record, if one has been written.

    Deliberately re-read per request rather than cached at import: deploying is
    something that happens while the service is already running, and a cached
    ``None`` would keep reporting local mode until someone restarted it.
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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "workdir": str(STORE.workdir)}
