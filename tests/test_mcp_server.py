"""Unit tests for arc_devkit.mcp_server — the arcdevkit MCP tool server."""

import asyncio
from unittest.mock import patch

import pytest


def test_tools_are_registered():
    from arc_devkit.mcp_server import mcp

    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert {
        "get_balance",
        "get_block_info",
        "get_fee_quote",
        "debug_transaction",
        "get_bridge_status",
        "get_agent_reputation",
        "call_view_function",
    } <= names


def test_get_block_info_tool_calls_web3(mock_web3):
    from arc_devkit.mcp_server import get_block_info

    with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
        result = get_block_info()

    assert "block_number" in result
    assert "chain_id" in result


def test_get_bridge_status_not_found(tmp_path):
    from arc_devkit.mcp_server import get_bridge_status

    with patch("arc_devkit.bridge.store._STORE_DIR", tmp_path):
        result = get_bridge_status("nope")

    assert result["found"] is False


def test_get_fee_quote_invalid_address_raises(mock_web3):
    from arc_devkit.core.validation import ValidationError
    from arc_devkit.mcp_server import get_fee_quote

    with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
        with pytest.raises(ValidationError):
            get_fee_quote("bad-address", 1.0)


def test_get_balance_tool(mock_web3):
    from arc_devkit.mcp_server import get_balance

    mock_web3.eth.get_balance.return_value = 1_000_000_000_000_000_000
    mock_web3.from_wei.return_value = "1.0"

    with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
        result = get_balance("0x" + "b" * 40)

    assert "address" in result


def test_get_balance_tool_invalid_address_raises(mock_web3):
    from arc_devkit.core.validation import ValidationError
    from arc_devkit.mcp_server import get_balance

    with pytest.raises(ValidationError):
        get_balance("not-an-address")


def test_debug_transaction_tool_invalid_hash_raises(mock_web3):
    from arc_devkit.core.validation import ValidationError
    from arc_devkit.mcp_server import debug_transaction

    with pytest.raises(ValidationError):
        debug_transaction("0x123")


def test_call_view_function_tool(mock_web3):
    from arc_devkit.mcp_server import call_view_function

    with patch("arc_devkit.contracts.loader.call_view", return_value=42):
        result = call_view_function(
            contract_address="0x" + "c" * 40,
            abi_json='[{"name":"foo","type":"function","inputs":[],"outputs":[],"stateMutability":"view"}]',
            function_name="foo",
        )

    assert result["result"] == "42"


def test_get_agent_reputation_tool_found(mock_web3):
    from arc_devkit.agents.identity import ReputationScore
    from arc_devkit.mcp_server import get_agent_reputation

    score = ReputationScore(agent_id=1, total_score=80, feedback_count=4)
    with (
        patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
        patch("arc_devkit.agents.identity.AgentRegistry.get_reputation", return_value=score),
    ):
        result = get_agent_reputation(1, "0x" + "1" * 40, "0x" + "2" * 40)

    assert result["found"] is True
    assert result["total_score"] == 80


def test_cli_mcp_serve_invokes_run_server():
    from typer.testing import CliRunner

    from arc_devkit.cli.main import app

    runner = CliRunner()
    with patch("arc_devkit.mcp_server.main") as mock_main:
        result = runner.invoke(app, ["mcp", "serve"])

    assert result.exit_code == 0
    mock_main.assert_called_once()
