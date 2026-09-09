"""Short-lived request authorization; no reusable listing credentials."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct

DOMAIN = "Succession/request/v2"
MAX_AGE = 300


def request_message(*, listing_id: str, method: str, path: str, body: bytes,
                    chain_id: int, contract: str, timestamp: int, nonce: str) -> str:
    return DOMAIN + "\n" + json.dumps({
        "listing_id": listing_id, "method": method.upper(), "path": path,
        "body_sha256": hashlib.sha256(body).hexdigest(), "chain_id": chain_id,
        "contract": contract.lower(), "timestamp": timestamp, "nonce": nonce,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def request_auth_headers(private_key: str, *, listing_id: str, method: str,
                         path: str, body: bytes = b"", chain_id: int, contract: str,
                         timestamp: int | None = None, nonce: str | None = None) -> dict[str, str]:
    timestamp = int(time.time()) if timestamp is None else timestamp
    nonce = nonce or uuid.uuid4().hex
    message = request_message(listing_id=listing_id, method=method, path=path,
        body=body, chain_id=chain_id, contract=contract, timestamp=timestamp, nonce=nonce)
    return {
        "X-Succession-Address": Account.from_key(private_key).address,
        "X-Succession-Timestamp": str(timestamp), "X-Succession-Nonce": nonce,
        "X-Succession-Signature": Account.sign_message(encode_defunct(text=message), private_key).signature.hex(),
    }


def json_body(body: dict[str, Any]) -> bytes:
    return json.dumps(body, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
