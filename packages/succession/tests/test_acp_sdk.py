"""Exercise the installed ACP SDK surface without contacting a registry."""
from unittest.mock import patch

import pytest

from succession.acp import LiveACP
from succession.demokeys import SELLER


def test_live_adapter_constructs_the_installed_sdk_without_a_task_socket(monkeypatch):
    sdk = pytest.importorskip('virtuals_acp.client')
    from virtuals_acp.configs.configs import BASE_SEPOLIA_CONFIG
    from virtuals_acp.contract_clients.contract_client import ACPContractClient

    monkeypatch.setenv('WHITELISTED_WALLET_PRIVATE_KEY', SELLER.private_key)
    monkeypatch.setenv('AGENT_WALLET_ADDRESS', SELLER.address)
    monkeypatch.setenv('ACP_ENTITY_ID', '417')

    def initialize_contract(instance, wallet_private_key, agent_wallet_address, entity_id, config):
        # Only the network-bound constructor is replaced. autospec enforces
        # the actual SDK signature; the enclosing API client is the real class.
        instance.agent_wallet_address = agent_wallet_address
        instance.config = config
        assert wallet_private_key == SELLER.private_key
        assert entity_id == 417
        assert config is BASE_SEPOLIA_CONFIG

    with patch.object(ACPContractClient, '__init__', autospec=True,
                      side_effect=initialize_contract) as constructor:
        with patch.object(sdk.socketio, 'Client', side_effect=AssertionError('read path opened a socket')):
            source = LiveACP()
            client = source.client
            assert isinstance(client, sdk.VirtualsACP)
            assert source.wallet_address == SELLER.address
            assert source.client is client
            assert callable(client.get_agent)
            assert callable(client.get_completed_jobs)
            assert callable(client.get_cancelled_jobs)
            constructor.assert_called_once()
