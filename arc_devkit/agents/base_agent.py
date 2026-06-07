"""Classe base abstrata para todos os agentes econômicos Arc."""

import logging
from abc import ABC, abstractmethod

from eth_account import Account
from web3 import Web3

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Fundação para todos os agentes econômicos Arc.

    Gerencia a conexão com a blockchain, a identidade da carteira
    e fornece helpers de logging. Subclasses implementam get_balance()
    e execute() com a lógica específica de cada tipo de agente.
    """

    def __init__(
        self,
        private_key: str | None = None,
        rpc_url: str | None = None,
    ) -> None:
        """
        Inicializa o agente com carteira e conexão RPC.

        Args:
            private_key: Chave privada hex (opcional). Se omitida, usa
                         ARC_PRIVATE_KEY do ambiente. Sem chave = modo leitura.
            rpc_url: URL do nó RPC (opcional). Se omitida, usa ARC_RPC_URL.
        """
        from arc_devkit.config import settings
        from arc_devkit.core.connection import get_web3

        # Configurar conexão com a Arc
        self._w3: Web3 = get_web3()

        # Resolver chave privada: argumento > variável de ambiente > None
        _chave = private_key or settings.arc_private_key

        if _chave:
            account = Account.from_key(_chave)
            self._address: str | None = account.address
            self._private_key: str | None = _chave
            logger.info(
                "[%s] Inicializado com carteira %s",
                self.__class__.__name__,
                self._address,
            )
        else:
            self._address = None
            self._private_key = None
            logger.warning(
                "[%s] Sem chave privada — modo somente leitura.",
                self.__class__.__name__,
            )

    @property
    def wallet_address(self) -> str | None:
        """Endereço checksummed da carteira do agente."""
        return self._address

    @abstractmethod
    def get_balance(self) -> dict:
        """
        Retorna o saldo atual da carteira do agente.

        Returns:
            Dict com pelo menos 'address' e 'balance_usdc'.
        """
        ...

    @abstractmethod
    def execute(self, **kwargs) -> dict:
        """
        Executa a ação principal do agente.

        Returns:
            Dict com o resultado da execução, incluindo 'status'.
        """
        ...

    def log(self, msg: str) -> None:
        """Helper de log padronizado: prefixo com nome da classe."""
        logger.info("[%s] %s", self.__class__.__name__, msg)
