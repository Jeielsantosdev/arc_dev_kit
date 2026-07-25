"""Unit tests for arc_devkit.config — ARC_NETWORK profile fallback."""

import pytest

from arc_devkit.config import _load_settings


def _clear_network_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.delenv("ARC_NETWORK", raising=False)
    monkeypatch.delenv("ARC_RPC_URL", raising=False)
    monkeypatch.delenv("ARC_CHAIN_ID", raising=False)


class TestNetworkFallback:
    def test_default_network_is_testnet_when_unset(self, monkeypatch):
        _clear_network_env(monkeypatch)

        settings = _load_settings()

        assert settings.arc_network == "testnet"
        assert settings.arc_rpc_url == "https://arc-testnet.drpc.org"
        assert settings.arc_chain_id == 5042002
        assert settings.network.name == "testnet"

    def test_explicit_rpc_url_overrides_network_profile(self, monkeypatch):
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_NETWORK", "testnet")
        monkeypatch.setenv("ARC_RPC_URL", "https://custom-rpc.example.com")

        settings = _load_settings()

        assert settings.arc_rpc_url == "https://custom-rpc.example.com"

    def test_explicit_chain_id_overrides_network_profile(self, monkeypatch):
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_RPC_URL", "https://arc-testnet.drpc.org")
        monkeypatch.setenv("ARC_CHAIN_ID", "999999")

        settings = _load_settings()

        assert settings.arc_chain_id == 999999

    def test_mainnet_without_explicit_rpc_raises(self, monkeypatch):
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_NETWORK", "mainnet")

        with pytest.raises(OSError, match="ARC_RPC_URL"):
            _load_settings()

    def test_mainnet_with_explicit_rpc_and_chain_id_works(self, monkeypatch):
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_NETWORK", "mainnet")
        monkeypatch.setenv("ARC_RPC_URL", "https://mainnet-rpc.example.com")
        monkeypatch.setenv("ARC_CHAIN_ID", "1234567")

        settings = _load_settings()

        assert settings.arc_network == "mainnet"
        assert settings.arc_rpc_url == "https://mainnet-rpc.example.com"
        assert settings.arc_chain_id == 1234567

    def test_unknown_network_raises(self, monkeypatch):
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_NETWORK", "not-a-real-network")
        monkeypatch.setenv("ARC_RPC_URL", "https://arc-testnet.drpc.org")

        with pytest.raises(OSError, match="Unknown Arc network"):
            _load_settings()
