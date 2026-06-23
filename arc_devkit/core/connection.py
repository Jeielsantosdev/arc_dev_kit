"""Arc blockchain connection via web3.py."""

import logging

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)


def get_web3() -> Web3:
    """
    Return a Web3 instance connected to the RPC node configured in ARC_RPC_URL.

    Injects PoA middleware required for EVM networks that use blocks
    with extraData larger than 32 bytes (common in testnets).
    """
    from arc_devkit.config import settings

    w3 = Web3(Web3.HTTPProvider(settings.arc_rpc_url))

    # PoA middleware required for compatibility with Arc testnet
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    return w3


def check_connection() -> bool:
    """
    Test the connection to the Arc RPC node.

    Returns:
        True if connected successfully, False otherwise.
    """
    try:
        w3 = get_web3()
        if w3.is_connected():
            bloco = w3.eth.block_number
            chain_id = w3.eth.chain_id
            logger.info("Connected to Arc! Block: #%d | Chain ID: %d", bloco, chain_id)
            return True

        logger.warning("Web3 instantiated but is_connected() returned False.")
        return False

    except Exception as exc:
        logger.error("Failed to connect to Arc RPC: %s", exc)
        return False
