"""Monitor agent — detects balance changes in Arc wallets."""

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from web3 import Web3

from arc_devkit.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Minimal ABI to listen for USDC ERC-20 Transfer events
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


class MonitorAgent(BaseAgent):
    """
    Monitors multiple Arc wallets and fires callbacks on balance changes.

    Supports a minimum change threshold, JSON state persistence,
    and ERC-20 Transfer event monitoring.
    """

    def __init__(
        self,
        watched_address: str | None = None,
        watched_addresses: list[str] | None = None,
        interval_seconds: int = 15,
        min_change_wei: int = 0,
        state_file: str | Path | None = None,
        usdc_contract_address: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Args:
            watched_address: Single address to monitor (backward-compat).
            watched_addresses: List of addresses to monitor.
            interval_seconds: Polling interval in seconds.
            min_change_wei: Alert only when change >= this value (in wei).
            state_file: Path to a JSON file for persisting last balances.
            usdc_contract_address: USDC contract address to monitor Transfer events.
        """
        super().__init__(**kwargs)

        # Normalize address list
        addrs: list[str] = []
        if watched_addresses:
            addrs = [Web3.to_checksum_address(a) for a in watched_addresses]
        elif watched_address:
            addrs = [Web3.to_checksum_address(watched_address)]
        self._watched: list[str] = addrs

        self._interval = interval_seconds
        self._min_change_wei = min_change_wei
        self._last_balances: dict[str, int] = {}
        self._running = False
        self._state_file = Path(state_file) if state_file else None

        self._usdc_contract = None
        if usdc_contract_address:
            self._usdc_contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(usdc_contract_address),
                abi=_TRANSFER_ABI,
            )

        # Restore persisted state
        if self._state_file and self._state_file.exists():
            try:
                saved = json.loads(self._state_file.read_text())
                self._last_balances = {k: int(v) for k, v in saved.items()}
                logger.info("State restored from %s", self._state_file)
            except Exception as exc:
                logger.warning("Failed to restore state: %s", exc)

    @property
    def watched_addresses(self) -> list[str]:
        """List of monitored wallet addresses."""
        return list(self._watched)

    def _save_state(self) -> None:
        """Persist current balances to the state file."""
        if self._state_file:
            try:
                self._state_file.write_text(
                    json.dumps({k: str(v) for k, v in self._last_balances.items()})
                )
            except Exception as exc:
                logger.warning("Failed to save state: %s", exc)

    def get_balance(self) -> dict:
        """Return current balances for all monitored wallets."""
        resultado = {}
        for addr in self._watched:
            wei = self._w3.eth.get_balance(addr)
            resultado[addr] = {
                "address": addr,
                "balance_wei": str(wei),
                "balance_eth": str(self._w3.from_wei(wei, "ether")),
            }
        return resultado

    def execute(
        self,
        callback: Callable[[dict], None] | None = None,
        max_iterations: int = 0,
    ) -> dict:
        """
        Start the wallet monitoring loop.

        Args:
            callback: Called with an event dict when a change above the threshold
                      is detected. Event keys: address, prev_balance_wei,
                      balance_wei, change_wei, type, event_type.
            max_iterations: Maximum number of iterations (0 = infinite).

        Returns:
            Dict with status and total iterations executed.
        """
        self._running = True

        # Initialize base balances for wallets without saved state
        for addr in self._watched:
            if addr not in self._last_balances:
                self._last_balances[addr] = self._w3.eth.get_balance(addr)

        iterations = 0
        self.log(f"Monitoring {len(self._watched)} wallet(s) every {self._interval}s")

        while self._running:
            for addr in self._watched:
                current_balance = self._w3.eth.get_balance(addr)
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
                    if callback:
                        callback(event)
                    self._last_balances[addr] = current_balance

            self._save_state()
            iterations += 1
            if max_iterations and iterations >= max_iterations:
                break

            time.sleep(self._interval)

        return {"status": "done", "iterations": iterations}

    def stop(self) -> None:
        """Stop the monitoring loop on the next iteration."""
        self._running = False
        self._save_state()
        self.log("Monitoring stopped.")
