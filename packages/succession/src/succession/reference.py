"""The command reference, read out of the parser rather than written beside it.

Documentation that is retyped drifts. The README, the in-app guide and the CLI's
own help were three copies of the same list, and two of them were already
incomplete: the web app named five of nineteen commands, and the README omitted
`inspect`, `succession-acp snapshot` and `succession-acp show`.

So none of them is written by hand any more. This walks the argparse parsers
that actually run and reports what they accept, which means a renamed flag
cannot leave stale documentation behind and a new command cannot be forgotten.
It is the same discipline as the ABI staleness check in CI, adopted for the same
reason: the generated file that was edited by hand kept CI red for
twenty-seven commits.
"""

from __future__ import annotations

import argparse
from typing import Any

__all__ = ["build_reference", "ENV", "GROUPS"]

#: Every environment variable the tools read, and what it is for. These are not
#: discoverable from argparse because several are consumed deep in the call
#: stack, so this is the one hand-maintained list, and a test checks each name
#: actually appears in the source.
ENV: tuple[tuple[str, str], ...] = (
    ("SUCCESSION_SIGNING_KEY",
     "The seller's wallet. Read from the environment, never an argument, "
     "because a private key on a command line lands in shell history and in "
     "the process table."),
    ("SUCCESSION_BUYER_KEY",
     "The buyer's wallet. Deliberately a different variable from the seller's: "
     "conflating them is how someone tries to buy their own listing."),
    ("SUCCESSION_EVALUATOR_KEY",
     "The independent evaluator wallet configured in the listing contract. "
     "It alone may settle a delivery."),
    ("SUCCESSION_FINALITY_CONFIRMATIONS",
     "Receipt depth required before a chain write is accepted. Defaults to "
     "three on Base Sepolia and one on local EVMs."),
    ("SUCCESSION_MARKETPLACE",
     "Which marketplace to publish to and read from. Defaults to "
     "http://127.0.0.1:8000, which is right for local development and wrong "
     "for everything else."),
    ("BASE_SEPOLIA_RPC_URL", "How to reach the chain."),
    ("SUCCESSION_DEPLOYMENT",
     "Path to the deployment record. The packaged copy is used when this is "
     "unset and no checkout is present."),
    ("SUCCESSION_ARTIFACTS",
     "Path to the contract ABI. Same fallback as the deployment record."),
    ("SUCCESSION_VAULT",
     "Where the seller's listings, envelopes and content keys are kept. "
     "Defaults to ~/.succession/listings."),
    ("SUCCESSION_MCP_ALLOW_WRITES",
     "Set to 1 to let an MCP client call the tools that spend money, release a "
     "decryption key, or permanently seal an agent. Off by default because "
     "sealing has no undo."),
    ("SIBYL_CREDENTIALS",
     "Path to credentials.json. Without it the memory SDK enforces a strict "
     "5 MB cap and the paid features gate off."),
)

#: How the commands group for a reader. A flat alphabetical list of nineteen
#: tells someone nothing about which to run first.
GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Start here", "Nothing here changes anything.",
     ("status", "audit", "market", "show")),
    ("Selling", "Runs on your own machine, against your own store.",
     ("inventory", "value", "preview", "prove", "export", "list", "publish",
      "fulfil", "listings")),
    ("Buying", "Fund escrow, then claim after independent evaluator settlement.",
     ("buy", "claim")),
    ("Evaluating", "Import into an isolated tenant, verify, and settle on the evaluator's signed verdict.",
     ("evaluate",)),
    ("Compatibility", "Retained to explain the evaluator migration to older buyer scripts.",
     ("confirm",)),
    ("Working with a package directly", "For inspecting a file you were handed.",
     ("inspect", "verify", "import")),
)


def _flag(action: argparse.Action) -> dict[str, Any]:
    names = list(action.option_strings) or [action.dest]
    return {
        "names": names,
        "required": bool(getattr(action, "required", False)),
        "help": (action.help or "").strip(),
        "choices": [str(c) for c in action.choices] if action.choices else [],
        "positional": not action.option_strings,
    }


def _commands(parser: argparse.ArgumentParser) -> list[dict[str, Any]]:
    subparsers = [
        a for a in parser._actions  # noqa: SLF001 - argparse exposes no public API
        if isinstance(a, argparse._SubParsersAction)  # noqa: SLF001
    ]
    if not subparsers:
        return []

    out = []
    # `choices` maps name to parser; `_choices_actions` carries the help text.
    helps = {c.dest: (c.help or "").strip() for c in subparsers[0]._choices_actions}  # noqa: SLF001
    for name, sub in subparsers[0].choices.items():
        flags = [
            _flag(a)
            for a in sub._actions  # noqa: SLF001
            if not isinstance(a, argparse._HelpAction)  # noqa: SLF001
        ]
        out.append({"name": name, "help": helps.get(name, ""), "flags": flags})
    return out


def build_reference() -> dict[str, Any]:
    """Every command both entry points accept, as the parsers define them."""
    from . import acp_cli, cli

    def parser_of(module: Any) -> argparse.ArgumentParser:
        # Both `main()` functions build their parser and then parse. Calling
        # with `--help` would exit, so the parser is rebuilt here by invoking
        # the same construction path with a sentinel that raises before parsing.
        captured: dict[str, argparse.ArgumentParser] = {}
        original = argparse.ArgumentParser.parse_args

        def capture(self, *a: Any, **k: Any):  # type: ignore[no-untyped-def]
            captured["parser"] = self
            raise _Captured

        argparse.ArgumentParser.parse_args = capture  # type: ignore[assignment]
        try:
            module.main([])
        except _Captured:
            pass
        finally:
            argparse.ArgumentParser.parse_args = original  # type: ignore[assignment]
        return captured["parser"]

    return {
        "succession": _commands(parser_of(cli)),
        "succession-acp": _commands(parser_of(acp_cli)),
        "env": [{"name": n, "help": h} for n, h in ENV],
        "groups": [
            {"title": t, "note": n, "commands": list(c)} for t, n, c in GROUPS
        ],
    }


class _Captured(Exception):
    """Control flow, not an error: the parser was built, so stop before parsing."""
