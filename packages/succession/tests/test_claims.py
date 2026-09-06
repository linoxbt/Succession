"""The project's claims about itself, checked against the project.

Succession's whole argument is that its assertions are verifiable. The headline
number was the one assertion with nothing behind it: the README said 259 in
three places, the handoff doc said 248, the landing page said 259, and the suite
collected 319. Three numbers, none of them true, on a page arguing that you
should not have to take a seller's word for anything.

So the count is checked the same way everything else here is: by measuring.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TESTS = Path(__file__).resolve().parent

README = ROOT / "README.md"
LANDING = ROOT / "web" / "src" / "landing" / "Landing.tsx"
FORGE = ROOT / "contracts" / "test" / "ListingContract.t.sol"


def _static_test_functions() -> int:
    """Test functions as written, before parametrisation expands them."""
    total = 0
    for path in sorted(TESTS.glob("test_*.py")):
        tree = ast.parse(path.read_text("utf-8"))
        total += sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )
    return total


def test_the_stated_python_test_count_is_the_real_one(request):
    """Every number the project prints for its own suite must be the true one."""
    collected = request.session.testscollected
    if collected < _static_test_functions():
        pytest.skip("a subset of the suite was selected; the count is meaningless here")

    stated = [int(n) for n in re.findall(r"(\d{3})\s*(?:tests|·)", README.read_text("utf-8"))]
    readme_counts = {
        n for n in re.findall(r"# (\d{3})(?:\s|$)", README.read_text("utf-8"))
    }

    landing = LANDING.read_text("utf-8")
    landing_match = re.search(r"useCountUp\((\d+)\)", landing)
    assert landing_match, "the landing page no longer states a test count"

    claimed = int(landing_match.group(1))
    assert claimed == collected, (
        f"the landing page claims {claimed} tests; the suite collects {collected}"
    )

    for number in readme_counts:
        assert int(number) == collected, (
            f"the README claims {number} tests; the suite collects {collected}"
        )
    assert stated, "the README no longer states a test count"
    assert all(n == collected for n in stated), (
        f"the README badge claims {stated}; the suite collects {collected}"
    )


def test_the_stated_contract_test_count_is_the_real_one():
    """The Foundry number, counted from the Solidity rather than remembered."""
    source = FORGE.read_text("utf-8")
    actual = len(re.findall(r"function\s+(test_|testFuzz_)\w+", source))

    landing = LANDING.read_text("utf-8")
    match = re.search(r"useCountUp\((\d+),\s*[\d.]+\)|contracts?\D{0,40}?(\d{2})\b", landing)
    assert actual == 28, (
        f"the Foundry suite has {actual} tests; every doc that says 28 is now wrong"
    )
    assert match is not None


def test_the_readme_does_not_deny_a_deployment_that_exists():
    """Documentation must not understate what the repo can prove.

    The README said Base Sepolia was "not yet deployed" while
    `deployments/base-sepolia.json` recorded a live contract and
    `transfers.json` recorded five settled sales. Understating is still being
    wrong, and it throws away the strongest evidence the project has.
    """
    record = ROOT / "deployments" / "base-sepolia.json"
    if not record.is_file():
        pytest.skip("no deployment record; nothing to contradict")

    deployed = json.loads(record.read_text("utf-8")).get("listing_contract")
    assert deployed, "the deployment record names no contract"

    text = README.read_text("utf-8").lower()
    for denial in ("not yet deployed to base", "not deployed to base"):
        assert denial not in text, (
            f"the README says {denial!r} while {deployed} is recorded as deployed"
        )


def test_the_readme_does_not_claim_the_two_suites_are_identical():
    """They are not, and saying so invites a reader to check and lose trust.

    The Foundry suite covers a fee-taking token, escrow isolation and a fuzz
    case that the Python suite does not; the Python suite covers a token that
    returns false, double-buying and the registration URI that Foundry does not.
    """
    text = README.read_text("utf-8").lower()
    assert "cover the same scenarios" not in text
