"""Canonical, deterministic serialization.

Hashing a memory store is only meaningful if two honest parties who hold the
same logical content always produce the same bytes. Everything that reaches the
Merkle tree goes through this module first.

The rules, in full:

* Objects are emitted with keys sorted by Unicode code point.
* No insignificant whitespace (``separators=(",", ":")``).
* Text stays UTF-8 (``ensure_ascii=False``) and is NFC-normalized, so two
  visually identical strings that differ only in Unicode composition hash the
  same.
* Floats are rejected outright. JSON has no canonical float rendering that
  survives a round trip through every language's parser, and a memory store has
  no legitimate need for one — an agent that wants a number with a fractional
  part should carry it as a string or a scaled integer.
* Entities sort by ``(category, name)``; journal events sort by ``(ts, id)``.
  ``id`` breaks ties because two events written in the same millisecond are
  common and their insertion order is not stable across a re-import.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any

__all__ = [
    "canonical_bytes",
    "canonical_json",
    "normalize",
    "entity_sort_key",
    "event_sort_key",
    "CanonicalizationError",
]


class CanonicalizationError(ValueError):
    """A value cannot be canonicalized deterministically."""


def normalize(value: Any) -> Any:
    """Recursively coerce ``value`` into canonicalizable form.

    Rejects anything whose serialization is not stable across languages.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise CanonicalizationError(
            "floats are not canonicalizable; carry the value as a string or a "
            f"scaled integer instead (got {value!r})"
        )
    if isinstance(value, str):
        # NFC so "é" (U+00E9) and "é" hash identically.
        return unicodedata.normalize("NFC", value)
    if isinstance(value, (list, tuple)):
        # List order is content: it is preserved, not sorted.
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise CanonicalizationError(
                    f"object keys must be strings, got {type(k).__name__}"
                )
            key = unicodedata.normalize("NFC", k)
            if key in out:
                raise CanonicalizationError(
                    f"duplicate key after NFC normalization: {key!r}"
                )
            out[key] = normalize(v)
        return out
    raise CanonicalizationError(
        f"value of type {type(value).__name__} is not JSON-canonicalizable"
    )


def canonical_json(value: Any) -> str:
    """Return the canonical JSON text for ``value``."""
    return json.dumps(
        normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_bytes(value: Any) -> bytes:
    """Return the canonical UTF-8 bytes for ``value`` — what actually gets hashed."""
    return canonical_json(value).encode("utf-8")


def entity_sort_key(entity: dict[str, Any]) -> tuple[str, str]:
    return (entity.get("category") or "", entity.get("name") or "")


def event_sort_key(event: dict[str, Any]) -> tuple[str, str]:
    return (event.get("ts") or "", event.get("id") or "")
