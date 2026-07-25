"""Unit tests for PaymentAgent security hardening: simulation, gas ceiling, guardrails, RBF."""

import dataclasses
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

_TO = "0x" + "b" * 40
_KEY = "0x" + "a" * 64


@pytest.fixture
def signed_mock(mock_web3):
    signed = MagicMock()
    signed.raw_transaction = b"\x01\x02\x03"
    mock_web3.eth.account.sign_transaction.return_value = signed
    mock_web3.eth.get_transaction_count.return_value = 0
    mock_web3.eth.gas_price = 1_000_000_000
    mock_web3.eth.chain_id = 7_777_777
    mock_web3.to_wei.return_value = 10**18
    mock_web3.eth.send_raw_transaction.return_value = bytes.fromhex("deadbeef")
    return signed


class TestMandatorySimulation:
    def test_simulated_revert_blocks_broadcast(self, mock_web3, signed_mock):
        mock_web3.eth.call.side_effect = Exception("execution reverted")

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=_KEY)
        result = agent.execute(to=_TO, amount_usdc=1.0, enviar=True, wait_receipt=False)

        assert result["status"] == "simulation_failed"
        mock_web3.eth.send_raw_transaction.assert_not_called()

    def test_force_bypasses_simulation(self, mock_web3, signed_mock):
        mock_web3.eth.call.side_effect = Exception("execution reverted")

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=_KEY)
        result = agent.execute(to=_TO, amount_usdc=1.0, enviar=True, wait_receipt=False, force=True)

        assert result["status"] == "sent"
        mock_web3.eth.send_raw_transaction.assert_called_once()

    def test_successful_simulation_allows_broadcast(self, mock_web3, signed_mock):
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=_KEY)
        result = agent.execute(to=_TO, amount_usdc=1.0, enviar=True, wait_receipt=False)

        assert result["status"] == "sent"


class TestGasPriceCeiling:
    def test_gas_above_ceiling_blocks_tx(self, mock_web3, signed_mock, monkeypatch):
        from arc_devkit import config as config_module

        monkeypatch.setattr(
            config_module,
            "settings",
            dataclasses.replace(config_module.settings, max_gas_price_gwei=Decimal("0.5")),
        )
        mock_web3.from_wei.return_value = "1.0"  # 1 gwei > 0.5 ceiling

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=_KEY)
        result = agent.execute(to=_TO, amount_usdc=1.0, enviar=True, wait_receipt=False)

        assert result["status"] == "error"
        assert "ceiling" in result["error"]
        mock_web3.eth.send_raw_transaction.assert_not_called()

    def test_no_ceiling_configured_allows_tx(self, mock_web3, signed_mock):
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=_KEY)
        result = agent.execute(to=_TO, amount_usdc=1.0, enviar=True, wait_receipt=False)
        assert result["status"] == "sent"


class TestGuardrailsIntegration:
    def test_non_whitelisted_recipient_blocked(self, mock_web3, signed_mock, tmp_path):
        from arc_devkit.agents.guardrails import Guardrails
        from arc_devkit.agents.payment_agent import PaymentAgent

        other = "0x" + "c" * 40
        agent = PaymentAgent(
            private_key=_KEY,
            guardrails=Guardrails(allowed_recipients=[other], state_dir=tmp_path),
        )
        result = agent.execute(to=_TO, amount_usdc=1.0, enviar=True, wait_receipt=False)

        assert result["status"] == "blocked"
        mock_web3.eth.send_raw_transaction.assert_not_called()

    def test_spend_limit_blocks_and_audit_records_success(self, mock_web3, signed_mock, tmp_path):
        from arc_devkit.agents.guardrails import Guardrails
        from arc_devkit.agents.payment_agent import PaymentAgent

        guardrails = Guardrails(max_spend_per_day_usdc=Decimal("1.5"), state_dir=tmp_path)
        agent = PaymentAgent(private_key=_KEY, guardrails=guardrails)

        first = agent.execute(to=_TO, amount_usdc=1.0, enviar=True, wait_receipt=False)
        assert first["status"] == "sent"
        assert "transfer" in (tmp_path / "audit.log").read_text()

        second = agent.execute(to=_TO, amount_usdc=1.0, enviar=True, wait_receipt=False)
        assert second["status"] == "blocked"

    def test_sign_only_skips_guardrails(self, mock_web3, signed_mock, tmp_path):
        """Guardrails apply to broadcasts; signing without sending is unrestricted."""
        from arc_devkit.agents.guardrails import Guardrails
        from arc_devkit.agents.payment_agent import PaymentAgent

        other = "0x" + "c" * 40
        agent = PaymentAgent(
            private_key=_KEY,
            guardrails=Guardrails(allowed_recipients=[other], state_dir=tmp_path),
        )
        result = agent.execute(to=_TO, amount_usdc=1.0, enviar=False)
        assert result["status"] == "signed"


class TestReplaceByFee:
    def test_speed_up_pending_tx(self, mock_web3, signed_mock):
        mock_web3.eth.get_transaction.return_value = {
            "blockNumber": None,
            "to": _TO,
            "value": 10**18,
            "nonce": 5,
            "gas": 21_000,
            "gasPrice": 1_000_000_000,
            "input": "0x",
        }
        mock_web3.eth.send_raw_transaction.return_value = bytes.fromhex("beef")

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=_KEY)
        result = agent.speed_up("0x" + "a" * 64)

        assert result["status"] == "replaced"
        assert result["gas_price"] == 1_100_000_000  # +10%

    def test_speed_up_already_mined(self, mock_web3, signed_mock):
        mock_web3.eth.get_transaction.return_value = {"blockNumber": 123}

        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=_KEY)
        result = agent.speed_up("0x" + "a" * 64)
        assert result["status"] == "already_mined"

    def test_speed_up_without_key(self, mock_web3):
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=None)
        result = agent.speed_up("0x" + "a" * 64)
        assert result["status"] == "error"


class TestUsePaymaster:
    def test_use_paymaster_fails_clearly_when_unavailable(self, mock_web3, signed_mock):
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=_KEY)
        result = agent.execute(
            to=_TO, amount_usdc=1.0, enviar=True, wait_receipt=False, use_paymaster=True
        )

        assert result["status"] == "error"
        assert "paymaster" in result["error"].lower()
        mock_web3.eth.send_raw_transaction.assert_not_called()

    def test_use_paymaster_false_does_not_check_paymaster(self, mock_web3, signed_mock):
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=_KEY)
        result = agent.execute(
            to=_TO, amount_usdc=1.0, enviar=True, wait_receipt=False, use_paymaster=False
        )

        assert result["status"] == "sent"
