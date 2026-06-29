"""Async monitor agent — detects balance changes in Arc wallets (async variant)."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, cast

import httpx
from eth_typing import ChecksumAddress
from web3 import Web3

from arc_devkit.agents.async_base import AsyncBaseAgent

logger = logging.getLogger(__name__)

_TRANSFER_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    }
]

_WEBHOOK_TIMEOUT = 10

# Callback type: may be a plain function OR an async coroutine function
_Callback = Callable[[dict], Any]


class AsyncMonitorAgent(AsyncBaseAgent):
    """
    Async version of MonitorAgent.

    Uses asyncio.sleep() instead of time.sleep() so it integrates cleanly with
    FastAPI WebSocket handlers and other async applications.
    All balance reads are dispatched via _acall_rpc() to avoid blocking the loop.
    """

    def __init__(
        self,
        watched_address: str | None = None,
        watched_addresses: list[str] | None = None,
        interval_seconds: int = 15,
        min_change_wei: int = 0,
        state_file: str | Path | None = None,
        usdc_contract_address: str | None = None,
        webhook_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        addrs: list[str] = []
        if watched_addresses:
            addrs = [Web3.to_checksum_address(a) for a in watched_addresses]
        elif watched_address:
            addrs = [Web3.to_checksum_address(watched_address)]
        self._watched: list[str] = addrs
        self._watched_lower: set[str] = {a.lower() for a in addrs}

        self._interval = interval_seconds
        self._min_change_wei = min_change_wei
        self._last_balances: dict[str, int] = {}
        self._last_erc20_block: int = 0
        self._running = False
        self._state_file = Path(state_file) if state_file else None
        self._webhook_url = webhook_url

        self._usdc_contract = None
        if usdc_contract_address:
            self._usdc_contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(usdc_contract_address),
                abi=_TRANSFER_ABI,
            )

        if self._state_file and self._state_file.exists():
            try:
                saved = json.loads(self._state_file.read_text())
                if "balances" in saved:
                    self._last_balances = {k: int(v) for k, v in saved["balances"].items()}
                    self._last_erc20_block = int(saved.get("last_erc20_block", 0))
                else:
                    self._last_balances = {k: int(v) for k, v in saved.items()}
                logger.info("State restored from %s", self._state_file)
            except Exception as exc:
                logger.warning("Failed to restore state: %s", exc)

    @property
    def watched_addresses(self) -> list[str]:
        return list(self._watched)

    def _save_state(self) -> None:
        if self._state_file:
            try:
                self._state_file.write_text(
                    json.dumps({
                        "balances": {k: str(v) for k, v in self._last_balances.items()},
                        "last_erc20_block": self._last_erc20_block,
                    })
                )
            except Exception as exc:
                logger.warning("Failed to save state: %s", exc)

    async def _fire_webhook(self, event: dict) -> None:
        if not self._webhook_url:
            return
        try:
            async with httpx.AsyncClient(timeout=_WEBHOOK_TIMEOUT) as client:
                resp = await client.post(
                    self._webhook_url,
                    json=event,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                logger.debug("Webhook delivered: %s", resp.status_code)
        except Exception as exc:
            logger.warning("Webhook delivery failed (%s): %s", self._webhook_url, exc)

    async def _emit(self, event: dict, callback: _Callback | None) -> None:
        """Fire callback (sync or async) and webhook."""
        if callback:
            result = callback(event)
            if asyncio.iscoroutine(result):
                await result
        await self._fire_webhook(event)

    async def _scan_erc20_events(
        self,
        from_block: int,
        to_block: int,
        callback: _Callback | None,
    ) -> None:
        if not self._usdc_contract or not self._watched:
            return
        try:
            logs = await self._acall_rpc(
                self._usdc_contract.events.Transfer.get_logs,  # type: ignore[attr-defined]
                from_block=from_block,
                to_block=to_block,
            )
        except Exception as exc:
            logger.debug("ERC-20 log query failed: %s", exc)
            return

        for log in logs:
            args = log.get("args", {})
            sender = (args.get("from") or "").lower()
            recipient = (args.get("to") or "").lower()
            value = args.get("value", 0)

            if sender not in self._watched_lower and recipient not in self._watched_lower:
                continue

            direction = "credit" if recipient in self._watched_lower else "debit"
            address = next(
                (a for a in self._watched if a.lower() == (recipient if direction == "credit" else sender)),
                "",
            )

            event = {
                "address": address,
                "event_type": "erc20_transfer",
                "token": "USDC",
                "from": args.get("from"),
                "to": args.get("to"),
                "value_atomic": str(value),
                "tx_hash": log.get("transactionHash", b"").hex()
                if hasattr(log.get("transactionHash", b""), "hex")
                else str(log.get("transactionHash", "")),
                "block": log.get("blockNumber"),
                "type": direction,
            }
            self.log(f"[ERC-20] {direction} {value} atomic USDC → {address[:10]}")
            await self._emit(event, callback)

    async def get_balance(self) -> dict:  # type: ignore[override]
        resultado = {}
        for addr in self._watched:
            wei = await self._acall_rpc(
                self._w3.eth.get_balance, cast(ChecksumAddress, addr)
            )
            resultado[addr] = {
                "address": addr,
                "balance_wei": str(wei),
                "balance_eth": str(self._w3.from_wei(wei, "ether")),
            }
        return resultado

    async def execute(  # type: ignore[override]
        self,
        callback: _Callback | None = None,
        max_iterations: int = 0,
    ) -> dict:
        """
        Start the async wallet monitoring loop.

        Args:
            callback: Called with an event dict on each detected change.
                      May be a plain function or an async coroutine function.
            max_iterations: Maximum iterations (0 = infinite until stop()).
        """
        self._running = True

        for addr in self._watched:
            if addr not in self._last_balances:
                self._last_balances[addr] = await self._acall_rpc(
                    self._w3.eth.get_balance, cast(ChecksumAddress, addr)
                )

        if self._usdc_contract and self._last_erc20_block == 0:
            try:
                self._last_erc20_block = await self._acall_rpc(
                    lambda: self._w3.eth.block_number
                )
            except Exception:
                pass

        iterations = 0
        self.log(f"[Async] Monitoring {len(self._watched)} wallet(s) every {self._interval}s")

        while self._running:
            for addr in self._watched:
                current_balance = await self._acall_rpc(
                    self._w3.eth.get_balance, cast(ChecksumAddress, addr)
                )
                prev_balance = self._last_balances.get(addr, current_balance)
                delta = current_balance - prev_balance

                if delta != 0 and abs(delta) >= self._min_change_wei:
                    event = {
                        "address": addr,
                        "prev_balance_wei": str(prev_balance),
                        "balance_wei": str(current_balance),
                        "change_wei": str(delta),
                        "type": "credit" if delta > 0 else "debit",
                        "event_type": "native",
                    }
                    self.log(f"[{addr[:10]}] Change: {delta:+d} wei ({event['type']})")
                    await self._emit(event, callback)
                    self._last_balances[addr] = current_balance

            if self._usdc_contract:
                try:
                    current_block = await self._acall_rpc(lambda: self._w3.eth.block_number)
                    if current_block > self._last_erc20_block:
                        await self._scan_erc20_events(
                            from_block=self._last_erc20_block + 1,
                            to_block=current_block,
                            callback=callback,
                        )
                        self._last_erc20_block = current_block
                except Exception as exc:
                    logger.debug("ERC-20 scan skipped: %s", exc)

            await asyncio.to_thread(self._save_state)
            iterations += 1
            if max_iterations and iterations >= max_iterations:
                break

            await asyncio.sleep(self._interval)

        return {"status": "done", "iterations": iterations}

    async def event_stream(
        self,
        max_events: int = 0,
    ) -> AsyncIterator[dict]:
        """
        Async generator that yields events as they occur.

        Starts execute() as a background task and forwards events via an
        internal asyncio.Queue. Safe to use inside WebSocket handlers.

        Usage:
            async for event in monitor.event_stream():
                await ws.send_json(event)
        """
        queue: asyncio.Queue[dict] = asyncio.Queue()
        count = 0

        async def _enqueue(event: dict) -> None:
            await queue.put(event)

        task = asyncio.create_task(self.execute(callback=_enqueue))
        try:
            while True:
                # Drain remaining events after the task finishes
                if task.done() and queue.empty():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                except TimeoutError:
                    continue  # re-check task.done() on next iteration
                yield event
                count += 1
                if max_events and count >= max_events:
                    break
        finally:
            self.stop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def stop(self) -> None:
        """Stop the monitoring loop on the next iteration."""
        self._running = False
        self._save_state()
        self.log("Async monitoring stopped.")
