"""
Integration tests — require live Arc testnet connection.

These tests are skipped by default and only run with:
  pytest -m integration

They need real environment variables:
  ANTHROPIC_API_KEY, ARC_RPC_URL (pointing to arc-testnet.drpc.org)

They do NOT require ARC_PRIVATE_KEY (read-only operations only).
"""

import pytest

# Arc testnet well-known address with activity (Circle deployer / faucet)
_KNOWN_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest.mark.integration
def test_rpc_connection_returns_block_number():
    """Can connect to Arc testnet and fetch the current block number."""
    from arc_devkit.core.connection import get_web3

    w3 = get_web3()
    block = w3.eth.block_number
    assert isinstance(block, int)
    assert block > 0


@pytest.mark.integration
def test_chain_id_is_arc_testnet():
    """Arc testnet chain ID is 5042002."""
    from arc_devkit.core.connection import get_web3

    w3 = get_web3()
    assert w3.eth.chain_id == 5042002


@pytest.mark.integration
def test_gas_price_is_positive():
    """Arc testnet returns a positive gas price."""
    from arc_devkit.core.connection import get_web3

    w3 = get_web3()
    assert w3.eth.gas_price > 0


@pytest.mark.integration
def test_estimate_transfer_returns_cost():
    """Gas cost estimate for a transfer returns a positive value."""
    from arc_devkit.core.gas import estimate_transfer

    est = estimate_transfer(to=_KNOWN_ADDRESS, amount_usdc=1.0)
    assert est["gas_limit"] > 0
    assert float(est["custo_usdc"]) >= 0


@pytest.mark.integration
def test_get_balance_zero_address():
    """Balance of the zero address is readable (may be 0 or non-zero)."""
    from arc_devkit.core.wallet import get_balance

    result = get_balance(_KNOWN_ADDRESS)
    assert "balance_usdc" in result
    assert "address" in result


@pytest.mark.integration
def test_portfolio_analyze_zero_address():
    """PortfolioAnalyzer.analyze runs without error on the zero address."""
    from arc_devkit.analytics.portfolio import PortfolioAnalyzer

    analyzer = PortfolioAnalyzer()
    snapshot = analyzer.analyze(_KNOWN_ADDRESS, scan_blocks=5)
    assert snapshot.address.startswith("0x")
    assert snapshot.native_balance >= 0
    assert snapshot.blocks_scanned >= 1


@pytest.mark.integration
def test_copilot_ask_returns_non_empty_string():
    """DevCopilot.ask() returns a non-empty string from the real API."""
    from arc_devkit.copilot.agent import DevCopilot

    copilot = DevCopilot()
    response = copilot.ask("What is the Arc blockchain? Answer in one sentence.")
    assert isinstance(response, str)
    assert len(response) > 10


@pytest.mark.integration
def test_event_listener_poll_no_error():
    """EventListener.poll() completes without error on the live chain."""
    from arc_devkit.events.listener import EventListener

    listener = EventListener(from_block="latest")
    result = listener.poll()
    assert isinstance(result, list)
