"""Async abstract base class for Arc economic agents."""

import asyncio
import logging
from abc import abstractmethod

from arc_devkit.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AsyncBaseAgent(BaseAgent):
    """
    Async variant of BaseAgent — get_balance() and execute() are coroutines.

    Inherits wallet resolution and RPC connection from BaseAgent.
    Blocking web3 calls are dispatched to a thread pool via asyncio.to_thread()
    so the event loop is never blocked.
    """

    @abstractmethod  # type: ignore[override]
    async def get_balance(self) -> dict: ...

    @abstractmethod  # type: ignore[override]
    async def execute(self, **kwargs) -> dict: ...

    async def _acall_rpc(self, fn, *args, **kwargs):
        """Run a blocking RPC call in a thread without blocking the event loop."""
        return await asyncio.to_thread(fn, *args, **kwargs)
