"""Unit tests for arc_devkit.debugger.tx_analyzer."""

import json
import tempfile
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tx(
    from_addr: str = "0x" + "a" * 40,
    to_addr: str = "0x" + "b" * 40,
    value: int = 0,
    gas: int = 21_000,
    gas_price: int = 1_000_000_000,
    input_data: str = "0x",
) -> MagicMock:
    tx = MagicMock()
    tx.get.side_effect = lambda k, d=None: {
        "from": from_addr,
        "to": to_addr,
        "value": value,
        "gas": gas,
        "gasPrice": gas_price,
        "input": input_data,
    }.get(k, d)
    tx.__getitem__ = lambda self, k: tx.get(k)
    return tx


def _make_receipt(status: int = 1, gas_used: int = 21_000, block: int = 100) -> MagicMock:
    receipt = MagicMock()
    receipt.get.side_effect = lambda k, d=None: {
        "status": status,
        "gasUsed": gas_used,
        "blockNumber": block,
        "logs": [],
    }.get(k, d)
    return receipt


def _make_w3(tx=None, receipt=None) -> MagicMock:
    w3 = MagicMock()
    w3.eth.get_transaction.return_value = tx or _make_tx()
    w3.eth.get_transaction_receipt.return_value = receipt or _make_receipt()
    w3.from_wei.return_value = "0.000021"
    return w3


# ---------------------------------------------------------------------------
# decode_revert_bytes
# ---------------------------------------------------------------------------


class TestDecodeRevertBytes:
    def test_standard_require_message(self):
        from eth_abi import encode

        from arc_devkit.debugger.tx_analyzer import decode_revert_bytes

        # Build Error(string) payload
        selector = bytes.fromhex("08c379a0")
        payload = selector + encode(["string"], ["Insufficient balance"])
        result = decode_revert_bytes(payload)
        assert "Insufficient balance" in result
        assert "require failed" in result

    def test_panic_overflow(self):
        from eth_abi import encode

        from arc_devkit.debugger.tx_analyzer import decode_revert_bytes

        selector = bytes.fromhex("4e487b71")
        payload = selector + encode(["uint256"], [0x11])
        result = decode_revert_bytes(payload)
        assert "overflow" in result.lower() or "0x11" in result

    def test_empty_data(self):
        from arc_devkit.debugger.tx_analyzer import decode_revert_bytes

        result = decode_revert_bytes(b"")
        assert "empty revert" in result

    def test_unknown_selector_fallback(self):
        from arc_devkit.debugger.tx_analyzer import decode_revert_bytes

        result = decode_revert_bytes(bytes.fromhex("deadbeef" + "00" * 32))
        assert "unknown revert" in result or "deadbeef" in result

    def test_custom_error_with_abi(self):
        from eth_abi import encode

        from arc_devkit.debugger.tx_analyzer import decode_revert_bytes

        abi = [
            {
                "type": "error",
                "name": "InsufficientFunds",
                "inputs": [{"name": "available", "type": "uint256"}],
            }
        ]
        # Compute the correct selector for InsufficientFunds(uint256)
        from web3 import Web3

        selector = Web3.keccak(text="InsufficientFunds(uint256)")[:4]
        payload = selector + encode(["uint256"], [42])
        result = decode_revert_bytes(payload, abi=abi)
        assert "InsufficientFunds" in result
        assert "42" in result

    def test_custom_error_no_args(self):
        from arc_devkit.debugger.tx_analyzer import decode_revert_bytes
        from web3 import Web3

        abi = [{"type": "error", "name": "Unauthorized", "inputs": []}]
        selector = Web3.keccak(text="Unauthorized()")[:4]
        result = decode_revert_bytes(selector, abi=abi)
        assert "Unauthorized" in result


# ---------------------------------------------------------------------------
# TxAnalyzer.analyze()
# ---------------------------------------------------------------------------


