"""Arc transaction analyzer — combines RPC data with Claude AI analysis."""

import logging
from decimal import Decimal

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)

_ANALYSIS_PROMPT = """\
Analyze this Arc blockchain transaction and respond in English.

Transaction data:
{data}

Answer in structured format:
1. **What the transaction did** — describe in plain language
2. **Status** — success or failure, with reason if error
3. **Cost in USDC** — gas consumed converted to USDC
4. **Suggestion** — if error occurred, how to fix it; if success, any possible optimization
"""


class TxAnalyzer:
    """
    Analyze Arc transactions: fetches data via RPC and generates AI diagnosis.

    Combines eth_getTransaction + eth_getTransactionReceipt with
    Dev Copilot to produce a natural-language analysis report.
    """

    def __init__(self) -> None:
        self._w3 = get_web3()

    def analyze(self, tx_hash: str) -> dict:
        """
        Analyze a transaction and return a complete diagnosis.

        Args:
            tx_hash: Transaction hash (0x... format).

        Returns:
            Dict with: status, summary, custo_usdc, error, suggestion,
            and raw transaction data.
        """
        logger.info("Analyzing transaction: %s", tx_hash)

        # --- 1. Fetch raw data via RPC ---
        try:
            tx = self._w3.eth.get_transaction(tx_hash)
            receipt = self._w3.eth.get_transaction_receipt(tx_hash)
        except Exception as exc:
            logger.error("Error fetching transaction %s: %s", tx_hash, exc)
            return {
                "hash": tx_hash,
                "status": "error",
                "resumo": f"Could not fetch transaction: {exc}",
                "custo_usdc": "0",
                "erro": str(exc),
                "sugestao": "Check that the hash is correct and the RPC is reachable.",
            }

        # --- 2. Calculate USDC cost ---
        gas_usado = receipt.get("gasUsed", 0)
        gas_price = tx.get("gasPrice", 0)
        custo_wei = gas_usado * gas_price
        # Convert to human-readable units (18 decimals for native token)
        custo_decimal = Decimal(str(self._w3.from_wei(custo_wei, "ether")))

        # --- 3. Build data summary for AI prompt ---
        status_str = "success" if receipt.get("status") == 1 else "reverted"
        dados_resumo = {
            "hash": tx_hash,
            "from": tx.get("from"),
            "to": tx.get("to"),
            "value_wei": str(tx.get("value", 0)),
            "gas_limit": tx.get("gas"),
            "gas_used": gas_usado,
            "status": status_str,
            "estimated_cost_usdc": str(custo_decimal),
            "block": receipt.get("blockNumber"),
            "logs_count": len(receipt.get("logs", [])),
        }

        logger.debug("Data collected: %s", dados_resumo)

        # --- 4. Request analysis from Dev Copilot ---
        try:
            from arc_devkit.copilot.agent import DevCopilot

            copilot = DevCopilot()
            prompt = _ANALYSIS_PROMPT.format(data=dados_resumo)
            resumo = copilot.ask(prompt)
        except Exception as exc:
            logger.warning("AI analysis unavailable: %s", exc)
            resumo = f"Status: {status_str} | Gas used: {gas_usado} | Cost: {custo_decimal} USDC"

        return {
            "hash": tx_hash,
            "status": status_str,
            "resumo": resumo,
            "custo_usdc": str(custo_decimal),
            "erro": None if status_str == "success" else "Transaction reverted",
            "sugestao": "",  # included in the Claude-generated resumo
            "dados_brutos": dados_resumo,
        }
