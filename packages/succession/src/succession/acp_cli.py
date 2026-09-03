"""ACP registration, sync, and snapshot — the operator-side commands.

Registration itself happens in the Virtuals app, not here: the ACP Tech
Playbook issues a whitelisted wallet and an entity id, and no SDK call
substitutes for that. What these commands do is everything after it — confirm
the registration is live, pull the agent's job history, mirror it into memory so
it becomes part of the transferable asset, and snapshot it for offline use.

    export WHITELISTED_WALLET_PRIVATE_KEY=0x...
    export AGENT_WALLET_ADDRESS=0x...
    export ACP_ENTITY_ID=...

    succession-acp status
    succession-acp sync --db seller.db --tenant tenant-seller
    succession-acp snapshot --out web/public/acp-snapshot.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .acp import (
    ACPNotConfigured,
    AgentNotRegistered,
    LiveACP,
    RecordedACP,
    fetch_history,
    job_history_from_memory,
    require_registered,
    sync_job_history,
)
from .memory.sibyl import open_tenant


def _history(args: argparse.Namespace):
    if getattr(args, "snapshot", None):
        return fetch_history(RecordedACP.from_file(args.snapshot))
    return fetch_history(LiveACP())


def cmd_status(args: argparse.Namespace) -> int:
    history = _history(args)
    try:
        require_registered(history)
    except AgentNotRegistered as exc:
        print(f"NOT REGISTERED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(history.to_dict(), indent=2))
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Pull job history and mirror it into the tenant.

    Gated on registration: syncing an unregistered agent would write an empty
    earnings record that later reads as "this agent earned nothing" rather than
    "this agent was never registered".
    """
    history = _history(args)
    require_registered(history)
    memory = open_tenant(args.db, args.tenant)
    written = sync_job_history(memory, history)
    print(f"synced {written} ACP jobs into {args.tenant}")
    print(f"completed: {len(history.completed)}  failed: {len(history.failed)}")
    print(f"gross volume: {history.gross_volume}")
    rate = history.success_rate()
    print(f"success rate: {rate if rate is not None else 'sample too small'}")
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    """Capture live history to a file, for offline development and the hosted UI."""
    source = LiveACP()
    payload = {"agent": source.agent(), "jobs": [j.to_dict() for j in source.jobs()]}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(payload['jobs'])} jobs to {args.out}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Read back the history a tenant already carries. Needs no credentials."""
    memory = open_tenant(args.db, args.tenant)
    print(json.dumps(job_history_from_memory(memory).to_dict(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="succession-acp", description="Virtuals ACP job history."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def snapshot_opt(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--snapshot",
            help="read from a captured snapshot instead of the live API",
        )

    def tenant_opts(p: argparse.ArgumentParser) -> None:
        p.add_argument("--db", type=Path, required=True)
        p.add_argument("--tenant", required=True)

    p = sub.add_parser("status", help="confirm registration and show job history")
    snapshot_opt(p)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("sync", help="mirror ACP job history into a tenant's memory")
    tenant_opts(p)
    snapshot_opt(p)
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("snapshot", help="capture live job history to a file")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("show", help="show the job history a tenant already carries")
    tenant_opts(p)
    p.set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ACPNotConfigured, AgentNotRegistered) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
