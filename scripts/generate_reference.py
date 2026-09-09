#!/usr/bin/env python
"""Write the command reference the web app renders, from the parsers themselves.

    python scripts/generate_reference.py

The output is checked in and CI regenerates it and diffs, exactly as it does for
the contract ABI. That pairing is deliberate: the last long CI outage was a
generated file someone had edited by hand, and documentation drifts the same way
an ABI does, only more quietly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "succession" / "src"))

from succession.reference import build_reference  # noqa: E402

OUT = ROOT / "web" / "src" / "app" / "reference.ts"
README = ROOT / "README.md"

BEGIN = "<!-- BEGIN GENERATED COMMANDS -->"
END = "<!-- END GENERATED COMMANDS -->"

HEADER = '''/**
 * GENERATED FILE, do not edit.
 *
 * Produced by `python scripts/generate_reference.py` from the argparse parsers
 * in `succession/cli.py` and `succession/acp_cli.py`, so the guide in this app
 * cannot describe a command the tool does not have, or miss one it does.
 *
 * Before this existed the web app named five of nineteen commands and the
 * README omitted three. Both were written by hand.
 */

export interface CommandFlag {
  names: string[];
  required: boolean;
  help: string;
  choices: string[];
  positional: boolean;
}

export interface Command {
  name: string;
  help: string;
  flags: CommandFlag[];
}

export interface CommandGroup {
  title: string;
  note: string;
  commands: string[];
}

export interface EnvVar {
  name: string;
  help: string;
}

export interface Reference {
  succession: Command[];
  "succession-acp": Command[];
  env: EnvVar[];
  groups: CommandGroup[];
}

export const REFERENCE: Reference = '''


def markdown(reference: dict) -> str:
    """The same reference as prose, for the README.

    Grouped rather than alphabetical, because a flat list of nineteen tells a
    reader nothing about which to run first.
    """
    by_name = {c["name"]: c for c in reference["succession"]}
    lines: list[str] = [
        BEGIN,
        "",
        "<!-- Written by scripts/generate_reference.py from the argparse",
        "     parsers themselves. Do not edit by hand: CI regenerates this",
        "     block and fails on a diff. -->",
        "",
    ]

    for group in reference["groups"]:
        lines += [f"### {group['title']}", "", group["note"], "", "```bash"]
        for name in group["commands"]:
            command = by_name[name]
            required = [
                f.get("names", [""])[0]
                for f in command["flags"]
                if f.get("required") and not f.get("positional")
            ]
            positional = [
                f.get("names", [""])[0] for f in command["flags"] if f.get("positional")
            ]
            parts = " ".join(positional + [f"{r} …" for r in required])
            usage = f"succession {name}{(' ' + parts) if parts else ''}"
            lines.append(f"{usage:<58}# {command['help']}")
        lines += ["```", ""]

    lines += ["### Virtuals ACP", "", "```bash"]
    for command in reference["succession-acp"]:
        lines.append(f"{'succession-acp ' + command['name']:<58}# {command['help']}")
    lines += ["```", "", "### Environment", "", "| Variable | What it is for |", "|---|---|"]
    for var in reference["env"]:
        lines.append(f"| `{var['name']}` | {var['help']} |")

    lines += ["", END]
    return "\n".join(lines)


def main() -> int:
    reference = build_reference()

    body = json.dumps(reference, indent=2, sort_keys=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(f"{HEADER}{body};\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(reference['succession'])} commands)")

    text = README.read_text("utf-8")
    if BEGIN in text and END in text:
        head = text.split(BEGIN)[0]
        tail = text.split(END, 1)[1]
        README.write_text(head + markdown(reference) + tail, encoding="utf-8")
        print(f"wrote the generated block in {README}")
    else:
        print(f"note: {README} has no generated block; skipping it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
