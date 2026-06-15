"""Testes unitários para PaymentAgent e MonitorAgent."""

from decimal import Decimal
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# PaymentAgent
# ---------------------------------------------------------------------------

class TestPaymentAgent:
    """
    base_agent importa get_web3 e settings lazy (dentro de __init__).
    O fixture mock_web3 já remenda Web3 em arc_devkit.core.connection,
    então qualquer chamada a get_web3() retorna o mock automaticamente.
    """

    def test_get_balance_retorna_saldo(self, mock_web3):
        mock_web3.eth.get_balance.return_value = 1_000_000_000_000_000_000
        mock_web3.from_wei.return_value = Decimal("1.0")

        from arc_devkit.agents.payment_agent import PaymentAgent

        agente = PaymentAgent(private_key="0x" + "a" * 64)
        resultado = agente.get_balance()

        assert "address" in resultado
        assert "balance_wei" in resultado

    def test_get_balance_sem_chave_retorna_erro(self, mock_web3):
        from arc_devkit.agents.payment_agent import PaymentAgent

        # conftest não define ARC_PRIVATE_KEY → settings.arc_private_key = None
        agente = PaymentAgent(private_key=None)
        resultado = agente.get_balance()

        assert "error" in resultado

    def test_execute_sem_chave_retorna_erro(self, mock_web3):
        from arc_devkit.agents.payment_agent import PaymentAgent

        agente = PaymentAgent(private_key=None)
        resultado = agente.execute(to="0x" + "b" * 40, amount_usdc=1.0)

        assert resultado["status"] == "erro"

    def test_execute_assina_sem_enviar(self, mock_web3):
        mock_web3.eth.get_transaction_count.return_value = 0
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.eth.chain_id = 7_777_777
        mock_web3.to_wei.return_value = 1_000_000_000_000_000_000

        signed_mock = MagicMock()
        signed_mock.raw_transaction = b"\x01\x02\x03"
        mock_web3.eth.account.sign_transaction.return_value = signed_mock

        from arc_devkit.agents.payment_agent import PaymentAgent

        agente = PaymentAgent(private_key="0x" + "a" * 64)
        resultado = agente.execute(to="0x" + "b" * 40, amount_usdc=1.0, enviar=False)

        assert resultado["status"] == "assinada"
        assert "raw_transaction" in resultado
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

        agente = PaymentAgent(private_key="0x" + "a" * 64)
        resultado = agente.execute(to="0x" + "b" * 40, amount_usdc=1.0, enviar=True)

        assert resultado["status"] == "enviada"
        assert "tx_hash" in resultado
        mock_web3.eth.send_raw_transaction.assert_called_once()


# ---------------------------------------------------------------------------
# MonitorAgent
# ---------------------------------------------------------------------------

class TestMonitorAgent:
    def test_get_balance_retorna_saldo_monitorado(self, mock_web3):
        mock_web3.eth.get_balance.return_value = 500_000_000
        mock_web3.from_wei.return_value = "0.5"

        from arc_devkit.agents.monitor_agent import MonitorAgent

        agente = MonitorAgent(watched_address="0x" + "c" * 40)
        resultado = agente.get_balance()

        assert "address" in resultado
        assert "balance_wei" in resultado

    def test_execute_detecta_mudanca_de_saldo(self, mock_web3):
        # Primeira chamada (init): saldo base; segunda e terceira: iterações
        mock_web3.eth.get_balance.side_effect = [100, 200, 200]

        eventos_capturados = []

        def _cb(evt):
            eventos_capturados.append(evt)

        from arc_devkit.agents.monitor_agent import MonitorAgent

        with patch("time.sleep"):  # evita sleep real
            agente = MonitorAgent(watched_address="0x" + "c" * 40, interval_seconds=1)
            agente.execute(callback=_cb, max_iterations=2)

        assert len(eventos_capturados) == 1
        assert eventos_capturados[0]["tipo"] == "credito"
        assert eventos_capturados[0]["diferenca_wei"] == "100"

    def test_execute_sem_mudanca_nao_chama_callback(self, mock_web3):
        mock_web3.eth.get_balance.return_value = 100
        chamadas = []

        from arc_devkit.agents.monitor_agent import MonitorAgent

        with patch("time.sleep"):
            agente = MonitorAgent(watched_address="0x" + "c" * 40, interval_seconds=1)
            agente.execute(callback=lambda e: chamadas.append(e), max_iterations=3)

        assert len(chamadas) == 0

    def test_stop_encerra_loop(self, mock_web3):
        mock_web3.eth.get_balance.return_value = 100

        from arc_devkit.agents.monitor_agent import MonitorAgent

        with patch("time.sleep"):
            agente = MonitorAgent(watched_address="0x" + "c" * 40, interval_seconds=1)
            resultado = agente.execute(max_iterations=1)

        assert resultado["status"] == "finalizado"
        assert resultado["iteracoes"] == 1
