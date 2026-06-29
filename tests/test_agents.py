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

    def test_estimate_gas_fallback_on_exception(self, mock_web3):
        mock_web3.eth.estimate_gas.side_effect = Exception("gas fail")

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        result = agent._estimate_gas({"from": agent._address, "to": "0x" + "b" * 40})
        assert result == 21_000

    def test_wait_for_receipt_returns_receipt(self, mock_web3):

        receipt = {"status": 1, "gasUsed": 21_000}
        mock_web3.eth.get_transaction_receipt.return_value = receipt

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        with patch("time.sleep"), patch("time.time", side_effect=[0, 1]):
            result = agent._wait_for_receipt(b"\xde\xad", timeout=10)
        assert result == receipt

    def test_simulate_returns_true_on_success(self, mock_web3):
        mock_web3.eth.call.return_value = b""

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        assert agent._simulate({"to": "0x" + "b" * 40}) is True

    def test_simulate_returns_false_on_revert(self, mock_web3):
        mock_web3.eth.call.side_effect = Exception("revert")

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        assert agent._simulate({"to": "0x" + "b" * 40}) is False

    def test_execute_with_receipt_and_on_success(self, mock_web3):
        mock_web3.eth.get_transaction_count.return_value = 0
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.eth.chain_id = 7_777_777
        mock_web3.to_wei.return_value = 1_000_000_000_000_000_000
        raw_hash = MagicMock()
        raw_hash.hex.return_value = "0x" + "ab" * 32
        mock_web3.eth.send_raw_transaction.return_value = raw_hash
        mock_web3.eth.get_transaction_receipt.return_value = {"status": 1, "gasUsed": 21_000}

        signed_mock = MagicMock()
        signed_mock.raw_transaction = b"\x01\x02"
        mock_web3.eth.account.sign_transaction.return_value = signed_mock

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        success_calls: list = []

        with patch("time.sleep"), patch("time.time", side_effect=[0, 1, 0, 1]):
            result = agent.execute(
                to="0x" + "b" * 40,
                amount_usdc=1.0,
                enviar=True,
                wait_receipt=True,
                on_success=lambda r: success_calls.append(r),
            )

        assert result["status"] == "confirmed"
        assert len(success_calls) == 1

    def test_execute_on_failure_callback(self, mock_web3):
        mock_web3.eth.get_transaction_count.return_value = 0
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.eth.chain_id = 7_777_777
        mock_web3.to_wei.return_value = 1_000_000_000_000_000_000
        mock_web3.eth.account.sign_transaction.side_effect = Exception("signing failed")

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        failure_calls: list = []

        import pytest

        with pytest.raises(Exception, match="signing failed"):
            agent.execute(
                to="0x" + "b" * 40,
                amount_usdc=1.0,
                enviar=True,
                on_failure=lambda e: failure_calls.append(e),
            )

        assert len(failure_calls) == 1

    def test_execute_batch_signs_multiple(self, mock_web3):
        mock_web3.eth.get_transaction_count.return_value = 5
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.eth.chain_id = 7_777_777
        mock_web3.to_wei.return_value = 1_000_000_000_000_000_000

        signed_mock = MagicMock()
        signed_mock.raw_transaction = b"\x01\x02"
        mock_web3.eth.account.sign_transaction.return_value = signed_mock

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        payments = [
            {"to": "0x" + "b" * 40, "amount_usdc": 1.0},
            {"to": "0x" + "c" * 40, "amount_usdc": 2.0},
        ]
        results = agent.execute_batch(payments)

        assert len(results) == 2
        assert all(r["status"] == "signed" for r in results)

    def test_execute_batch_no_key(self, mock_web3):
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=None)
        results = agent.execute_batch([{"to": "0x" + "b" * 40, "amount_usdc": 1.0}])
        assert results[0]["status"] == "error"

    def test_execute_batch_sends_when_enviar_true(self, mock_web3):
        mock_web3.eth.get_transaction_count.return_value = 0
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.eth.chain_id = 7_777_777
        mock_web3.to_wei.return_value = 1_000_000_000_000_000_000
        tx_hash = MagicMock()
        tx_hash.hex.return_value = "0x" + "ab" * 32
        mock_web3.eth.send_raw_transaction.return_value = tx_hash
        signed_mock = MagicMock()
        signed_mock.raw_transaction = b"\x01\x02"
        mock_web3.eth.account.sign_transaction.return_value = signed_mock

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        results = agent.execute_batch([{"to": "0x" + "b" * 40, "amount_usdc": 1.0, "enviar": True}])
        assert results[0]["status"] == "sent"
        assert "tx_hash" in results[0]

    def test_wait_for_receipt_polls_then_confirms(self, mock_web3):
        """Covers the sleep path when first receipt poll returns None."""
        from unittest.mock import patch

        receipt = {"status": 1, "gasUsed": 21_000}
        mock_web3.eth.get_transaction_receipt.side_effect = [None, receipt]

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        with patch("time.sleep") as mock_sleep, patch(
            "time.time", side_effect=[0.0, 1.0, 2.0]
        ):
            result = agent._wait_for_receipt(b"\xde\xad", timeout=10)
        assert result == receipt
        mock_sleep.assert_called_once()

    def test_wait_for_receipt_timeout(self, mock_web3):
        """Covers the None return when timeout is exceeded."""
        from unittest.mock import patch

        mock_web3.eth.get_transaction_receipt.return_value = None

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        with patch("time.sleep"), patch("time.time", side_effect=[0.0, 125.0]):
            result = agent._wait_for_receipt(b"\xde\xad", timeout=120)
        assert result is None

    def test_call_rpc_delegates_to_function(self, mock_web3):
        """Covers BaseAgent._call_rpc proxy."""
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        fn = MagicMock(return_value=99)
        result = agent._call_rpc(fn, "arg1", key="val")
        assert result == 99
        fn.assert_called_once_with("arg1", key="val")

    def test_log_method_does_not_raise(self, mock_web3):
        """Covers BaseAgent.log()."""
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        agent.log("Test log message")

    def test_execute_usdc_signed_no_broadcast(self, mock_web3):
        """token='usdc' path builds ERC-20 transfer and returns signed status."""
        contract_mock = MagicMock()
        built_tx = {
            "from": "0x" + "a" * 40,
            "to": "0x" + "c" * 40,
            "data": "0x" + "aa" * 32,
            "gas": 65_000,
            "gasPrice": 1_000_000_000,
            "nonce": 0,
            "chainId": 7_777_777,
        }
        contract_mock.functions.transfer.return_value.build_transaction.return_value = built_tx
        mock_web3.eth.contract.return_value = contract_mock
        mock_web3.eth.get_transaction_count.return_value = 0
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.eth.chain_id = 7_777_777

        signed_mock = MagicMock()
        signed_mock.raw_transaction = b"\x01\x02\x03"
        mock_web3.eth.account.sign_transaction.return_value = signed_mock

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        result = agent.execute(to="0x" + "b" * 40, amount_usdc=5.0, enviar=False, token="usdc")

        assert result["status"] == "signed"
        assert result["token"] == "usdc"
        assert "raw_transaction" in result
        mock_web3.eth.send_raw_transaction.assert_not_called()

    def test_execute_usdc_sends_when_broadcast(self, mock_web3):
        """token='usdc' with enviar=True broadcasts the ERC-20 tx."""
        contract_mock = MagicMock()
        built_tx = {
            "from": "0x" + "a" * 40,
            "to": "0x" + "c" * 40,
            "data": "0x" + "aa" * 32,
            "gas": 65_000,
            "gasPrice": 1_000_000_000,
            "nonce": 0,
            "chainId": 7_777_777,
        }
        contract_mock.functions.transfer.return_value.build_transaction.return_value = built_tx
        mock_web3.eth.contract.return_value = contract_mock
        mock_web3.eth.get_transaction_count.return_value = 0
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.eth.chain_id = 7_777_777

        raw_hash = MagicMock()
        raw_hash.hex.return_value = "0x" + "cc" * 32
        mock_web3.eth.send_raw_transaction.return_value = raw_hash

        signed_mock = MagicMock()
        signed_mock.raw_transaction = b"\x01\x02"
        mock_web3.eth.account.sign_transaction.return_value = signed_mock

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        result = agent.execute(
            to="0x" + "b" * 40,
            amount_usdc=10.0,
            enviar=True,
            wait_receipt=False,
            token="usdc",
        )

        assert result["status"] == "sent"
        assert result["token"] == "usdc"
        assert result["tx_hash"] == "0x" + "cc" * 32
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

    def test_monitor_restores_state_from_file(self, mock_web3, tmp_path):
        """Covers state file restore on __init__ (lines 83-88)."""
        import json

        from arc_devkit.agents.monitor_agent import MonitorAgent

        addr = "0x" + "c" * 40
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({addr: "999"}))

        agent = MonitorAgent(watched_address=addr, state_file=str(state_file))
        assert agent._last_balances.get(addr) == 999

    def test_monitor_watched_addresses_property(self, mock_web3):
        """Covers watched_addresses property (line 93)."""
        from arc_devkit.agents.monitor_agent import MonitorAgent

        addr = "0x" + "c" * 40
        agent = MonitorAgent(watched_address=addr)
        assert addr.lower() in [a.lower() for a in agent.watched_addresses]

    def test_monitor_saves_state_to_file(self, mock_web3, tmp_path):
        """Covers _save_state (lines 97-103)."""
        from arc_devkit.agents.monitor_agent import MonitorAgent

        addr = "0x" + "c" * 40
        state_file = tmp_path / "state.json"
        mock_web3.eth.get_balance.return_value = 100

        with patch("time.sleep"):
            agent = MonitorAgent(
                watched_address=addr, state_file=str(state_file), interval_seconds=1
            )
            agent.execute(max_iterations=1)

        assert state_file.exists()

    def test_monitor_multiple_addresses(self, mock_web3):
        """Covers watched_addresses list init (line 63)."""
        from arc_devkit.agents.monitor_agent import MonitorAgent

        addrs = ["0x" + "a" * 40, "0x" + "b" * 40]
        mock_web3.eth.get_balance.return_value = 0

        with patch("time.sleep"):
            agent = MonitorAgent(watched_addresses=addrs, interval_seconds=1)
            agent.execute(max_iterations=1)

        assert len(agent.watched_addresses) == 2

    def test_base_agent_call_rpc(self, mock_web3):
        """Covers _call_rpc (line 93)."""
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key="0x" + "a" * 64)
        fn = MagicMock(return_value=77)
        result = agent._call_rpc(fn, "x", y=2)
        assert result == 77
