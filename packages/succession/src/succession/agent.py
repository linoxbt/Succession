"""A minimal agent that answers strictly out of Sibyl Memory.

This backs the demo's final beat — the buyer's agent, cold-booted on new
infrastructure, continuing a live customer relationship it has never seen.

It is retrieval over the tenant, not a language model, and that is a deliberate
choice rather than a shortcut. The claim being demonstrated is "the memory
transferred and is usable", and a deterministic responder demonstrates exactly
that: every line it produces is traceable to a specific record, with the
category and name it came from. A model in this position would produce a more
fluent answer and a weaker demonstration, because a fluent answer is exactly
what a model can produce with no memory at all.

Swapping in a real model is a small change and the right one for production —
:meth:`Agent.context_for` already returns the grounded context a prompt would
carry. The demo keeps the deterministic path so what is on screen is evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Agent", "Reply", "Citation"]

#: Words too common to retrieve anything useful. Kept short on purpose: an
#: aggressive list would strip the domain terms ("reefer", "flatbed", "lane")
#: that are exactly what makes a message findable.
_STOPWORDS = frozenset(
    """a an and are as at be but by can could do for from has have hi hello
    how i if in is it me my need of on or our out still that the their them
    then there this to us we what when where which will with would you your
    again about any anything back get got just like more not now one same
    still than too very was were yes""".split()
)


def _terms(text: str) -> list[str]:
    """The distinctive words in a message, in order, deduplicated."""
    import re

    seen: set[str] = set()
    out: list[str] = []
    for raw in re.findall(r"[A-Za-z][A-Za-z'-]+", text):
        word = raw.lower().strip("'-")
        if len(word) < 4 or word in _STOPWORDS or word in seen:
            continue
        seen.add(word)
        out.append(raw)
    return out[:8]


@dataclass(frozen=True)
class Citation:
    """Where a line of the answer came from. Every claim carries one."""

    tier: str
    key: str

    def to_dict(self) -> dict[str, str]:
        return {"tier": self.tier, "key": self.key}


@dataclass
class Reply:
    text: str
    citations: list[Citation] = field(default_factory=list)
    recalled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "recalled": self.recalled,
            "citations": [c.to_dict() for c in self.citations],
        }


class Agent:
    """Answers about a counterparty from whatever the tenant actually holds."""

    def __init__(self, memory: Any) -> None:
        self.memory = memory

    # -- retrieval -----------------------------------------------------

    def find_counterparty(self, text: str) -> dict[str, Any] | None:
        """Match a message to a known counterparty.

        Goes through Sibyl's FTS5 index (``search_entities``, anchored to the
        ``relationship`` category) rather than scanning every entity in Python.
        That matters for more than speed: the index covers the entity's name,
        category and body, so a customer who mentions their lane or a detail
        from the notes is matched even when they never say the company name —
        which is the realistic case for a returning customer.

        The scan is kept as a fallback. FTS returns nothing for a query whose
        every token is a stopword or punctuation, and "recall failed" is the
        wrong answer when the company name is sitting right there in the text.
        """
        hits = self._search_relationships(text)

        needle = text.lower()
        best: tuple[int, dict[str, Any]] | None = None
        for entity in hits or self._all_relationships():
            company = str(entity["body"].get("company", ""))
            for candidate in (company.lower(), entity["name"].replace("-", " ")):
                if candidate and candidate in needle:
                    # Longest literal match wins, so "Northwind Mills" beats "mills".
                    if best is None or len(candidate) > best[0]:
                        best = (len(candidate), entity)
        if best is not None:
            return best[1]

        # No literal name in the message, but FTS matched something on the body
        # — the lane, or a detail from the notes. Take its top-ranked hit.
        return hits[0] if hits else None

    def _search_relationships(self, text: str) -> list[dict[str, Any]]:
        """FTS over the relationship category, one distinctive term at a time.

        The SDK sanitizes a query into a single FTS5 *phrase*, so passing a
        whole sentence asks the index for that exact sentence and finds
        nothing. Searching the message's distinctive terms individually and
        merging by how many of them hit is what actually retrieves a
        counterparty from "we need a reefer from Yakima to Denver" — where the
        company is never named and the match has to come from the lane and the
        notes.
        """
        scored: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}
        for term in _terms(text):
            try:
                results = self.memory.client.search_entities(
                    term, limit=5, category="relationship"
                )
            except Exception:  # noqa: BLE001 - a search that errors is skipped
                continue
            for entity in results:
                key = (entity["category"], entity["name"])
                count, _ = scored.get(key, (0, entity))
                scored[key] = (count + 1, entity)

        return [
            entity
            for _, entity in sorted(scored.values(), key=lambda p: -p[0])
        ]

    def _all_relationships(self) -> list[dict[str, Any]]:
        return [e for e in self.memory.entities() if e["category"] == "relationship"]

    def open_commitment_for(self, company: str) -> dict[str, Any] | None:
        for entity in self.memory.entities():
            if entity["category"] != "commitment":
                continue
            if entity["body"].get("counterparty") == company:
                return entity
        return None

    def behaviour_for(self, company: str) -> dict[str, Any] | None:
        for entity in self.memory.entities():
            if entity["category"] != "learned-behavior":
                continue
            if company.lower() in str(entity["body"].get("pattern", "")).lower():
                return entity
        return None

    def working_state(self) -> dict[str, Any] | None:
        state = self.memory.client.get_state("current-negotiation")
        return state["body"] if state else None

    def context_for(self, message: str) -> dict[str, Any]:
        """The grounded context behind an answer — what a prompt would carry."""
        counterparty = self.find_counterparty(message)
        if counterparty is None:
            return {}
        company = counterparty["body"].get("company", counterparty["name"])
        return {
            "counterparty": counterparty,
            "commitment": self.open_commitment_for(company),
            "behaviour": self.behaviour_for(company),
            "state": self.working_state(),
            "history": self._history_for(counterparty),
        }

    def _history_for(self, counterparty: dict[str, Any]) -> list[str]:
        """Journal lines about this counterparty.

        Matching on the company name alone misses most of them: the journal
        records work by lane ("quoted Duluth to Kansas City at 2380; accepted"),
        because that is how the agent thinks about a booking. The lane is
        therefore part of the needle, not just the name.
        """
        body = counterparty["body"]
        needles = {str(body.get("company", "")).lower(), counterparty["name"].replace("-", " ")}
        lane = str(body.get("primary_lane", "")).lower()
        if lane and lane != "withheld":
            needles.add(lane)
        needles = {n for n in needles if n}

        return [
            line
            for event in self.memory.events()
            for line in (event.get("acted") or [])
            if any(n in line.lower() for n in needles)
        ]

    # -- response ------------------------------------------------------

    def respond(self, message: str) -> Reply:
        context = self.context_for(message)
        if not context:
            return Reply(
                text=(
                    "I don't have a record of this counterparty. Could you tell me "
                    "the company and the lane, and I'll quote it fresh?"
                ),
                recalled=False,
            )

        counterparty = context["counterparty"]
        company = counterparty["body"].get("company", counterparty["name"])
        citations = [Citation("relationship", counterparty["name"])]

        parts = [f"Yes — {company}."]

        commitment = context.get("commitment")
        state = context.get("state")
        if commitment is not None:
            body = commitment["body"]
            rate = body.get("quoted_rate_usd") or body.get("proposed_standing_rate_usd")
            parts.append(
                f"We have {body['lane']} open at ${rate:,}, quoted as "
                f"{commitment['name']} and still {body['status']}."
            )
            citations.append(Citation("commitment", commitment["name"]))

        if state and state.get("counterparty") == company:
            parts.append(state["our_position"])
            citations.append(Citation("state", "current-negotiation"))

        behaviour = context.get("behaviour")
        if behaviour is not None:
            parts.append(behaviour["body"]["pattern"])
            citations.append(Citation("learned-behavior", behaviour["name"]))

        history = context.get("history") or []
        if history:
            n = len(history)
            parts.append(
                f"That's {n} prior interaction{'' if n == 1 else 's'} on record."
            )
            citations.append(
                Citation("history", f"{n} journal event{'' if n == 1 else 's'}")
            )

        return Reply(text=" ".join(parts), citations=citations)
