"""Live terminal dashboard for agent state — built on rich.Live."""

from datetime import datetime
from decimal import Decimal

from rich.live import Live
from rich.table import Table

from arc_devkit.agents.monitor_agent import MonitorAgent


class AgentDashboard:
    """
    Renders watched-wallet balances and recent events in a live terminal panel.

    Example:
        monitor = MonitorAgent(watched_addresses=[...], interval_seconds=10)
        AgentDashboard(monitor).run(max_iterations=0)
    """

    MAX_EVENTS = 8

    def __init__(self, monitor: MonitorAgent) -> None:
        self._monitor = monitor
        self._events: list[dict] = []

    def _on_event(self, event: dict) -> None:
        self._events.append({**event, "_at": datetime.now().strftime("%H:%M:%S")})
        self._events = self._events[-self.MAX_EVENTS :]

    def _render(self) -> Table:
        table = Table(title="Arc Agents — Live", header_style="bold cyan")
        table.add_column("Wallet", style="cyan")
        table.add_column("Balance (USDC)", justify="right")

        balances = self._monitor.get_balance()
        for addr, info in balances.items():
            wei = Decimal(info["balance_wei"])
            table.add_row(f"{addr[:10]}…{addr[-6:]}", str(wei / Decimal(10**18)))

        if self._events:
            table.add_section()
            table.add_row("[bold]Recent events[/bold]", "")
            for ev in reversed(self._events):
                kind = ev.get("event_type", "native")
                sign = "+" if ev.get("type") == "credit" else "-"
                amount = ev.get("change_wei") or ev.get("value_atomic") or "?"
                table.add_row(
                    f"[dim]{ev['_at']}[/dim] {kind}",
                    f"{sign}{amount}",
                )
        return table

    def run(self, max_iterations: int = 0, refresh_per_second: int = 2) -> dict:
        """Run the monitor loop while rendering the live panel (blocking)."""
        with Live(self._render(), refresh_per_second=refresh_per_second) as live:

            def _callback(event: dict) -> None:
                self._on_event(event)
                live.update(self._render())

            result = self._monitor.execute(callback=_callback, max_iterations=max_iterations)
            live.update(self._render())
        return result
