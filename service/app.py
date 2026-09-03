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

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from succession.agent import Agent
from succession.demokeys import BUYER, SELLER
from succession.memory.sibyl import open_tenant
from succession.seal import SealRegistry, TenantSealed, guard
from succession.seed import seed_seller
from succession.settlement import LocalSettlement, SettlementError
from succession.transfer import execute_transfer, list_asset

WORKDIR = Path(os.environ.get("SUCCESSION_WORKDIR", "demo-state"))
LISTING_ID = os.environ.get("SUCCESSION_LISTING_ID", "listing-0417")
PRICE = int(os.environ.get("SUCCESSION_PRICE", 420_000_000))

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
        # The listing's encrypted envelope and content key are held in memory
        # only. Persisting the content key next to the ciphertext would defeat
        # the entire point of escrowing it.
        self.listed: Any = None

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


STORE = Store(WORKDIR)


# --- models --------------------------------------------------------------


class ResetRequest(BaseModel):
    categories: list[str] | None = None
    price: int = PRICE


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
    """Wipe state, seed the seller, and post the listing."""
    import shutil

    if STORE.workdir.exists():
        shutil.rmtree(STORE.workdir)
    STORE.workdir.mkdir(parents=True, exist_ok=True)
    STORE.listed = None

    seller = STORE.seller()
    seed_seller(seller)

    STORE.listed = list_asset(
        seller,
        STORE.settlement,
        listing_id=LISTING_ID,
        agent_identity=SELLER.agent_id,
        seller_address=SELLER.address,
        private_key=SELLER.private_key,
        price=request.price,
        categories=request.categories,
    )
    return {"listing_id": LISTING_ID, "committed_root": STORE.listed.committed_root}


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
    if STORE.listed is None:
        raise HTTPException(409, "no listing in this process; POST /api/demo/reset")
    return STORE.listed.preview.to_dict()


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
    if STORE.listed is None:
        raise HTTPException(409, "no listing in this process; POST /api/demo/reset")
    try:
        outcome = execute_transfer(
            listing_id=LISTING_ID,
            settlement=STORE.settlement,
            seals=STORE.seals,
            envelope=STORE.listed.envelope,
            content_key=STORE.listed.content_key,
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
    return payload


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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "workdir": str(STORE.workdir)}
