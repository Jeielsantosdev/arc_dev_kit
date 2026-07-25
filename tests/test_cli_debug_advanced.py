"""Unit tests for `arcdevkit debug trace` and `arcdevkit debug compare`."""

from unittest.mock import patch

from typer.testing import CliRunner

from arc_devkit.cli.main import app

runner = CliRunner()

_H1 = "0x" + "a" * 64
_H2 = "0x" + "b" * 64


class TestDebugTrace:
    def test_trace_supported_prints_json(self, mock_web3):
        result_payload = {
            "hash": _H1,
            "supported": True,
            "trace": {"type": "CALL", "calls": []},
            "error": None,
        }
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch(
                "arc_devkit.debugger.tx_analyzer.TxAnalyzer.trace_transaction",
                return_value=result_payload,
            ),
        ):
            result = runner.invoke(app, ["debug", "trace", _H1])
        assert result.exit_code == 0

    def test_trace_unsupported_exits_nonzero(self, mock_web3):
        result_payload = {
            "hash": _H1,
            "supported": False,
            "trace": None,
            "error": "debug_traceTransaction is not available on this RPC: Method not found.",
        }
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch(
                "arc_devkit.debugger.tx_analyzer.TxAnalyzer.trace_transaction",
                return_value=result_payload,
            ),
        ):
            result = runner.invoke(app, ["debug", "trace", _H1])
        assert result.exit_code == 1
        assert "Not available" in result.stdout


class TestDebugCompare:
    def test_compare_shows_both_transactions(self, mock_web3):
        r1 = {
            "hash": _H1,
            "status": "success",
            "custo_usdc": "0.001",
            "revert_reason": None,
            "raw_data": {"gas_used": 21_000, "block": 100},
        }
        r2 = {
            "hash": _H2,
            "status": "reverted",
            "custo_usdc": "0.002",
            "revert_reason": 'require failed: "insufficient balance"',
            "raw_data": {"gas_used": 30_000, "block": 101},
        }
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch(
                "arc_devkit.debugger.tx_analyzer.TxAnalyzer.analyze",
                side_effect=[r1, r2],
            ),
        ):
            result = runner.invoke(app, ["debug", "compare", _H1, _H2])

        assert result.exit_code == 0
        assert "success" in result.stdout
        assert "reverted" in result.stdout
