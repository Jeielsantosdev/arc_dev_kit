"""Unit tests for analytics.portfolio.PortfolioAnalyzer."""

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_w3(
    balance_wei: int = 5_000_000_000_000_000_000,
    from_wei_result: str = "5.0",
    tx_count: int = 3,
    block_number: int = 1_000,
) -> MagicMock:
    """Return a minimal Web3 mock for PortfolioAnalyzer tests."""
    w3 = MagicMock()
    w3.eth.get_balance.return_value = balance_wei
    w3.from_wei.return_value = from_wei_result
    w3.eth.get_transaction_count.return_value = tx_count
    w3.eth.block_number = block_number
    # Default: blocks with no transactions
    w3.eth.get_block.return_value = {"transactions": []}
    return w3


def _make_tx(
    address: str,
    direction: str = "sent",
    value: int = 1_000_000_000_000_000_000,
) -> dict:
    """Return a dict mimicking a web3 full-transaction object."""
    other = "0x" + "b" * 40

    class FakeHash:
        def hex(self):
            return "0x" + "ab" * 32

    return {
        "from": address if direction == "sent" else other,
        "to": other if direction == "sent" else address,
        "value": value,
        "hash": FakeHash(),
    }


# ---------------------------------------------------------------------------
# PortfolioAnalyzer unit tests
# ---------------------------------------------------------------------------


