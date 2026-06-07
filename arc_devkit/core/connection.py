"""Conexão com a Arc blockchain via web3.py."""

import logging

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)


def get_web3() -> Web3:
    """
    Retorna instância Web3 conectada ao nó RPC configurado em ARC_RPC_URL.

    Aplica o middleware PoA necessário para redes EVM que usam blocos
    com extraData maior que 32 bytes (comum em testnets).
    """
    from arc_devkit.config import settings

    w3 = Web3(Web3.HTTPProvider(settings.arc_rpc_url))

    # Middleware necessário para compatibilidade com redes PoA/testnets
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    return w3


def check_connection() -> bool:
    """
    Testa a conexão com o nó RPC da Arc.

    Returns:
        True se conectado com sucesso, False caso contrário.
    """
    try:
        w3 = get_web3()
        if w3.is_connected():
            bloco = w3.eth.block_number
            chain_id = w3.eth.chain_id
            logger.info(
                "Conectado à Arc! Bloco: #%d | Chain ID: %d", bloco, chain_id
            )
            return True

        logger.warning("Web3 instanciado mas is_connected() retornou False.")
        return False

    except Exception as exc:
        logger.error("Falha ao conectar ao Arc RPC: %s", exc)
        return False
