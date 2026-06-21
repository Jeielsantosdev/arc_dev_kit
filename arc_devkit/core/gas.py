"""Gas cost estimation for Arc transactions."""

import logging
from decimal import Decimal

from web3 import Web3

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)

# Fixed gas cost for native transfer (ETH/USDC) in gas units
GAS_TRANSFERENCIA = 21_000


def estimate_transfer(to: str, amount_usdc: float, from_address: str | None = None) -> dict:
    """
    Estimate the gas cost for a native transfer on Arc.

    Args:
        to: Recipient EVM address.
        amount_usdc: Amount to transfer (in USDC).
        from_address: Sender address (optional — used for a more precise estimate).

    Returns:
        Dict with gas_limit, gas_price_gwei, custo_usdc and custo_wei.
    """
    w3 = get_web3()

    destino = Web3.to_checksum_address(to)
    gas_price_wei = w3.eth.gas_price
    gas_price_gwei = Decimal(str(w3.from_wei(gas_price_wei, "gwei")))

    # Native transfers use fixed 21,000 gas
    # For contracts, uses eth_estimateGas (more precise, requires from_address)
    if from_address:
        try:
            remetente = Web3.to_checksum_address(from_address)
            gas_limit = w3.eth.estimate_gas(
                {
                    "from": remetente,
                    "to": destino,
                    "value": w3.to_wei(amount_usdc, "ether"),
                }
            )
        except Exception:
            gas_limit = GAS_TRANSFERENCIA
    else:
        gas_limit = GAS_TRANSFERENCIA

    custo_wei = gas_limit * gas_price_wei
    custo_usdc = Decimal(str(w3.from_wei(custo_wei, "ether")))

    logger.debug("Estimate: %d gas × %s gwei = %s USDC", gas_limit, gas_price_gwei, custo_usdc)

    return {
        "gas_limit": gas_limit,
        "gas_price_gwei": str(gas_price_gwei),
        "gas_price_wei": str(gas_price_wei),
        "custo_usdc": str(custo_usdc),
        "custo_wei": str(custo_wei),
        "amount_usdc": amount_usdc,
        "to": str(destino),
    }
