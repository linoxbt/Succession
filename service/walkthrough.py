"""The walkthrough: one scripted sale on a sample agent, kept away from the market.

Why this exists at all
----------------------

The marketplace is real — its listings come from ``ListingContract`` and exist
only because someone paid gas to commit a root. That is the right way for it to
work and it is also, on an empty market, a screen with nothing on it. The thing
this project most needs to *show* is the beat where a buyer's agent boots cold
into a store it has never seen and immediately knows an open commitment: memory
being load-bearing, which is the whole claim.

So the beat survives, on a sample agent, in here.

Why it cannot leak into the market
----------------------------------

Quarantine is structural rather than a label:

* **Its own module and its own route namespace.** Nothing in :mod:`service.app`
  imports this, and no route here writes to the metadata registry the
  marketplace reads. There is no code path by which a walkthrough listing
  becomes a marketplace row.
* **Explicitly ``LocalSettlement``.** Every settlement reference it produces is
  prefixed ``local:``, so a reference from here can never be mistaken for a
  transaction hash even out of context.
* **Every response carries ``simulated: true``.** The frontend does not have to
  remember which client it used; the payload says what it is. A screen that
  renders this as a live sale has to ignore a field that is always present.

The memory is synthetic and says so. The *pipeline* underneath is not: this runs
the same export, hash, encrypt, import and re-hash code as a real sale, so the
hash comparison it puts on screen is genuinely computed.
"""

from __future__ import annotations

from typing import Any
from contextvars import ContextVar
import asyncio
import secrets
import time
import shutil

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sibyl_memory_client import NotFoundError

from succession.agent import Agent
from succession.demokeys import BUYER, SELLER, EVALUATOR
from succession.evaluator import Evaluator
from succession.memory.sibyl import open_tenant
from succession.seal import SealRegistry, TenantSealed, guard
from succession.seed import seed_seller
from succession.settlement import LocalSettlement, SettlementError
from succession.transfer import execute_transfer, list_asset
from succession.valuation import value_tenant

router = APIRouter(prefix="/api/walkthrough", tags=["walkthrough"])

LISTING_ID = "walkthrough-0417"
SELLER_TENANT = "walkthrough-seller"
BUYER_TENANT = "walkthrough-buyer"

#: Stamped onto every response. The frontend keys its banner off this rather
#: than off which URL it happened to call.
SIMULATED = {
    "simulated": True,
    "notice": (
        "A scripted sale on a sample agent. The memory is synthetic and nothing "
        "here touches a chain — settlement is LocalSettlement, an in-process "
        "mirror of the contract's state machine. Real listings are on the "
        "Marketplace."
    ),
}


def _flag(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, **SIMULATED}


