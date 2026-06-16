"""Estimativa de custo de gás para transações Arc."""

import logging
from decimal import Decimal

from web3 import Web3

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)

# Custo fixo de transferência nativa (ETH/USDC) em unidades de gás
GAS_TRANSFERENCIA = 21_000


def estimate_transfer(to: str, amount_usdc: float, from_address: str | None = None) -> dict:
    """
    Estima o custo de gás para uma transferência nativa na Arc.

    Args:
        to: Endereço EVM de destino.
        amount_usdc: Valor a transferir (em USDC).
        from_address: Endereço remetente (opcional — usado para estimativa mais precisa).

    Returns:
        Dict com gas_limit, gas_price_gwei, custo_usdc e custo_wei.
    """
    w3 = get_web3()

    destino = Web3.to_checksum_address(to)
    gas_price_wei = w3.eth.gas_price
    gas_price_gwei = Decimal(str(w3.from_wei(gas_price_wei, "gwei")))

    # Para transferências nativas o gás é fixo em 21.000
    # Para contratos, usa eth_estimateGas (mais preciso mas requer from_address)
    if from_address:
        try:
            remetente = Web3.to_checksum_address(from_address)
            gas_limit = w3.eth.estimate_gas({
                "from": remetente,
                "to": destino,
                "value": w3.to_wei(amount_usdc, "ether"),
            })
        except Exception:
            gas_limit = GAS_TRANSFERENCIA
    else:
        gas_limit = GAS_TRANSFERENCIA

    custo_wei = gas_limit * gas_price_wei
    custo_usdc = Decimal(str(w3.from_wei(custo_wei, "ether")))

    logger.debug("Estimativa: %d gas × %s gwei = %s USDC", gas_limit, gas_price_gwei, custo_usdc)

    return {
        "gas_limit": gas_limit,
        "gas_price_gwei": str(gas_price_gwei),
        "gas_price_wei": str(gas_price_wei),
        "custo_usdc": str(custo_usdc),
        "custo_wei": str(custo_wei),
        "amount_usdc": amount_usdc,
        "to": str(destino),
    }
