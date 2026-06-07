"""Agente de monitoramento — detecta mudanças de saldo em carteiras Arc."""

import logging
import time
from collections.abc import Callable
from typing import Any

from web3 import Web3

from arc_devkit.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MonitorAgent(BaseAgent):
    """
    Monitora uma carteira Arc e chama callbacks ao detectar mudanças de saldo.

    Executa em loop de polling — adequado para MVP. Versões futuras
    utilizarão eth_subscribe para eventos em tempo real via WebSocket.
    """

    def __init__(
        self,
        watched_address: str,
        interval_seconds: int = 15,
        **kwargs: Any,
    ) -> None:
        """
        Inicializa o agente de monitoramento.

        Args:
            watched_address: Endereço EVM a monitorar.
            interval_seconds: Intervalo de polling em segundos (padrão: 15).
            **kwargs: Repassado ao BaseAgent (private_key, rpc_url).
        """
        super().__init__(**kwargs)
        self._watched = Web3.to_checksum_address(watched_address)
        self._interval = interval_seconds
        self._last_balance: int | None = None
        self._running = False

    def get_balance(self) -> dict:
        """Retorna o saldo atual da carteira monitorada."""
        wei = self._w3.eth.get_balance(self._watched)
        return {
            "address": self._watched,
            "balance_wei": str(wei),
            "balance_eth": str(self._w3.from_wei(wei, "ether")),
        }

    def execute(
        self,
        callback: Callable[[dict], None] | None = None,
        max_iterations: int = 0,
    ) -> dict:
        """
        Inicia o loop de monitoramento da carteira.

        Args:
            callback: Função chamada com um dict de evento ao detectar mudança.
                      O dict contém: address, saldo_anterior, saldo_atual, diferenca_wei.
            max_iterations: Número máximo de iterações (0 = loop infinito).

        Returns:
            Dict com status e total de iterações executadas.
        """
        self._running = True
        self._last_balance = self._w3.eth.get_balance(self._watched)
        iteracoes = 0

        self.log(f"Monitorando {self._watched} a cada {self._interval}s")

        while self._running:
            saldo_atual = self._w3.eth.get_balance(self._watched)

            if saldo_atual != self._last_balance:
                diferenca = saldo_atual - self._last_balance
                evento = {
                    "address": self._watched,
                    "saldo_anterior_wei": str(self._last_balance),
                    "saldo_atual_wei": str(saldo_atual),
                    "diferenca_wei": str(diferenca),
                    "tipo": "credito" if diferenca > 0 else "debito",
                }
                self.log(
                    "Mudança detectada: %+d wei (%s)",
                    diferenca,
                    evento["tipo"],
                )

                if callback:
                    callback(evento)

                self._last_balance = saldo_atual

            iteracoes += 1
            if max_iterations and iteracoes >= max_iterations:
                break

            time.sleep(self._interval)

        return {"status": "finalizado", "iteracoes": iteracoes}

    def stop(self) -> None:
        """Interrompe o loop de monitoramento na próxima iteração."""
        self._running = False
        self.log("Monitoramento encerrado.")