class _State:
    """Held per process. Losing it on restart costs a re-run of the walkthrough."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.last_used = time.monotonic()
        self.lock = asyncio.Lock()
        self.listed: Any = None
        self.outcome: dict[str, Any] | None = None

    def workdir(self):
        from .app import STORE

        # Under the service's workdir but in its own directory, so wiping the
        # walkthrough can never touch the marketplace's registry.
        path = STORE.workdir / "walkthrough" / self.session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def settlement(self) -> LocalSettlement:
        return LocalSettlement(self.workdir() / "settlement.db", arbiter=EVALUATOR.address)

    @property
    def seals(self) -> SealRegistry:
        return SealRegistry(self.workdir() / "seals.db")

    def seller(self):
        return open_tenant(self.workdir() / "seller.db", SELLER_TENANT)

    def buyer(self):
        return open_tenant(self.workdir() / "buyer.db", BUYER_TENANT)

    def evaluator(self):
        return open_tenant(self.workdir() / "evaluator.db", "walkthrough-evaluator")


_CURRENT: ContextVar[_State] = ContextVar("walkthrough_session")
_SESSIONS: dict[str, _State] = {}
SESSION_TTL = 1800
MAX_SESSIONS = 64


def _state() -> _State:
    return _CURRENT.get()


async def session_middleware(request: Request, call_next):
    if not request.url.path.startswith("/api/walkthrough/"):
        return await call_next(request)
    now = time.monotonic()
    for key, state in list(_SESSIONS.items()):
        if now - state.last_used > SESSION_TTL and not state.lock.locked():
            del _SESSIONS[key]
            await run_in_threadpool(shutil.rmtree, state.workdir(), True)
    session_id = request.cookies.get("succession_walkthrough", "")
    state = _SESSIONS.get(session_id)
    if state is None:
        if len(_SESSIONS) >= MAX_SESSIONS:
            return JSONResponse({"detail": "Walkthrough capacity reached; please try again later."},
                                status_code=503, headers={"Retry-After": "60", "Cache-Control": "no-store"})
        session_id = secrets.token_hex(32)
        state = _SESSIONS[session_id] = _State(session_id)
    async with state.lock:
        token = _CURRENT.set(state)
        try:
            response = await call_next(request)
        finally:
            state.last_used = time.monotonic()
            _CURRENT.reset(token)
    response.set_cookie("succession_walkthrough", session_id, httponly=True,
                        secure=request.url.scheme == "https", samesite="strict",
                        path="/api/walkthrough", max_age=SESSION_TTL)
    response.headers["Cache-Control"] = "no-store"
    return response


class ResetRequest(BaseModel):
    categories: list[str] | None = None


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class WriteAttemptRequest(BaseModel):
    category: str = "commitment"
    name: str = "quote-NW-4472"
    body: dict[str, Any] = {"lane": "Duluth to Kansas City", "quoted_rate_usd": 2400}


@router.post("/reset")
def reset(request: ResetRequest) -> dict[str, Any]:
    """Seed the sample agent and post its listing.

    Even here the figures are computed: the root, the counts and the valuation
    come out of the seeded store by running the real pipeline over it. Only the
    memory itself is invented, and the banner says so.
    """
    import shutil

    directory = _state().workdir()
    if directory.exists():
        shutil.rmtree(directory)
    _state().listed, _state().outcome = None, None

    seller = _state().seller()
    seed_seller(seller)
    price = int(value_tenant(seller).amount * 1_000_000)
    _state().listed = list_asset(
        seller,
        _state().settlement,
        listing_id=LISTING_ID,
        agent_identity=SELLER.agent_id,
        seller_address=SELLER.address,
        private_key=SELLER.private_key,
        price=price,
        categories=request.categories,
    )
    return _flag(
        {
            "listing_id": LISTING_ID,
            "committed_root": _state().listed.committed_root,
            "price": price,
        }
    )


def _require_listed():
    if _state().listed is None:
        raise HTTPException(409, "walkthrough not started; POST /api/walkthrough/reset")
    return _state().listed


@router.get("/listing")
def listing() -> dict[str, Any]:
    _require_listed()
    try:
        return _flag(_state().settlement.get(LISTING_ID).to_dict())
    except SettlementError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/preview")
def preview() -> dict[str, Any]:
    """The data room: aggregate statistics only, no record bodies."""
    return _flag(_require_listed().preview.to_dict())


@router.post("/buy")
def buy() -> dict[str, Any]:
    _require_listed()
    try:
        record = _state().settlement.buy(
            LISTING_ID,
            buyer=BUYER.address,
            amount=_state().settlement.get(LISTING_ID).price,
        )
    except SettlementError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _flag(record.to_dict())


@router.post("/transfer")
def transfer() -> dict[str, Any]:
    """Deliver, re-key, verify, settle, seal — the whole pipeline, for real."""
    listed = _require_listed()
    try:
        outcome = execute_transfer(
            listing_id=LISTING_ID,
            settlement=_state().settlement,
            seals=_state().seals,
            envelope=listed.envelope,
            content_key=listed.content_key,
            seller_tenant_id=SELLER_TENANT,
            buyer_sink=_state().buyer(),
            evaluator_sink=_state().evaluator(),
            evaluator=Evaluator(EVALUATOR.private_key),
            buyer_identity=BUYER.agent_id,
            buyer_address=BUYER.address,
            expected_signer=SELLER.address,
        )
    except SettlementError as exc:
        raise HTTPException(409, str(exc)) from exc

    payload = outcome.to_dict()
    if outcome.certificate is not None:
        payload["certificate_text"] = outcome.certificate.to_text()
    _state().outcome = payload
    return _flag(payload)


@router.get("/outcome")
def outcome() -> dict[str, Any]:
    if _state().outcome is None:
        raise HTTPException(404, "the walkthrough has not settled")
    return _flag(_state().outcome)


@router.get("/seal/{tenant_id}")
def seal_status(tenant_id: str) -> dict[str, Any]:
    record = _state().seals.get(tenant_id)
    return _flag(
        {
            "tenant_id": tenant_id,
            "sealed": record is not None,
            "record": record.to_dict() if record else None,
        }
    )


@router.post("/write-attempt")
def write_attempt(request: WriteAttemptRequest) -> dict[str, Any]:
    """Try to write to the seller's tenant. After the sale this must be rejected.

    The beat that answers "what stops the seller keeping a copy". The guard is
    the real one — the same `seal.guard` a production tenant runs behind.
    """
    guarded = guard(_state().seller(), _state().seals)
    try:
        guarded.client.set_entity(request.category, request.name, request.body)
    except TenantSealed as exc:
        return _flag({"accepted": False, "reason": str(exc)})
    return _flag(
        {"accepted": True, "reason": "tenant is not sealed; the sale has not completed"}
    )


@router.post("/agent/{side}/message")
def agent_message(side: str, request: MessageRequest) -> dict[str, Any]:
    """The beat that matters: a cold agent recalling transferred memory.

    Retrieval runs through Sibyl's FTS5 index over the buyer's *own* store, in
    its own tenant and its own file — so what comes back was genuinely written
    there by the import, not read out of the seller's copy.
    """
    if side == "seller":
        memory = _state().seller()
    elif side == "buyer":
        memory = _state().buyer()
    else:
        raise HTTPException(404, "side must be 'seller' or 'buyer'")

    if side == "buyer" and memory.is_empty():
        return _flag(
            {
                "text": (
                    "I have no memory yet. This agent has not been booted against "
                    "a transferred store."
                ),
                "recalled": False,
                "citations": [],
            }
        )
    return _flag(Agent(memory).respond(request.message).to_dict())


@router.get("/agent/{side}/provenance")
def agent_provenance(side: str) -> dict[str, Any]:
    if side not in ("seller", "buyer"):
        raise HTTPException(404, "side must be 'seller' or 'buyer'")
    memory = _state().buyer() if side == "buyer" else _state().seller()
    try:
        return _flag(memory.client.get_entity("provenance", "acquisition")["body"])
    except NotFoundError:
        raise HTTPException(404, "no acquisition record for this agent") from None
