"""The reference cannot describe a tool that does not exist, or miss one that does.

Documentation drifted here before: the web app named five of nineteen commands
and the README omitted three. The fix was to stop writing the list by hand, and
these are the tests that keep it honest, including the generated file that the
app renders.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from succession import cli
from succession.reference import ENV, GROUPS, build_reference

ROOT = Path(__file__).resolve().parents[3]
GENERATED = ROOT / "web" / "src" / "app" / "reference.ts"


def test_the_reference_is_the_parser():
    """Every command the parser accepts is described, and nothing else is."""
    reference = build_reference()
    described = {c["name"] for c in reference["succession"]}

    # Read the real parser the same way the CLI does, by running it.
    listed = set(
        re.findall(
            r"[\w-]+",
            subprocess.run(
                [sys.executable, "-m", "succession.cli", "--help"],
                capture_output=True, text=True, check=True,
            ).stdout.split("{", 1)[1].split("}", 1)[0],
        )
    )
    assert described == listed, (
        f"described but not real: {described - listed}; "
        f"real but undescribed: {listed - described}"
    )


def test_every_command_carries_its_help_and_flags():
    for entry in build_reference()["succession"]:
        assert entry["help"], f"{entry['name']} has no help text"
        for flag in entry["flags"]:
            assert flag["names"], f"{entry['name']} has an unnamed flag"


def test_every_grouped_command_exists_and_every_command_is_grouped():
    """A group naming a command that was renamed would send a reader nowhere."""
    reference = build_reference()
    real = {c["name"] for c in reference["succession"]}
    grouped = {name for _t, _n, names in GROUPS for name in names}

    assert grouped <= real, f"grouped but not real: {grouped - real}"
    assert real <= grouped, f"real but ungrouped: {real - grouped}"


def test_every_documented_environment_variable_is_read_somewhere():
    """A variable nobody reads is a promise the tool does not keep."""
    source = "\n".join(
        p.read_text("utf-8")
        for p in (ROOT / "packages" / "succession" / "src").rglob("*.py")
    )
    for name, help_text in ENV:
        assert name in source, f"{name} is documented but read nowhere"
        assert help_text.strip(), f"{name} has no explanation"


def test_the_generated_file_is_current():
    """The same guard the contract ABI has, and for the same reason.

    A generated file edited by hand kept CI red for twenty-seven commits. This
    one is rendered by the app, so a stale copy would show a reader a command
    that no longer takes the flag it names.
    """
    if not GENERATED.is_file():
        pytest.skip("the web app is not present in this checkout")

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_reference.py")],
        capture_output=True, check=True,
    )
    regenerated = GENERATED.read_text("utf-8")
    body = regenerated.split("export const REFERENCE: Reference = ", 1)[1].rstrip().rstrip(";")
    parsed = json.loads(body)

    assert {c["name"] for c in parsed["succession"]} == {
        c["name"] for c in build_reference()["succession"]
    }


def test_the_bare_command_names_only_real_commands(capsys):
    """The guide is prose rather than generated, so it is checked instead."""
    cli.main([])
    guide = capsys.readouterr().out
    real = {c["name"] for c in build_reference()["succession"]}

    for match in re.findall(r"succession ([a-z-]+)", guide):
        if match in {"cli", "acp", "mcp"}:
            continue
        assert match in real, f"the guide names `succession {match}`, which does not exist"
