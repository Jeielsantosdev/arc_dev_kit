"""Abstract base class for all Arc economic agents."""

import logging
from abc import ABC, abstractmethod

from eth_account import Account
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from web3 import Web3

logger = logging.getLogger(__name__)


def _make_web3(rpc_url: str) -> Web3:
    from web3.middleware import ExtraDataToPOAMiddleware

    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def _get_web3_with_fallback(rpc_urls: tuple[str, ...]) -> Web3:
    """Try each URL in order; raise ConnectionError if all fail."""
    for url in rpc_urls:
        try:
            w3 = _make_web3(url)
            if w3.is_connected():
                return w3
        except Exception as exc:
            logger.warning("RPC %s unavailable: %s", url, exc)
    raise ConnectionError(f"No RPC available: {rpc_urls}")


class BaseAgent(ABC):
    """
    Foundation for all Arc economic agents.

    Manages blockchain connection, wallet identity, and logging helpers.
    Subclasses implement get_balance() and execute() with agent-specific logic.
    """

    def __init__(
        self,
        private_key: str | None = None,
        rpc_url: str | None = None,
    ) -> None:
        """
        Initialize the agent with wallet and RPC connection.

        Args:
            private_key: Hex private key (optional). Falls back to ARC_PRIVATE_KEY
                         env var. Without a key the agent runs in read-only mode.
            rpc_url: RPC node URL (optional). Falls back to ARC_RPC_URL.
                     Comma-separated list enables automatic failover.
        """
        from arc_devkit.config import settings
        from arc_devkit.core.connection import get_web3

        # Multi-RPC support
        if rpc_url:
            # Explicit rpc_url — may be a comma-separated list
            rpc_urls = tuple(u.strip() for u in rpc_url.split(",") if u.strip())
            self._w3: Web3 = _get_web3_with_fallback(rpc_urls)
        elif len(settings.arc_rpc_urls) > 1:
            # Multiple RPCs configured — activate automatic fallback
            self._w3 = _get_web3_with_fallback(settings.arc_rpc_urls)
        else:
            # Single RPC — use default get_web3() (mockable in tests)
            self._w3 = get_web3()

        # Resolve private key: argument > env var > None
        _key = private_key or settings.arc_private_key

        if _key:
            account = Account.from_key(_key)
            self._address: str | None = account.address
            self._private_key: str | None = _key
            logger.info(
                "[%s] Initialized with wallet %s",
                self.__class__.__name__,
                self._address,
            )
        else:
            self._address = None
            self._private_key = None
            logger.warning(
                "[%s] No private key — read-only mode.",
                self.__class__.__name__,
            )

    @property
    def wallet_address(self) -> str | None:
        """Checksummed wallet address."""
        return self._address

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call_rpc(self, fn, *args, **kwargs):
        """Execute an RPC call with automatic retry on network failures."""
        return fn(*args, **kwargs)

    @abstractmethod
    def get_balance(self) -> dict: ...

    @abstractmethod
    def execute(self, **kwargs) -> dict: ...

    def log(self, msg: str) -> None:
        """Standardized log helper: prefixes with class name."""
        logger.info("[%s] %s", self.__class__.__name__, msg)
