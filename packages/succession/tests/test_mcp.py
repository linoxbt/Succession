"""The MCP server: what an agent can reach, and what it cannot reach by accident.

The interesting assertions here are about the gate. Three tools spend money,
release a decryption key, or seal an agent permanently, and sealing has no undo.
An agent enumerating its own tools should not be able to end its own memory's
life because a description sounded useful.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("mcp")

from succession.mcp_server import REFUSAL, WRITE_GATE, build_server, writes_allowed

READ_TOOLS = {"inventory", "preview", "value", "prove", "audit",
              "marketplace_listings", "activity"}
WRITE_TOOLS = {"list_for_sale", "fulfil", "claim", "buy", "evaluate"}


def _tools():
    return asyncio.run(build_server().list_tools())


def test_every_cli_capability_is_reachable():
    """Full parity was the requirement, so the whole surface has to be here."""
    names = {t.name for t in _tools()}
    assert READ_TOOLS <= names
    assert WRITE_TOOLS <= names


def test_writes_are_closed_unless_the_operator_opens_them(monkeypatch):
    monkeypatch.delenv(WRITE_GATE, raising=False)
    assert writes_allowed() is False
    monkeypatch.setenv(WRITE_GATE, "1")
    assert writes_allowed() is True


def test_a_transacting_tool_refuses_rather_than_failing_obscurely(monkeypatch):
    """The refusal has to explain itself, or an agent will just retry it."""
    monkeypatch.delenv(WRITE_GATE, raising=False)
    server = build_server()

    result = asyncio.run(
        server.call_tool(
            "claim",
            {
                "db": "/tmp/does-not-matter.db",
                "tenant": "t",
                "listing": "listing-0",
                "marketplace": "http://127.0.0.1:1",
            },
        )
    )
    text = str(result)
    assert "refused" in text.lower()
    assert WRITE_GATE in text
    assert "no undo" in text.lower(), "the refusal must say why it is gated"


def test_the_refusal_names_what_is_irreversible():
    assert "seals an agent" in REFUSAL
    assert "no undo" in REFUSAL


def test_a_read_tool_needs_no_gate(monkeypatch):
    """Reading and verifying must work out of the box, or the server is useless."""
    monkeypatch.delenv(WRITE_GATE, raising=False)
    server = build_server()
    result = asyncio.run(server.call_tool("audit", {}))
    text = str(result)
    assert "refused" not in text.lower()
    assert "categories-transfer" in text


def test_every_transacting_tool_says_so_in_its_description():
    """An agent choosing a tool reads the description, not the source."""
    for tool in _tools():
        if tool.name in WRITE_TOOLS:
            assert WRITE_GATE in (tool.description or ""), tool.name


def test_tools_never_request_private_keys():
    for tool in _tools():
        assert 'private_key' not in str(tool.input_schema), tool.name


def test_command_result_captures_failures_without_exiting_the_server():
    from succession.mcp_server import _run_cli
    result = _run_cli(['not-a-real-command'])
    assert result['ok'] is False
    assert result['exit_code'] == 2
    assert 'invalid choice' in result['error']


def test_cli_bridge_gates_mutations_before_execution(monkeypatch):
    monkeypatch.delenv(WRITE_GATE, raising=False)
    result = asyncio.run(build_server().call_tool('run_command', {'command':'export', 'arguments':[]}))
    assert 'refused' in str(result)


def test_cli_bridge_enumerates_every_parser_command():
    import ast
    from pathlib import Path
    from succession import cli
    tree = ast.parse(Path(cli.__file__).read_text())
    names = {node.args[0].value for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
             and node.func.attr == 'add_parser' and node.args and isinstance(node.args[0], ast.Constant)}
    tool = next(t for t in _tools() if t.name == 'run_command')
    assert set(tool.input_schema['properties']['command']['enum']) == names


def test_quote_tool_uses_remembered_rules_without_write_opt_in(seller, monkeypatch):
    monkeypatch.delenv(WRITE_GATE, raising=False)
    result = asyncio.run(build_server().call_tool('quote', {
        'db': str(seller.client.storage.db_path), 'tenant': seller.tenant_id,
        'counterparty': 'Tallgrass Brewing', 'target': '1000', 'cost': '800',
    }))
    assert '1040.00' in str(result)
    assert '879.13' in str(result)
    assert 'margin-floor' in str(result)
