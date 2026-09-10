"""Sibyl Memory adapter — the reference implementation of MemorySource/Sink.

Notes on the real SDK surface, since it differs from the contract-level shape
the build spec sketches (the spec says to confirm signatures at build time, and
this is what confirming them turned up against ``sibyl-memory-client`` 0.8.0):

* ``list_entities(category=None, status=None, limit=100)`` exists natively.
  There is no need to iterate ``search_entities`` with an empty query.
* ``limit`` is clamped to ``MAX_LIMIT`` (10,000) on every listing call, so a
  full export has to page rather than ask for everything at once.
* ``read_events`` returns newest-first and is likewise clamped, so the journal
  is paged backwards through its ``until`` cursor and reversed at the end.
* The free-tier cap is **5 MB**, not the 2 MB the spec quotes. Seed data should
  still stay compact, but the real ceiling is higher than planned for.
* ``get_state`` / ``get_reference`` are keyed-only: the public client has no
  "list every state document" call. A full export needs enumeration, so those
  two tiers are read through the client's own documented ``storage`` escape
  hatch (``MemoryClient.storage`` is exposed for exactly this "advanced use"),
  scoped to the active tenant. Writes always go back through the public API so
  the cap gate, validation, and FTS triggers all still run.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from uuid import uuid4
from pathlib import Path
from typing import Any, Iterable

from sibyl_memory_client import MemoryClient
from sibyl_memory_client.storage import Storage

from .base import (
    archived_record,
    entity_record,
    event_record,
    reference_record,
    relation_record,
    state_record,
)

__all__ = ["SibylMemory", "open_tenant"]

_PAGE = 1_000


def _loads(raw: str | None) -> Any:
    return None if raw is None else json.loads(raw)


class AtomicStorage(Storage):
    """SDK writes use savepoints inside an application-owned transaction.

    Connections are SDK thread-local; unrelated threads never join this
    transaction. The outer BEGIN IMMEDIATE serializes competing writers.
    """
    tenant_provider = None

    def _assert_writable(self, conn):
        if self.tenant_provider is None:
            return
        from ..seal import TenantSealed
        tenant = self.tenant_provider()
        row = conn.execute(
            "SELECT sealed_at, reason FROM sealed_tenants WHERE tenant_id = ?", (tenant,)
        ).fetchone()
        if row is not None:
            raise TenantSealed(tenant, row["sealed_at"], row["reason"])

    @contextmanager
    def transaction(self):
        with self.connection() as conn:
            if not conn.in_transaction:
                with super().transaction() as active:
                    self._assert_writable(active)
                    yield active
                return
            name = "succession_" + uuid4().hex
            conn.execute(f"SAVEPOINT {name}")
            try:
                self._assert_writable(conn)
                yield conn
            except BaseException:
                conn.execute(f"ROLLBACK TO {name}")
                conn.execute(f"RELEASE {name}")
                raise
            else:
                conn.execute(f"RELEASE {name}")


class SibylMemory:
    """Adapts a ``MemoryClient`` bound to one tenant."""

    def __init__(self, client: MemoryClient) -> None:
        self._client = client

    @contextmanager
    def atomic_import(self):
        if not isinstance(self._client.storage, AtomicStorage):
            raise RuntimeError("atomic imports require a tenant opened through succession.open_tenant")
        with self._client.storage.transaction():
            yield

    @property
    def client(self) -> MemoryClient:
        return self._client

    def seal(self, *, reason: str, agent_identity=None, transfer_id=None):
        """Retire this local tenant. This does not revoke remote SDK credentials."""
        from ..seal import SealRegistry
        return SealRegistry(self._client.storage.db_path).seal(
            self.tenant_id, reason=reason, agent_identity=agent_identity, transfer_id=transfer_id
        )

    @property
    def tenant_id(self) -> str:
        return self._client.get_tenant()

    # -- the rest of the SDK -------------------------------------------
    #
    # Succession used seventeen of MemoryClient's twenty-six public methods and
    # ignored the nine that describe the *state* of a store rather than its
    # contents. That was a real omission for a marketplace: a seller could not
    # see that their store was near the tier cap, that the linter had findings
    # against it, or that skill proposals were sitting unresolved — all of which
    # a buyer inherits or is denied. Each accessor below degrades to None rather
    # than raising, because three of the four are paid-tier features and an
    # export must not fail on a free account.

    def store_health(self) -> dict[str, Any]:
        """Everything the SDK knows about this store that is not a record.

        Assembled in one call because these are read together — before listing,
        by `succession status`, and into the data room — and because each one
        can be absent for a different reason that the caller should not have to
        distinguish.
        """
        return {
            "tier": self._safe(self._client.get_tier),
            "schema_version": self._safe(self._client.schema_version),
            "capacity": self._safe(self._client.free_tier_status),
            "pending_skill_proposals": self._pending(),
            "lint": self._lint(),
        }

    def schema_version(self) -> int | None:
        """The store's schema version, carried in the package header.

        A buyer importing into a store on a different schema needs to know
        before they pay, not after the import coerces something.
        """
        return self._safe(self._client.schema_version)

    def _pending(self) -> int | None:
        """How many skill proposals are unresolved.

        Succession could already accept and reject them but never list them, so
        a seller had no way to see what was outstanding. Proposals are memory
        the agent has not yet committed to, and selling with them pending hands
        the buyer a decision the seller declined to make.
        """
        try:
            return len(self._client.list_skill_proposals(status="pending"))
        except Exception:  # noqa: BLE001 - paid tier, or none at all
            return None

    def _lint(self) -> dict[str, Any] | None:
        """The memory linter's findings, when the tier allows it.

        A quality signal computed by the engine rather than asserted by the
        seller, which is the only kind this marketplace is interested in.
        """
        try:
            report = self._client.lint()
        except Exception:  # noqa: BLE001 - paid-tier only
            return None
        if report is None:
            return None
        if hasattr(report, "to_dict"):
            return report.to_dict()
        if isinstance(report, dict):
            return report
        return {"findings": len(report) if hasattr(report, "__len__") else None}

    @staticmethod
    def _safe(call: Any) -> Any:
        try:
            return call()
        except Exception:  # noqa: BLE001 - absence is an answer here
            return None

    # -- low-level -----------------------------------------------------

    def _query(self, sql: str, params: tuple[Any, ...]) -> list[sqlite3.Row]:
        with self._client.storage.connection() as conn:
            return conn.execute(sql, params).fetchall()

    # -- reads ---------------------------------------------------------

    def entities(self) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT id, category, name, status, body, created_at, updated_at "
            "FROM entities WHERE tenant_id = ? ORDER BY category, name",
            (self.tenant_id,),
        )
        return [
            entity_record(
                id=r["id"],
                category=r["category"],
                name=r["name"],
                status=r["status"],
                body=_loads(r["body"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def events(self) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT id, ts, evaluated, acted, forward, extra "
            "FROM journal_events WHERE tenant_id = ? ORDER BY ts, id",
            (self.tenant_id,),
        )
        return [
            event_record(
                id=r["id"],
                ts=r["ts"],
                evaluated=_loads(r["evaluated"]),
                acted=_loads(r["acted"]),
                forward=_loads(r["forward"]),
                extra=_loads(r["extra"]),
            )
            for r in rows
        ]

    def states(self) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT document_key, body, updated_at FROM state_documents "
            "WHERE tenant_id = ? ORDER BY document_key",
            (self.tenant_id,),
        )
        return [
            state_record(
                key=r["document_key"], body=_loads(r["body"]), updated_at=r["updated_at"]
            )
            for r in rows
        ]

    def references(self) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT doc_key, body, metadata, updated_at FROM reference_documents "
            "WHERE tenant_id = ? ORDER BY doc_key",
            (self.tenant_id,),
        )
        out = []
        for r in rows:
            # reference_documents.body is free text, not necessarily JSON.
            out.append(
                reference_record(
                    key=r["doc_key"],
                    body=r["body"],
                    metadata=_loads(r["metadata"]),
                    updated_at=r["updated_at"],
                )
            )
        return out

    def archived(self) -> list[dict[str, Any]]:
        rows = self._query(
            "SELECT id, category, name, body, archive_reason, archived_at "
            "FROM archived_entities WHERE tenant_id = ? ORDER BY category, name, id",
            (self.tenant_id,),
        )
        return [
            archived_record(
                id=r["id"],
                category=r["category"],
                name=r["name"],
                body=_loads(r["body"]),
                archive_reason=r["archive_reason"],
                archived_at=r["archived_at"],
            )
            for r in rows
        ]

    def relations(self) -> list[dict[str, Any]]:
        # Resolve both endpoints to logical (category, name) keys: row ids are
        # regenerated on import, so an edge stored by id dangles immediately.
        rows = self._query(
            "SELECT f.category AS f_cat, f.name AS f_name, "
            "       t.category AS t_cat, t.name AS t_name, "
            "       r.relation_type, r.metadata, r.created_at "
            "FROM entity_relations r "
            "JOIN entities f ON f.id = r.from_id "
            "JOIN entities t ON t.id = r.to_id "
            "WHERE r.tenant_id = ? "
            "ORDER BY f.category, f.name, t.category, t.name, r.relation_type",
            (self.tenant_id,),
        )
        return [
            relation_record(
                from_key=(r["f_cat"], r["f_name"]),
                to_key=(r["t_cat"], r["t_name"]),
                relation_type=r["relation_type"],
                metadata=_loads(r["metadata"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # -- writes --------------------------------------------------------

    def is_empty(self) -> bool:
        """True when this tenant holds no records in any tier.

        The import pipeline refuses to write into a non-empty tenant. Merging
        two independently-evolved memories is Part 6's ``merge`` primitive, and
        it is explicitly roadmap — silently colliding on the
        ``(tenant_id, category, name)`` unique constraint is not a merge, it is
        data loss with a friendly error message.
        """
        tables = (
            "entities",
            "journal_events",
            "state_documents",
            "reference_documents",
            "archived_entities",
            "entity_relations",
        )
        for table in tables:
            row = self._query(
                f"SELECT 1 FROM {table} WHERE tenant_id = ? LIMIT 1", (self.tenant_id,)
            )
            if row:
                return False
        return True

    def purge(self) -> int:
        """Delete every row belonging to this tenant. Returns the row count.

        The compensating action for a failed import, and nothing else. The
        transfer orchestrator calls it only against a tenant it confirmed empty
        moments earlier, so the rows being deleted are exactly the ones the
        failed import just wrote — never a buyer's pre-existing memory, which
        :meth:`is_empty` refused to import over in the first place.
        """
        tables = (
            "entity_relations",
            "entities",
            "journal_events",
            "state_documents",
            "reference_documents",
            "archived_entities",
        )
        deleted = 0
        with self._client.storage.transaction() as conn:
            for table in tables:
                cur = conn.execute(
                    f"DELETE FROM {table} WHERE tenant_id = ?", (self.tenant_id,)
                )
                deleted += cur.rowcount or 0
        return deleted

    def write_entities(self, records: Iterable[dict[str, Any]]) -> int:
        n = 0
        for rec in records:
            self._client.set_entity(
                rec["category"], rec["name"], rec["body"], status=rec.get("status")
            )
            n += 1
        return n

    def write_events(self, records: Iterable[dict[str, Any]]) -> int:
        n = 0
        for rec in records:
            self._client.write_event(
                evaluated=rec.get("evaluated"),
                acted=rec.get("acted"),
                forward=rec.get("forward"),
                extra=rec.get("extra"),
                ts=rec.get("ts"),
            )
            n += 1
        return n

    def write_states(self, records: Iterable[dict[str, Any]]) -> int:
        n = 0
        for rec in records:
            self._client.set_state(rec["key"], rec["body"])
            n += 1
        return n

    def write_references(self, records: Iterable[dict[str, Any]]) -> int:
        n = 0
        for rec in records:
            self._client.set_reference(
                rec["key"], rec["body"], metadata=rec.get("metadata")
            )
            n += 1
        return n

    def write_archived(self, records: Iterable[dict[str, Any]]) -> int:
        """Restore ARCHIVE-tier rows directly.

        There is no public "insert an already-archived entity" call — the
        client's ``archive_entity`` archives something currently live. Writing a
        live entity and archiving it would work but bumps the cap gate twice for
        every archived row and rewrites ``archived_at``. The direct insert keeps
        the original archive reason and timestamp, which is the point of
        carrying the tier at all.
        """
        n = 0
        with self._client.storage.transaction() as conn:
            for rec in records:
                conn.execute(
                    "INSERT INTO archived_entities "
                    "(id, tenant_id, original_entity_id, category, name, body, "
                    " archive_reason, archived_at) "
                    "VALUES (?, ?, NULL, ?, ?, ?, ?, "
                    "        COALESCE(?, strftime('%Y-%m-%dT%H:%M:%fZ','now')))",
                    (
                        _new_id(),
                        self.tenant_id,
                        rec["category"],
                        rec["name"],
                        json.dumps(rec["body"], separators=(",", ":")),
                        rec.get("archive_reason"),
                        rec.get("archived_at"),
                    ),
                )
                n += 1
        return n

    def write_relations(self, records: Iterable[dict[str, Any]]) -> int:
        """Re-link edges by logical key against the freshly written entities."""
        n = 0
        with self._client.storage.transaction() as conn:
            for rec in records:
                from_id = _resolve(conn, self.tenant_id, rec["from_key"])
                to_id = _resolve(conn, self.tenant_id, rec["to_key"])
                if from_id is None or to_id is None:
                    # Endpoint was withheld by a redaction or category filter.
                    # Dropping the edge is correct: an edge to an entity the
                    # buyer never received is not information they can use, and
                    # the FK would reject it anyway.
                    continue
                conn.execute(
                    "INSERT INTO entity_relations "
                    "(id, tenant_id, from_id, to_id, relation_type, metadata, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, "
                    "        COALESCE(?, strftime('%Y-%m-%dT%H:%M:%fZ','now')))",
                    (
                        _new_id(),
                        self.tenant_id,
                        from_id,
                        to_id,
                        rec["relation_type"],
                        None
                        if rec.get("metadata") is None
                        else json.dumps(rec["metadata"], separators=(",", ":")),
                        rec.get("created_at"),
                    ),
                )
                n += 1
        return n


def _resolve(conn: sqlite3.Connection, tenant: str, key: Any) -> str | None:
    category, name = key[0], key[1]
    row = conn.execute(
        "SELECT id FROM entities WHERE tenant_id = ? AND category = ? AND name = ?",
        (tenant, category, name),
    ).fetchone()
    return None if row is None else row["id"]


def _new_id() -> str:
    import uuid

    return uuid.uuid4().hex


def open_tenant(
    db_path: str | Path, tenant_id: str, *, tier: str = "free"
) -> SibylMemory:
    """Open one tenant of a Sibyl store as a Succession source/sink.

    Two tenants in the same file, or two separate files, both work — the
    ``(tenant_id, category, name)`` constraint is per-tenant either way. The
    two-machine rehearsal the spec insists on uses separate files on separate
    hosts; a single file with two tenants is the fast local loop.
    """
    # Credentials the Sibyl CLI already wrote, if there are any. Without them
    # the SDK enforces a strict local 5 MB cap and gates off the paid features,
    # so a customer on a plan was being silently treated as free tier. An
    # explicit `tier=` argument still wins, because callers that pass one mean it.
    from .credentials import load_credentials

    found = load_credentials()
    options = found.kwargs()
    if tier != "free":
        options["tier"] = tier

    from ..seal import SealRegistry

    path = Path(db_path).expanduser()
    SealRegistry(path)
    storage = AtomicStorage(path)
    client = MemoryClient(storage, tenant_id=tenant_id, **options)
    storage.tenant_provider = client.get_tenant
    return SibylMemory(client)
