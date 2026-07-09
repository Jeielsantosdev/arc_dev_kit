"""Tests for network profiles (arc_devkit.networks) and config resolution."""

import pytest

from arc_devkit.config import _load_settings
from arc_devkit.networks import (
    MAINNET,
    NETWORKS,
    TESTNET,
    ZERO_ADDRESS,
    Network,
    available_networks,
    get_network,
)

# ---------------------------------------------------------------------------
# networks.py — registry
# ---------------------------------------------------------------------------


def test_get_network_e_case_insensitive():
    """get_network() resolves profile names regardless of case/whitespace."""
    assert get_network("testnet") is TESTNET
    assert get_network("TESTNET") is TESTNET
    assert get_network("  Mainnet  ") is MAINNET


def test_get_network_desconhecida_levanta_valueerror():
    """An unknown profile name raises ValueError listing the valid options."""
    with pytest.raises(ValueError, match="Unknown network"):
        get_network("polygon")


def test_available_networks_lista_perfis():
    """available_networks() returns exactly the registered profile keys."""
    assert available_networks() == tuple(NETWORKS)
    assert set(available_networks()) == {"testnet", "mainnet"}


def test_testnet_tem_chain_id_e_rpc_reais():
    """The testnet profile carries the known chain ID and RPC endpoint."""
    assert TESTNET.chain_id == 5042002
    assert TESTNET.rpc_url == "https://arc-testnet.drpc.org"
    assert TESTNET.is_placeholder is False


def test_mainnet_e_placeholder_sem_rpc():
    """Mainnet is a placeholder with no RPC until launch."""
    assert MAINNET.is_placeholder is True
    assert MAINNET.rpc_urls == ()
    assert MAINNET.rpc_url == ""


def test_contract_lookup_e_case_insensitive():
    """contract() resolves canonical keys case-insensitively; unknown → None."""
    assert TESTNET.contract("usdc") == ZERO_ADDRESS
    assert TESTNET.contract("EURC") == ZERO_ADDRESS
    assert TESTNET.contract("CCTP_TOKEN_MESSENGER") == ZERO_ADDRESS
    assert TESTNET.contract("does_not_exist") is None


def test_explorer_urls_quando_definido():
    """Explorer URL builders join base + path and strip trailing slashes."""
    net = Network(
        name="custom",
        chain_id=1,
        rpc_urls=("https://rpc",),
        explorer_url="https://scan.example/",
        contracts={},
    )
    assert net.explorer_tx_url("0xabc") == "https://scan.example/tx/0xabc"
    assert net.explorer_address_url("0xdef") == "https://scan.example/address/0xdef"


def test_explorer_urls_none_quando_vazio():
    """Explorer builders return None when no explorer is configured."""
    assert TESTNET.explorer_url == ""
    assert TESTNET.explorer_tx_url("0xabc") is None
    assert TESTNET.explorer_address_url("0xabc") is None


# ---------------------------------------------------------------------------
# config.py — network profile resolution
# ---------------------------------------------------------------------------


def _clear_network_env(monkeypatch):
    for var in ("ARC_NETWORK", "ARC_RPC_URL", "ARC_CHAIN_ID", "ARC_EXPLORER_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")


def test_resolucao_compat_com_env_explicito(monkeypatch):
    """Explicit ARC_RPC_URL/ARC_CHAIN_ID behave as before (backward compat)."""
    _clear_network_env(monkeypatch)
    monkeypatch.setenv("ARC_RPC_URL", "https://arc-testnet.drpc.org")
    monkeypatch.setenv("ARC_CHAIN_ID", "5042002")

    s = _load_settings()

    assert s.network == "testnet"
    assert s.arc_rpc_url == "https://arc-testnet.drpc.org"
    assert s.arc_chain_id == 5042002


def test_resolucao_apenas_por_perfil(monkeypatch):
    """With no explicit RPC/chain, defaults come from the testnet profile."""
    _clear_network_env(monkeypatch)

    s = _load_settings()

    assert s.network == "testnet"
    assert s.arc_rpc_url == "https://arc-testnet.drpc.org"
    assert s.arc_chain_id == 5042002
    assert s.explorer_url == ""


def test_env_sobrescreve_perfil_com_multi_rpc(monkeypatch):
    """Explicit env vars override the profile; comma-separated RPCs are split."""
    _clear_network_env(monkeypatch)
    monkeypatch.setenv("ARC_RPC_URL", "https://a.rpc, https://b.rpc")
    monkeypatch.setenv("ARC_CHAIN_ID", "999")

    s = _load_settings()

    assert s.arc_rpc_urls == ("https://a.rpc", "https://b.rpc")
    assert s.arc_rpc_url == "https://a.rpc"
    assert s.arc_chain_id == 999


def test_network_invalida_levanta_oserror(monkeypatch):
    """An invalid ARC_NETWORK fails fast with OSError."""
    _clear_network_env(monkeypatch)
    monkeypatch.setenv("ARC_NETWORK", "foobar")

    with pytest.raises(OSError, match="Unknown network"):
        _load_settings()


def test_mainnet_sem_rpc_levanta_oserror(monkeypatch):
    """Selecting the mainnet placeholder without an RPC fails with guidance."""
    _clear_network_env(monkeypatch)
    monkeypatch.setenv("ARC_NETWORK", "mainnet")

    with pytest.raises(OSError, match="ARC_RPC_URL"):
        _load_settings()


def test_mainnet_com_rpc_explicito_funciona(monkeypatch):
    """Mainnet works once an explicit RPC is provided; chain ID from profile."""
    _clear_network_env(monkeypatch)
    monkeypatch.setenv("ARC_NETWORK", "mainnet")
    monkeypatch.setenv("ARC_RPC_URL", "https://mainnet.arc")

    s = _load_settings()

    assert s.network == "mainnet"
    assert s.arc_rpc_url == "https://mainnet.arc"
    assert s.arc_chain_id == MAINNET.chain_id


def test_explorer_url_via_env(monkeypatch):
    """ARC_EXPLORER_URL overrides the (empty) profile explorer."""
    _clear_network_env(monkeypatch)
    monkeypatch.setenv("ARC_EXPLORER_URL", "https://scan.arc/")

    s = _load_settings()

    assert s.explorer_url == "https://scan.arc/"