class TestTxAnalyzerAnalyze:
    def _analyzer(self, tx=None, receipt=None):
        from arc_devkit.debugger.tx_analyzer import TxAnalyzer

        w3 = _make_w3(tx=tx, receipt=receipt)
        with patch("arc_devkit.debugger.tx_analyzer.get_web3", return_value=w3):
            return TxAnalyzer(w3=w3)

    def test_successful_tx_basic_keys(self, mock_anthropic):
        analyzer = self._analyzer()
        with patch("arc_devkit.copilot.agent.DevCopilot.ask", return_value="AI response"):
            result = analyzer.analyze("0x" + "a" * 64)

        assert result["status"] == "success"
        assert result["revert_reason"] is None
        assert result["decoded_input"] is None
        assert "hash" in result
        assert "custo_usdc" in result

    def test_reverted_tx_has_status(self, mock_anthropic):
        receipt = _make_receipt(status=0)
        analyzer = self._analyzer(receipt=receipt)

        # eth_call replay raises with no useful data → fallback message
        analyzer._w3.eth.call.side_effect = Exception("execution reverted")
        with patch("arc_devkit.copilot.agent.DevCopilot.ask", return_value="AI"):
            result = analyzer.analyze("0x" + "b" * 64)

        assert result["status"] == "reverted"
        assert result["error"] is not None

    def test_reverted_tx_decodes_require(self, mock_anthropic):
        from eth_abi import encode

        receipt = _make_receipt(status=0)
        analyzer = self._analyzer(receipt=receipt)

        selector = bytes.fromhex("08c379a0")
        revert_data = "0x" + (selector + encode(["string"], ["Only owner"])).hex()

        err = Exception("execution reverted")
        err.data = revert_data
        analyzer._w3.eth.call.side_effect = err

        with patch("arc_devkit.copilot.agent.DevCopilot.ask", return_value="AI"):
            result = analyzer.analyze("0x" + "c" * 64)

        assert result["revert_reason"] is not None
        assert "Only owner" in result["revert_reason"]

    def test_rpc_error_returns_error_status(self, mock_anthropic):
        from arc_devkit.debugger.tx_analyzer import TxAnalyzer

        w3 = MagicMock()
        w3.eth.get_transaction.side_effect = Exception("RPC error")
        analyzer = TxAnalyzer(w3=w3)
        result = analyzer.analyze("0x" + "d" * 64)

        assert result["status"] == "error"
        assert "RPC error" in result["error"]

    def test_with_abi_decodes_input(self, mock_anthropic):
        from arc_devkit.debugger.tx_analyzer import TxAnalyzer

        abi = [
            {
                "type": "function",
                "name": "transfer",
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                ],
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
            }
        ]

        # Provide non-empty calldata so _decode_input doesn't early-return
        tx = _make_tx(input_data="0xa9059cbb" + "00" * 64)
        w3 = _make_w3(tx=tx)

        mock_fn = MagicMock()
        mock_fn.fn_name = "transfer"
        w3.eth.contract.return_value.decode_function_input.return_value = (
            mock_fn,
            {"to": "0x" + "f" * 40, "amount": 1000},
        )

        analyzer = TxAnalyzer(w3=w3)
        with patch("arc_devkit.copilot.agent.DevCopilot.ask", return_value="AI"):
            result = analyzer.analyze("0x" + "e" * 64, abi=abi)

        assert result["decoded_input"] is not None
        assert result["decoded_input"]["function"] == "transfer"

    def test_gas_cost_computed(self, mock_anthropic):
        tx = _make_tx(gas_price=2_000_000_000)
        receipt = _make_receipt(gas_used=21_000)
        analyzer = self._analyzer(tx=tx, receipt=receipt)
        analyzer._w3.from_wei.return_value = "0.000042"

        with patch("arc_devkit.copilot.agent.DevCopilot.ask", return_value="AI"):
            result = analyzer.analyze("0x" + "f" * 64)

        assert result["custo_usdc"] == "0.000042"


