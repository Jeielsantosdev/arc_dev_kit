"""On-chain event listener for Arc DevKit — polls logs by topic/contract."""

import logging
import time
from collections.abc import Callable
from typing import Any

from web3 import Web3
from web3.types import FilterParams

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)

# ERC-20 Transfer event topic (keccak256 of "Transfer(address,address,uint256)")
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


class EventListener:
    """
    Polls on-chain logs for specific events and invokes registered callbacks.

    Designed for ABI-defined events on Arc. Supports multiple callbacks per
    topic and optional address filtering. Uses eth_getLogs polling (no WS
    required).

    Example usage::

        listener = EventListener(contract_address=usdc_address, abi=erc20_abi)
        listener.on("Transfer", lambda evt: print(evt))
        listener.start(poll_interval=3)
    """

    def __init__(
        self,
        contract_address: str | None = None,
        abi: list[dict] | None = None,
        w3: Any | None = None,
        from_block: int | str = "latest",
    ) -> None:
        self._w3: Any = w3 or get_web3()
        self._contract_address = (
            Web3.to_checksum_address(contract_address) if contract_address else None
        )
        self._abi = abi or []
        self._callbacks: dict[str, list[Callable[[dict], None]]] = {}
        self._running = False
        self._from_block: int | str = from_block
        self._last_block: int | None = None

        self._contract = None
        if self._contract_address and self._abi:
            self._contract = self._w3.eth.contract(address=self._contract_address, abi=self._abi)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def on(self, event_name: str, callback: Callable[[dict], None]) -> "EventListener":
        """Register a callback for a named event (e.g. 'Transfer')."""
        self._callbacks.setdefault(event_name, []).append(callback)
        return self

    def off(self, event_name: str, callback: Callable[[dict], None] | None = None) -> None:
        """Unregister a specific callback or all callbacks for an event."""
        if callback is None:
            self._callbacks.pop(event_name, None)
        else:
            handlers = self._callbacks.get(event_name, [])
            self._callbacks[event_name] = [h for h in handlers if h is not callback]

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def poll(self) -> list[dict]:
        """
        Fetch new log entries since the last poll and invoke callbacks.

        Returns:
            List of decoded event dicts processed in this call.
        """
        current_block = self._w3.eth.block_number

        if self._last_block is None:
            if self._from_block == "latest":
                self._last_block = current_block
                return []
            self._last_block = int(self._from_block)

        if current_block < self._last_block:
            return []

        filter_params: FilterParams = {
            "fromBlock": self._last_block,
            "toBlock": current_block,
        }
        if self._contract_address:
            filter_params["address"] = self._contract_address

        processed: list[dict] = []
        try:
            raw_logs = self._w3.eth.get_logs(filter_params)
        except Exception as exc:
            logger.warning("eth_getLogs error: %s", exc)
            return processed

        for log in raw_logs:
            event = self._decode_log(log)
            if event:
                event_name = event.get("event", "")
                for cb in self._callbacks.get(event_name, []):
                    try:
                        cb(event)
                    except Exception as exc:
                        logger.warning("Callback error for %s: %s", event_name, exc)
                processed.append(event)

        self._last_block = current_block + 1
        return processed

    def _decode_log(self, log: Any) -> dict | None:
        """Attempt to decode a raw log using the contract ABI."""
        if self._contract is None:
            return self._raw_log_dict(log)

        for item in self._abi:
            if item.get("type") != "event":
                continue
            event_name = item["name"]
            try:
                event_obj = self._contract.events[event_name]()
                decoded = event_obj.process_log(log)
                return {
                    "event": event_name,
                    "address": decoded.get("address"),
                    "args": dict(decoded.get("args", {})),
                    "block_number": decoded.get("blockNumber"),
                    "tx_hash": decoded.get("transactionHash", b"").hex()
                    if decoded.get("transactionHash")
                    else None,
                    "log_index": decoded.get("logIndex"),
                }
            except Exception:
                continue
        return self._raw_log_dict(log)

    @staticmethod
    def _raw_log_dict(log: Any) -> dict:
        """Convert a raw Web3 log AttributeDict to a plain dict."""
        topics = log.get("topics") or []
        return {
            "event": None,
            "address": log.get("address"),
            "topics": [t.hex() if hasattr(t, "hex") else str(t) for t in topics],
            "data": log.get("data", ""),
            "block_number": log.get("blockNumber"),
            "tx_hash": log.get("transactionHash", b"").hex()
            if log.get("transactionHash")
            else None,
            "log_index": log.get("logIndex"),
        }

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    def start(self, poll_interval: float = 2.0, max_polls: int | None = None) -> None:
        """
        Start the blocking poll loop.

        Args:
            poll_interval: Seconds between polls.
            max_polls: Stop after this many polls (None = run forever).
        """
        self._running = True
        polls = 0
        logger.info(
            "EventListener started — contract=%s interval=%ss",
            self._contract_address or "all",
            poll_interval,
        )

        try:
            while self._running:
                self.poll()
                polls += 1
                if max_polls is not None and polls >= max_polls:
                    break
                time.sleep(poll_interval)
        finally:
            self._running = False
            logger.info("EventListener stopped after %d polls.", polls)

    def stop(self) -> None:
        """Signal the poll loop to stop after the current iteration."""
        self._running = False
