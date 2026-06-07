"""Agente de pagamento Arc — monta e assina transações de transferência."""

import logging
from decimal import Decimal

from web3 import Web3

from arc_devkit.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class PaymentAgent(BaseAgent):
    """
    Agente responsável por executar pagamentos na rede Arc.

    Monta, assina e (opcionalmente) envia transações de transferência.
    Projetado para ser reutilizado em fluxos de pagamento recorrente.
    """

    def get_balance(self) -> dict:
        """
        Retorna o saldo nativo da carteira do agente.

        Returns:
            Dict com address, balance_wei e balance_usdc (Decimal).
        """
        if not self._address:
            return {"error": "Nenhuma chave privada configurada — modo somente leitura."}

        wei = self._w3.eth.get_balance(self._address)
        balance = Decimal(str(self._w3.from_wei(wei, "ether")))

        return {
            "address": self._address,
            "balance_wei": str(wei),
            "balance_usdc": balance,
        }

    def execute(self, to: str, amount_usdc: float, enviar: bool = False) -> dict:
        """
        Monta e assina uma transação de pagamento.

        Args:
            to: Endereço EVM do destinatário.
            amount_usdc: Valor a transferir (em USDC).
            enviar: Se True, envia a transação para a rede (requer chave privada).
                    Se False (padrão), retorna a transação assinada sem enviar.

        Returns:
            Dict com status, dados da transação e hash (se enviada).
        """
        if not self._private_key:
            return {"status": "erro", "error": "Chave privada necessária para assinar transações."}

        destinatario = Web3.to_checksum_address(to)
        self.log(f"Preparando pagamento de {amount_usdc} USDC → {destinatario}")

        # Montar transação
        nonce = self._w3.eth.get_transaction_count(self._address)
        tx = {
            "from": self._address,
            "to": destinatario,
            "value": self._w3.to_wei(amount_usdc, "ether"),  # placeholder: USDC nativo
            "gas": 21_000,
            "gasPrice": self._w3.eth.gas_price,
            "nonce": nonce,
            "chainId": self._w3.eth.chain_id,
        }

        # Assinar a transação com a chave privada
        signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
        self.log("Transação assinada com sucesso.")

        if enviar:
            # Enviar para a rede Arc
            tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            self.log(f"Transação enviada: {tx_hash_hex}")
            return {
                "status": "enviada",
                "from": self._address,
                "to": destinatario,
                "amount_usdc": amount_usdc,
                "tx_hash": tx_hash_hex,
            }

        # Modo padrão: retornar transação assinada sem enviar
        # TODO: remova enviar=False e passe enviar=True para envio real
        return {
            "status": "assinada",
            "from": self._address,
            "to": destinatario,
            "amount_usdc": amount_usdc,
            "raw_transaction": signed.raw_transaction.hex(),
            "nota": "Transação assinada. Passe enviar=True para enviar à rede.",
        }