# ---------------------------------------------------------------------------
# TxAnalyzer.analyze_batch()
# ---------------------------------------------------------------------------


class TestAnalyzeBatch:
    def test_returns_list_same_length(self, mock_anthropic):
        from arc_devkit.debugger.tx_analyzer import TxAnalyzer

        w3 = _make_w3()
        analyzer = TxAnalyzer(w3=w3)

        hashes = ["0x" + str(i) * 64 for i in range(3)]
        with patch.object(analyzer, "analyze", return_value={"status": "success"}):
            results = analyzer.analyze_batch(hashes)

        assert len(results) == 3

    def test_on_progress_called_for_each(self, mock_anthropic):
        from arc_devkit.debugger.tx_analyzer import TxAnalyzer

        w3 = _make_w3()
        analyzer = TxAnalyzer(w3=w3)
        hashes = ["0x" + "a" * 64, "0x" + "b" * 64]

        calls: list[tuple] = []

        def on_progress(current, total, tx_hash):
            calls.append((current, total))

        with patch.object(analyzer, "analyze", return_value={"status": "success"}):
            analyzer.analyze_batch(hashes, on_progress=on_progress)

        assert calls == [(1, 2), (2, 2)]

    def test_passes_abi_to_analyze(self, mock_anthropic):
        from arc_devkit.debugger.tx_analyzer import TxAnalyzer

        w3 = _make_w3()
        analyzer = TxAnalyzer(w3=w3)
        abi = [{"type": "function", "name": "foo", "inputs": [], "outputs": []}]

        with patch.object(analyzer, "analyze", return_value={}) as mock_analyze:
            analyzer.analyze_batch(["0x" + "a" * 64], abi=abi)

        mock_analyze.assert_called_once_with("0x" + "a" * 64, abi=abi)


# ---------------------------------------------------------------------------
# CLI — arc debug and arc debug-batch
# ---------------------------------------------------------------------------


class TestDebugCLI:
    def test_debug_json_output(self, mock_anthropic):
        from typer.testing import CliRunner

        from arc_devkit.cli.flat import app

        runner = CliRunner()
        tx_hash = "0x" + "a" * 64

        with patch("arc_devkit.debugger.tx_analyzer.TxAnalyzer.analyze") as mock_analyze:
            mock_analyze.return_value = {
                "hash": tx_hash,
                "status": "success",
                "summary": "AI summary",
                "custo_usdc": "0.001",
                "revert_reason": None,
                "decoded_input": None,
                "error": None,
                "suggestion": "",
                "raw_data": {},
            }
            result = runner.invoke(app, ["debug", tx_hash, "--json"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["status"] == "success"
        assert data["revert_reason"] is None

    def test_debug_with_missing_abi_file(self):
        from typer.testing import CliRunner

        from arc_devkit.cli.flat import app

        runner = CliRunner()
        result = runner.invoke(
            app, ["debug", "0x" + "a" * 64, "--abi", "nonexistent.json"]
        )
        assert result.exit_code != 0

    def test_debug_batch_from_txt_file(self, mock_anthropic):
        from typer.testing import CliRunner

        from arc_devkit.cli.flat import app

        hashes = ["0x" + "a" * 64, "0x" + "b" * 64]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("\n".join(hashes))
            f.flush()

            with patch("arc_devkit.debugger.tx_analyzer.TxAnalyzer.analyze_batch") as mock_batch:
                mock_batch.return_value = [
                    {"hash": h, "status": "success", "custo_usdc": "0", "revert_reason": None}
                    for h in hashes
                ]
                runner = CliRunner()
                result = runner.invoke(app, ["debug-batch", f.name, "--json"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data) == 2

    def test_debug_batch_missing_file(self):
        from typer.testing import CliRunner

        from arc_devkit.cli.flat import app

        runner = CliRunner()
        result = runner.invoke(app, ["debug-batch", "no_such_file.txt"])
        assert result.exit_code != 0
