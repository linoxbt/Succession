from __future__ import annotations

import pytest

from succession.demokeys import BUYER, SELLER
from succession.memory.sibyl import open_tenant
from succession.seed import SELLER_AGENT_ID, seed_seller


@pytest.fixture
def seller(tmp_path):
    """A seeded seller tenant in its own store file."""
    mem = open_tenant(tmp_path / "seller.db", "tenant-seller")
    seed_seller(mem)
    return mem


@pytest.fixture
def buyer(tmp_path):
    """An empty buyer tenant, in a *separate* store file.

    Separate files, not two tenants in one file. The spec's whole point is that
    the transfer must work across genuinely independent infrastructure; sharing
    a SQLite file would let a bug that depends on shared state pass here and
    fail on the second machine.
    """
    return open_tenant(tmp_path / "buyer.db", "tenant-buyer")


@pytest.fixture
def agent_id():
    return SELLER_AGENT_ID
