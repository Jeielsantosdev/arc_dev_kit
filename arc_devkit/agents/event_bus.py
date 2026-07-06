"""Async event bus for inter-agent communication.

Lightweight publish/subscribe over asyncio: agents publish events to topics
("balance.low", "payment.sent", ...) and other agents subscribe with async or
sync handlers. Handler failures are isolated and logged.
"""

import asyncio
import inspect
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """In-process pub/sub bus for agent coordination."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict], Any]]] = {}
        self._history: list[tuple[str, dict]] = []

    def subscribe(self, topic: str, handler: Callable[[dict], Any]) -> None:
        """Register a sync or async handler for a topic."""
        self._subscribers.setdefault(topic, []).append(handler)
        logger.debug("Subscribed %s to topic %r", getattr(handler, "__name__", handler), topic)

    def unsubscribe(self, topic: str, handler: Callable[[dict], Any]) -> None:
        """Remove a handler from a topic (no-op if absent)."""
        handlers = self._subscribers.get(topic, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, topic: str, event: dict) -> int:
        """
        Deliver an event to all subscribers of a topic.

        Returns:
            Number of handlers that received the event.
        """
        self._history.append((topic, event))
        handlers = list(self._subscribers.get(topic, []))
        for handler in handlers:
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                logger.error("Event handler failed on topic %r: %s", topic, exc)
        return len(handlers)

    def publish_sync(self, topic: str, event: dict) -> int:
        """Publish from synchronous code (runs its own event loop tick)."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.publish(topic, event))
        task = loop.create_task(self.publish(topic, event))
        del task  # fire-and-forget inside a running loop
        return len(self._subscribers.get(topic, []))

    @property
    def history(self) -> list[tuple[str, dict]]:
        """Copy of all published (topic, event) pairs."""
        return list(self._history)
