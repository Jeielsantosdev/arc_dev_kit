"""Unit tests for PaymentAgent and MonitorAgent."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# PaymentAgent
# ---------------------------------------------------------------------------


class TestPaymentAgent:
    """
    base_agent imports get_web3 and settings lazily (inside __init__).
    The mock_web3 fixture patches Web3 in arc_devkit.core.connection,
    so any call to get_web3() returns the mock automatically.
    """

    def test_get_balance_retorna_saldo(self, mock_web3):
        mock_web3.eth.get_balance.return_value = 1_000_000_000_000_000_000
        mock_web3.from_wei.return_value = Decimal("1.0")

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        result = agent.get_balance()

        assert "address" in result
        assert "balance_wei" in result

    def test_get_balance_sem_chave_retorna_erro(self, mock_web3):
        from arc_devkit.agents.payment_agent import PaymentAgent

        # conftest does not set ARC_PRIVATE_KEY → settings.arc_private_key = None
        agent = PaymentAgent(private_key=None)
        result = agent.get_balance()

        assert "error" in result

    def test_execute_sem_chave_retorna_erro(self, mock_web3):
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=None)
        result = agent.execute(to="0x" + "b" * 40, amount_usdc=1.0)

        assert result["status"] == "error"

    def test_execute_assina_sem_enviar(self, mock_web3):
        mock_web3.eth.get_transaction_count.return_value = 0
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.eth.chain_id = 7_777_777
        mock_web3.to_wei.return_value = 1_000_000_000_000_000_000

        signed_mock = MagicMock()
        signed_mock.raw_transaction = b"\x01\x02\x03"
        mock_web3.eth.account.sign_transaction.return_value = signed_mock

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        result = agent.execute(to="0x" + "b" * 40, amount_usdc=1.0, enviar=False)

        assert result["status"] == "signed"
        assert "raw_transaction" in result
        mock_web3.eth.send_raw_transaction.assert_not_called()

    def test_execute_envia_quando_flag_ativa(self, mock_web3):
        mock_web3.eth.get_transaction_count.return_value = 0
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.eth.chain_id = 7_777_777
        mock_web3.to_wei.return_value = 1_000_000_000_000_000_000
        mock_web3.eth.send_raw_transaction.return_value = bytes.fromhex("deadbeef")

        signed_mock = MagicMock()
        signed_mock.raw_transaction = b"\x01\x02\x03"
        mock_web3.eth.account.sign_transaction.return_value = signed_mock

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        # wait_receipt=False to avoid polling a receipt in unit tests
        result = agent.execute(to="0x" + "b" * 40, amount_usdc=1.0, enviar=True, wait_receipt=False)

        assert result["status"] == "sent"
        assert "tx_hash" in result
        mock_web3.eth.send_raw_transaction.assert_called_once()


# ---------------------------------------------------------------------------
# MonitorAgent
# ---------------------------------------------------------------------------


class TestMonitorAgent:
    def test_get_balance_retorna_saldo_monitorado(self, mock_web3):
        mock_web3.eth.get_balance.return_value = 500_000_000
        mock_web3.from_wei.return_value = "0.5"

        from arc_devkit.agents.monitor_agent import MonitorAgent

        addr = "0x" + "c" * 40
        agent = MonitorAgent(watched_address=addr)
        result = agent.get_balance()

        # get_balance() returns a dict keyed by address (multi-wallet support)
        assert len(result) == 1
        info = next(iter(result.values()))
        assert "address" in info
        assert "balance_wei" in info

    def test_execute_detecta_mudanca_de_saldo(self, mock_web3):
        # First call (init): base balance; second and third: loop iterations
        mock_web3.eth.get_balance.side_effect = [100, 200, 200]

        captured_events = []

        def _cb(evt):
            captured_events.append(evt)

        from arc_devkit.agents.monitor_agent import MonitorAgent

        with patch("time.sleep"):  # avoid real sleep
            agent = MonitorAgent(watched_address="0x" + "c" * 40, interval_seconds=1)
            agent.execute(callback=_cb, max_iterations=2)

        assert len(captured_events) == 1
        assert captured_events[0]["type"] == "credit"
        assert captured_events[0]["change_wei"] == "100"

    def test_execute_sem_mudanca_nao_chama_callback(self, mock_web3):
        mock_web3.eth.get_balance.return_value = 100
        calls = []

        from arc_devkit.agents.monitor_agent import MonitorAgent

        with patch("time.sleep"):
            agent = MonitorAgent(watched_address="0x" + "c" * 40, interval_seconds=1)
            agent.execute(callback=lambda e: calls.append(e), max_iterations=3)

        assert len(calls) == 0

    def test_stop_encerra_loop(self, mock_web3):
        mock_web3.eth.get_balance.return_value = 100

        from arc_devkit.agents.monitor_agent import MonitorAgent

        with patch("time.sleep"):
            agent = MonitorAgent(watched_address="0x" + "c" * 40, interval_seconds=1)
            result = agent.execute(max_iterations=1)

        assert result["status"] == "done"
        assert result["iterations"] == 1
