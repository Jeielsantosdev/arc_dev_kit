"""Unit tests for `arcdevkit fees quote`."""

from unittest.mock import patch

from typer.testing import CliRunner

from arc_devkit.cli.main import app

runner = CliRunner()


def test_fees_quote_exits_zero(mock_web3):
    mock_web3.eth.gas_price = 1_000_000_000
    mock_web3.from_wei.return_value = "0.000021"

    with patch("arc_devkit.core.gas.get_web3", return_value=mock_web3):
        result = runner.invoke(app, ["fees", "quote", "0x" + "b" * 40, "5.0"])

    assert result.exit_code == 0
    assert "Fee" in result.stdout


def test_fees_quote_usdc_token(mock_web3):
    mock_web3.eth.gas_price = 1_000_000_000
    mock_web3.from_wei.return_value = "0.000021"
    mock_web3.eth.contract.return_value.functions.transfer.return_value.estimate_gas.return_value = 65_000

    with patch("arc_devkit.core.gas.get_web3", return_value=mock_web3):
        result = runner.invoke(app, ["fees", "quote", "0x" + "b" * 40, "5.0", "--token", "usdc"])

    assert result.exit_code == 0
