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
WRITE_TOOLS = {"list_for_sale", "fulfil", "claim"}


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
