"""Analisador de transações Arc — combina dados RPC com análise via Claude."""

import logging
from decimal import Decimal

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)

# Prompt enviado ao Claude com os dados brutos da transação
_PROMPT_ANALISE = """\
Analise os dados desta transação da Arc blockchain e responda em português brasileiro.

Dados da transação:
{dados}

Responda de forma estruturada:
1. **O que a transação fez** — descreva em linguagem simples
2. **Status** — sucesso ou falha, com motivo se houver erro
3. **Custo em USDC** — gás consumido convertido para USDC
4. **Sugestão** — se houve erro, como corrigir; se sucesso, alguma otimização possível
"""


class TxAnalyzer:
    """
    Analisa transações Arc: busca dados via RPC e gera diagnóstico com IA.

    O analisador combina eth_getTransaction + eth_getTransactionReceipt
    com o Dev Copilot para produzir uma análise em linguagem natural.
    """

    def __init__(self) -> None:
        self._w3 = get_web3()

    def analyze(self, tx_hash: str) -> dict:
        """
        Analisa uma transação e retorna diagnóstico completo.

        Args:
            tx_hash: Hash da transação (formato 0x...).

        Returns:
            Dict com: status, resumo, custo_usdc, erro, sugestao,
            e dados brutos da transação.
        """
        logger.info("Analisando transação: %s", tx_hash)

        # --- 1. Buscar dados brutos via RPC ---
        try:
            tx = self._w3.eth.get_transaction(tx_hash)
            receipt = self._w3.eth.get_transaction_receipt(tx_hash)
        except Exception as exc:
            logger.error("Erro ao buscar transação %s: %s", tx_hash, exc)
            return {
                "hash": tx_hash,
                "status": "erro",
                "resumo": f"Não foi possível buscar a transação: {exc}",
                "custo_usdc": "0",
                "erro": str(exc),
                "sugestao": "Verifique se o hash está correto e se a RPC está acessível.",
            }

        # --- 2. Calcular custo em USDC ---
        gas_usado = receipt.get("gasUsed", 0)
        gas_price = tx.get("gasPrice", 0)
        custo_wei = gas_usado * gas_price
        # Converte para unidade legível (18 decimais para o token nativo)
        custo_decimal = Decimal(str(self._w3.from_wei(custo_wei, "ether")))

        # --- 3. Montar resumo dos dados para o prompt ---
        status_str = "sucesso" if receipt.get("status") == 1 else "revertida"
        dados_resumo = {
            "hash": tx_hash,
            "de": tx.get("from"),
            "para": tx.get("to"),
            "valor_wei": str(tx.get("value", 0)),
            "gas_limite": tx.get("gas"),
            "gas_usado": gas_usado,
            "status": status_str,
            "custo_estimado_usdc": str(custo_decimal),
            "bloco": receipt.get("blockNumber"),
            "logs_count": len(receipt.get("logs", [])),
        }

        logger.debug("Dados coletados: %s", dados_resumo)

        # --- 4. Solicitar análise ao Dev Copilot ---
        try:
            from arc_devkit.copilot.agent import DevCopilot

            copilot = DevCopilot()
            prompt = _PROMPT_ANALISE.format(dados=dados_resumo)
            resumo = copilot.ask(prompt)
        except Exception as exc:
            logger.warning("Análise de IA indisponível: %s", exc)
            resumo = f"Status: {status_str} | Gas usado: {gas_usado} | Custo: {custo_decimal} USDC"

        return {
            "hash": tx_hash,
            "status": status_str,
            "resumo": resumo,
            "custo_usdc": str(custo_decimal),
            "erro": None if status_str == "sucesso" else "Transação revertida",
            "sugestao": "",  # incluído no resumo gerado pelo Claude
            "dados_brutos": dados_resumo,
        }