class TestPortfolioAnalyzer:
    def _analyzer(self, **kwargs):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        return PortfolioAnalyzer(w3=_make_w3(**kwargs))

    # --- analyze() structure ---

    def test_analyze_returns_snapshot(self):
        from arc_devkit.analytics.portfolio import PortfolioSnapshot

        snap = self._analyzer().analyze("0x" + "a" * 40, scan_blocks=2)
        assert isinstance(snap, PortfolioSnapshot)

    def test_analyze_native_balance(self):
        snap = self._analyzer(from_wei_result="7.5").analyze("0x" + "a" * 40, scan_blocks=1)
        assert snap.native_balance == Decimal("7.5")

    def test_analyze_nonce(self):
        snap = self._analyzer(tx_count=9).analyze("0x" + "a" * 40, scan_blocks=1)
        assert snap.nonce == 9

    def test_analyze_blocks_scanned(self):
        snap = self._analyzer(block_number=500).analyze("0x" + "a" * 40, scan_blocks=50)
        # from_block = max(0, 500 - 50 + 1) = 451
        # blocks_scanned = 500 - 451 + 1 = 50
        assert snap.blocks_scanned == 50
        assert snap.blocks_to == 500

    def test_analyze_usdc_none_when_placeholder(self):
        """USDC balance is None when contract address is the 0x000 placeholder."""
        snap = self._analyzer().analyze("0x" + "a" * 40, scan_blocks=1)
        assert snap.usdc_balance is None

    def test_analyze_usdc_with_real_contract(self):
        """USDC balance is fetched when a real contract address is provided."""
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        w3 = _make_w3()
        # Patch USDCToken so we don't need a real contract
        with patch("arc_devkit.usdc.token.USDCToken") as MockUSDC:
            mock_token = MagicMock()
            mock_token.balance.return_value = Decimal("100.50")
            MockUSDC.return_value = mock_token

            analyzer = PortfolioAnalyzer(w3=w3, usdc_contract="0x" + "c" * 40)
            snap = analyzer.analyze("0x" + "a" * 40, scan_blocks=1)

        assert snap.usdc_balance == Decimal("100.50")

    def test_analyze_address_checksum(self):
        """analyze() always returns a checksummed address."""
        from web3 import Web3

        raw = "0x" + "a" * 40
        snap = self._analyzer().analyze(raw, scan_blocks=1)
        assert snap.address == Web3.to_checksum_address(raw)

    # --- _compute_activity_score ---

    def test_activity_score_inactive(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        a = PortfolioAnalyzer(w3=_make_w3())
        assert a._compute_activity_score(0) == "inactive"

    def test_activity_score_low(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        a = PortfolioAnalyzer(w3=_make_w3())
        assert a._compute_activity_score(1) == "low"
        assert a._compute_activity_score(5) == "low"

    def test_activity_score_medium(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        a = PortfolioAnalyzer(w3=_make_w3())
        assert a._compute_activity_score(6) == "medium"
        assert a._compute_activity_score(20) == "medium"

    def test_activity_score_high(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        a = PortfolioAnalyzer(w3=_make_w3())
        assert a._compute_activity_score(21) == "high"

    # --- _scan_transactions ---

    def test_scan_finds_sent_tx(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        address = "0x" + "a" * 40
        w3 = _make_w3(block_number=5)
        tx = _make_tx(address, direction="sent")
        w3.eth.get_block.return_value = {"transactions": [tx]}
        w3.eth.get_transaction_receipt.return_value = {"gasUsed": 21_000, "status": 1}
        w3.from_wei.return_value = "1.0"

        analyzer = PortfolioAnalyzer(w3=w3)
        snap = analyzer.analyze(address, scan_blocks=3)

        sent = [t for t in snap.recent_txs if t.direction == "sent"]
        assert len(sent) >= 1
        assert sent[0].status == "success"
        assert sent[0].gas_used == 21_000

    def test_scan_finds_received_tx(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        address = "0x" + "a" * 40
        w3 = _make_w3(block_number=5)
        tx = _make_tx(address, direction="received")
        w3.eth.get_block.return_value = {"transactions": [tx]}
        w3.eth.get_transaction_receipt.return_value = {"gasUsed": 21_000, "status": 1}
        w3.from_wei.return_value = "1.0"

        analyzer = PortfolioAnalyzer(w3=w3)
        snap = analyzer.analyze(address, scan_blocks=3)

        received = [t for t in snap.recent_txs if t.direction == "received"]
        assert len(received) >= 1

    def test_scan_ignores_unrelated_txs(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        my_address = "0x" + "a" * 40
        w3 = _make_w3(block_number=5)
        # tx between two unrelated addresses
        unrelated = {
            "from": "0x" + "c" * 40,
            "to": "0x" + "d" * 40,
            "value": 0,
            "hash": MagicMock(hex=lambda: "0x" + "ff" * 32),
        }
        w3.eth.get_block.return_value = {"transactions": [unrelated]}
        w3.from_wei.return_value = "0.0"

        analyzer = PortfolioAnalyzer(w3=w3)
        snap = analyzer.analyze(my_address, scan_blocks=3)
        assert snap.recent_txs == []

    def test_scan_handles_failed_block_fetch(self):
        """Blocks that raise an exception are silently skipped."""
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        address = "0x" + "a" * 40
        w3 = _make_w3(block_number=5)
        w3.eth.get_block.side_effect = Exception("RPC timeout")
        w3.from_wei.return_value = "0.0"

        analyzer = PortfolioAnalyzer(w3=w3)
        snap = analyzer.analyze(address, scan_blocks=3)
        assert snap.recent_txs == []
        assert snap.activity_score == "inactive"

    def test_scan_tx_hash_prefixed(self):
        """Transaction hash in results always starts with 0x."""
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        address = "0x" + "a" * 40
        w3 = _make_w3(block_number=3)
        tx = _make_tx(address, direction="sent")
        w3.eth.get_block.return_value = {"transactions": [tx]}
        w3.eth.get_transaction_receipt.return_value = {"gasUsed": 21_000, "status": 1}
        w3.from_wei.return_value = "0.0"

        analyzer = PortfolioAnalyzer(w3=w3)
        snap = analyzer.analyze(address, scan_blocks=2)

        for tx_summary in snap.recent_txs:
            assert tx_summary.hash.startswith("0x")

    # --- to_dict ---

    def test_to_dict_is_json_serializable(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        analyzer = PortfolioAnalyzer(w3=_make_w3())
        snap = analyzer.analyze("0x" + "a" * 40, scan_blocks=1)
        data = analyzer.to_dict(snap)
        dumped = json.dumps(data)  # must not raise
        loaded = json.loads(dumped)
        assert loaded["address"] == snap.address

    def test_to_dict_required_keys(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        analyzer = PortfolioAnalyzer(w3=_make_w3())
        snap = analyzer.analyze("0x" + "a" * 40, scan_blocks=1)
        data = analyzer.to_dict(snap)

        for key in (
            "address",
            "native_balance",
            "usdc_balance",
            "nonce",
            "blocks_scanned",
            "blocks_from",
            "blocks_to",
            "activity_score",
            "tx_count",
            "recent_txs",
        ):
            assert key in data, f"Missing key: {key}"

    def test_to_dict_usdc_none_serialized(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        analyzer = PortfolioAnalyzer(w3=_make_w3())
        snap = analyzer.analyze("0x" + "a" * 40, scan_blocks=1)
        assert snap.usdc_balance is None
        data = analyzer.to_dict(snap)
        assert data["usdc_balance"] is None  # JSON null, not string

    def test_to_dict_tx_list_structure(self):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        address = "0x" + "a" * 40
        w3 = _make_w3(block_number=3)
        tx = _make_tx(address, direction="sent")
        w3.eth.get_block.return_value = {"transactions": [tx]}
        w3.eth.get_transaction_receipt.return_value = {"gasUsed": 21_000, "status": 1}
        w3.from_wei.return_value = "1.0"

        analyzer = PortfolioAnalyzer(w3=w3)
        snap = analyzer.analyze(address, scan_blocks=2)
        data = analyzer.to_dict(snap)

        assert data["tx_count"] == len(snap.recent_txs)
        if data["recent_txs"]:
            tx_data = data["recent_txs"][0]
            for key in ("hash", "block", "direction", "value_arc", "gas_used", "status"):
                assert key in tx_data


# ---------------------------------------------------------------------------
# CLI — arc portfolio analyze (via CliRunner)
# ---------------------------------------------------------------------------


class TestPortfolioCLI:
    def test_analyze_command_json_output(self):
        from typer.testing import CliRunner

        from arc_devkit.cli.flat import app

        address = "0x" + "a" * 40

        with (
            patch("arc_devkit.analytics.portfolio.PortfolioAnalyzer.analyze") as mock_analyze,
            patch("arc_devkit.cli.flat._save_history"),
        ):
            from arc_devkit.analytics.portfolio import PortfolioSnapshot

            mock_analyze.return_value = PortfolioSnapshot(
                address=address,
                native_balance=Decimal("2.5"),
                usdc_balance=None,
                nonce=5,
                recent_txs=[],
                blocks_scanned=100,
                blocks_from=900,
                blocks_to=1000,
                activity_score="inactive",
            )

            runner = CliRunner()
            result = runner.invoke(
                app,
                ["portfolio", "analyze", address, "--no-ai", "--json"],
            )

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["address"] == address
        assert data["activity_score"] == "inactive"
        assert data["nonce"] == 5

    def test_analyze_invalid_address(self):
        from typer.testing import CliRunner

        from arc_devkit.cli.flat import app

        runner = CliRunner()
        result = runner.invoke(app, ["portfolio", "analyze", "not-an-address", "--no-ai"])
        assert result.exit_code != 0

    def test_report_missing_file(self):
        from typer.testing import CliRunner

        from arc_devkit.cli.flat import app

        runner = CliRunner()
        result = runner.invoke(app, ["portfolio", "report", "nonexistent.json"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Balance history — save_snapshot / load_history
# ---------------------------------------------------------------------------


class TestBalanceHistory:
    def _make_snapshot(self, address="0x" + "a" * 40, tx_count=3):
        from arc_devkit.analytics.portfolio import PortfolioSnapshot

        return PortfolioSnapshot(
            address=address,
            native_balance=Decimal("1.5"),
            usdc_balance=None,
            nonce=tx_count,
            recent_txs=[],
            blocks_scanned=100,
            blocks_from=900,
            blocks_to=1000,
            activity_score="low",
        )

    def test_save_snapshot_creates_file(self, tmp_path):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        snap = self._make_snapshot()
        analyzer = PortfolioAnalyzer(w3=_make_w3())
        path = analyzer.save_snapshot(snap, history_dir=tmp_path)
        assert path.exists()
        data = path.read_text()
        assert '"native_balance"' in data

    def test_save_snapshot_appends_records(self, tmp_path):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        snap = self._make_snapshot()
        analyzer = PortfolioAnalyzer(w3=_make_w3())
        analyzer.save_snapshot(snap, history_dir=tmp_path)
        analyzer.save_snapshot(snap, history_dir=tmp_path)
        path = tmp_path / f"{snap.address.lower()}.jsonl"
        lines = [line for line in path.read_text().splitlines() if line.strip()]
        assert len(lines) == 2

    def test_save_snapshot_includes_timestamp(self, tmp_path):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        snap = self._make_snapshot()
        analyzer = PortfolioAnalyzer(w3=_make_w3())
        path = analyzer.save_snapshot(snap, history_dir=tmp_path)
        record = json.loads(path.read_text().splitlines()[0])
        assert "timestamp" in record
        assert "T" in record["timestamp"]

    def test_load_history_returns_newest_first(self, tmp_path):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        addr = "0x" + "b" * 40
        snap = self._make_snapshot(address=addr)
        analyzer = PortfolioAnalyzer(w3=_make_w3())
        analyzer.save_snapshot(snap, history_dir=tmp_path)
        analyzer.save_snapshot(snap, history_dir=tmp_path)

        records = PortfolioAnalyzer.load_history(addr, history_dir=tmp_path)
        assert len(records) == 2
        # newest first — second record has a timestamp >= first
        t1 = records[0].get("timestamp", "")
        t2 = records[1].get("timestamp", "")
        assert t1 >= t2

    def test_load_history_empty_when_no_file(self, tmp_path):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        result = PortfolioAnalyzer.load_history("0x" + "c" * 40, history_dir=tmp_path)
        assert result == []

    def test_load_history_limit(self, tmp_path):
        from arc_devkit.analytics.portfolio import PortfolioAnalyzer

        snap = self._make_snapshot()
        analyzer = PortfolioAnalyzer(w3=_make_w3())
        for _ in range(5):
            analyzer.save_snapshot(snap, history_dir=tmp_path)

        records = PortfolioAnalyzer.load_history(snap.address, history_dir=tmp_path, limit=3)
        assert len(records) == 3

    def test_portfolio_history_cli_no_file(self, tmp_path, monkeypatch):
        """arc portfolio history shows friendly message when no history exists."""
        from typer.testing import CliRunner

        from arc_devkit.cli.flat import app

        monkeypatch.setattr("arc_devkit.analytics.portfolio._HISTORY_DIR", tmp_path / "history")
        runner = CliRunner()
        with patch(
            "arc_devkit.analytics.portfolio.PortfolioAnalyzer.load_history", return_value=[]
        ):
            result = runner.invoke(app, ["portfolio", "history", "0x" + "a" * 40])
        assert result.exit_code == 0
        assert "No history" in result.output or "history" in result.output.lower()

    def test_portfolio_history_cli_json_output(self, tmp_path):
        """arc portfolio history --json outputs valid JSON list."""
        from typer.testing import CliRunner

        from arc_devkit.cli.flat import app

        records = [
            {"native_balance": "1.5", "timestamp": "2026-01-01T00:00:00+00:00", "tx_count": 2}
        ]
        runner = CliRunner()
        with patch(
            "arc_devkit.analytics.portfolio.PortfolioAnalyzer.load_history", return_value=records
        ):
            result = runner.invoke(app, ["portfolio", "history", "0x" + "a" * 40, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
