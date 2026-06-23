"""Wallet operations on the Arc blockchain."""

import logging
from decimal import Decimal

from eth_account import Account
from web3 import Web3

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)

# USDC uses 6 decimal places (Circle standard)
USDC_DECIMALS = 6
USDC_MULTIPLIER = 10**USDC_DECIMALS


def create_wallet() -> dict[str, str]:
    """
    Create a new random EVM wallet.

    Returns:
        Dict with 'address' (checksummed) and 'private_key' (hex with 0x prefix).

    Warning:
        The generated private key is never stored — save it immediately
        in a secure location. Losing the key means losing access to the wallet.
    """
    account = Account.create()
    logger.info("New wallet created: %s", account.address)
    key_hex = account.key.hex()
    return {
        "address": account.address,
        "private_key": key_hex if key_hex.startswith("0x") else f"0x{key_hex}",
    }


def get_balance(address: str) -> dict[str, str | Decimal]:
    """
    Return the native balance of an Arc address.

    On Arc, USDC is the gas token. This method returns the native network balance.
    For ERC-20 USDC contract balance, use the USDCToken module with the
    official USDC contract address on Arc.

    Args:
        address: EVM address (checksummed or not).

    Returns:
        Dict with address, balance_wei and balance_usdc (Decimal).
    """
    w3 = get_web3()
    checksum_addr = Web3.to_checksum_address(address)

    wei = w3.eth.get_balance(checksum_addr)
    # Convert to human-readable value (18 decimals for native balance)
    balance_human = Decimal(str(w3.from_wei(wei, "ether")))

    logger.debug("Balance of %s: %s (%d wei)", checksum_addr, balance_human, wei)

    return {
        "address": checksum_addr,
        "balance_wei": str(wei),
        "balance_usdc": balance_human,
    }


def get_block_number() -> int:
    """Return the most recent block number on Arc."""
    bloco = get_web3().eth.block_number
    logger.debug("Current block: #%d", bloco)
    return bloco
