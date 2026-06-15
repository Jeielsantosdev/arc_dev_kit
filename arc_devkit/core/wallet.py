"""Operações de carteira na Arc blockchain."""

import logging
from decimal import Decimal

from eth_account import Account
from web3 import Web3

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)

# USDC usa 6 casas decimais (padrão Circle)
USDC_DECIMALS = 6
USDC_MULTIPLIER = 10**USDC_DECIMALS


def create_wallet() -> dict[str, str]:
    """
    Cria uma nova carteira EVM aleatória.

    Returns:
        Dict com 'address' (checksummed) e 'private_key' (hex com prefixo 0x).

    Warning:
        A chave privada gerada nunca é armazenada — guarde-a imediatamente
        em local seguro. Perder a chave significa perder acesso à carteira.
    """
    account = Account.create()
    logger.info("Nova carteira criada: %s", account.address)
    key_hex = account.key.hex()
    return {
        "address": account.address,
        "private_key": key_hex if key_hex.startswith("0x") else f"0x{key_hex}",
    }


def get_balance(address: str) -> dict[str, str | Decimal]:
    """
    Retorna o saldo nativo de um endereço Arc.

    Na Arc, USDC é o token de gás. Este método retorna o saldo nativo
    da rede. Para saldo do contrato USDC ERC-20, será necessário o
    endereço do contrato USDC na Arc (a confirmar com a documentação oficial).

    Args:
        address: Endereço EVM (com ou sem checksum).

    Returns:
        Dict com address, balance_wei e balance_usdc (Decimal).
    """
    w3 = get_web3()
    checksum_addr = Web3.to_checksum_address(address)

    wei = w3.eth.get_balance(checksum_addr)
    # Converte para valor legível (18 casas decimais para saldo nativo)
    balance_human = Decimal(str(w3.from_wei(wei, "ether")))

    logger.debug("Saldo de %s: %s (%d wei)", checksum_addr, balance_human, wei)

    return {
        "address": checksum_addr,
        "balance_wei": str(wei),
        "balance_usdc": balance_human,
    }


def get_block_number() -> int:
    """Retorna o número do bloco mais recente na Arc."""
    bloco = get_web3().eth.block_number
    logger.debug("Bloco atual: #%d", bloco)
    return bloco
