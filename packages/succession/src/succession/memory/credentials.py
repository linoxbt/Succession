"""Read the credentials the Sibyl CLI writes, so a paid tenant stays paid.

Succession and the Sibyl CLI share a SQLite file, and until now that was the
whole relationship: `open_tenant` called `MemoryClient.local(path)` with
`tier="free"` hardcoded and no account. That is a real downgrade, not a
cosmetic one. The SDK's own docstring is explicit — without `account_id` and
`session_token` "the SDK enforces a strict local 5 MB cap (no server check
possible)" — and the paid features, self-learning and the memory linter, gate
off `tier`.

So a customer on a paid Sibyl plan who exported through Succession was silently
treated as a free-tier user and could hit a 5 MB ceiling on a store the server
would have allowed. The fix is to read the file `sibyl init` already wrote and
pass it through.

**What this does not do.** There is no memory sync to connect to. The SDK's
entire network surface is two endpoints — a capacity check at the cap boundary
and a heartbeat carrying an integer operation count — and neither moves memory.
Reads and writes are local by design, which is also what makes "plaintext never
leaves the seller before escrow" true rather than aspirational. Connecting
credentials makes the tier correct; it does not make the memory remote, and
nothing here should be read as claiming otherwise.

Everything is best-effort. A missing, unreadable or malformed credentials file
leaves the caller exactly where it was before: local, free tier, 5 MB. An
export must not fail because a telemetry field could not be parsed.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["SibylCredentials", "load_credentials", "DEFAULT_CREDENTIALS_PATH"]

#: Where `sibyl init` writes them. Overridable for anyone with a split setup.
DEFAULT_CREDENTIALS_PATH = Path("~/.sibyl-memory/credentials.json")

CREDENTIALS_ENV = "SIBYL_CREDENTIALS"
TIER_ENV = "SIBYL_TIER"


@dataclass(frozen=True)
class SibylCredentials:
    """What the SDK needs to treat this store as its owner's, not a stranger's."""

    tier: str = "free"
    account_id: str | None = None
    session_token: str | None = None
    claim: dict[str, Any] | None = None
    signature: str | None = None
    source: str = "defaults"

    @property
    def connected(self) -> bool:
        """Whether the server can be asked about this account at all."""
        return bool(self.account_id and self.session_token)

    def kwargs(self) -> dict[str, Any]:
        """The subset `MemoryClient.local` accepts, omitting what is unset.

        Passing `None` explicitly would be the same as omitting it, but building
        the dict this way keeps the call site honest about what was actually
        found rather than what was defaulted.
        """
        out: dict[str, Any] = {"tier": self.tier}
        if self.account_id:
            out["account_id"] = self.account_id
        if self.session_token:
            out["session_token"] = self.session_token
        if self.claim:
            out["credentials_claim"] = self.claim
        if self.signature:
            out["credentials_signature"] = self.signature
        return out

    def describe(self) -> str:
        if not self.connected:
            return (
                f"tier {self.tier}, local only. No account credentials found, so "
                "the SDK enforces a strict 5 MB cap and paid features stay off. "
                "Run `sibyl init` if you have a plan."
            )
        return f"tier {self.tier}, account {self.account_id} ({self.source})"


def load_credentials(path: str | Path | None = None) -> SibylCredentials:
    """Read `credentials.json`, or return the defaults it would have overridden.

    Never raises. A seller mid-export should not lose a package because a JSON
    file had a trailing comma.
    """
    candidate = (
        Path(path)
        if path
        else Path(os.environ.get(CREDENTIALS_ENV, DEFAULT_CREDENTIALS_PATH))
    )
    candidate = candidate.expanduser()

    tier_override = os.environ.get(TIER_ENV)

    if not candidate.is_file():
        return SibylCredentials(
            tier=tier_override or "free",
            source="environment" if tier_override else "defaults",
        )

    try:
        blob = json.loads(candidate.read_text("utf-8"))
    except (OSError, ValueError):
        return SibylCredentials(
            tier=tier_override or "free", source=f"unreadable ({candidate})"
        )

    if not isinstance(blob, dict):
        return SibylCredentials(tier=tier_override or "free", source="malformed")

    claim = blob.get("claim") if isinstance(blob.get("claim"), dict) else None
    return SibylCredentials(
        # An explicit environment override wins, because that is the documented
        # way to test a tier without editing a credentials file.
        tier=str(tier_override or blob.get("tier") or "free"),
        account_id=_text(blob.get("account_id")),
        session_token=_text(blob.get("session_token")),
        claim=claim,
        signature=_text(blob.get("signature")),
        source=str(candidate),
    )


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None
