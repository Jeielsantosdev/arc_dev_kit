"""Unit tests for monitor triggers, AutoRefueler, event bus, coordinator, and dashboard."""

import asyncio
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

_ADDR = "0x" + "b" * 40


# ---------------------------------------------------------------------------
# MonitorAgent declarative triggers
# ---------------------------------------------------------------------------


class TestMonitorTriggers:
    def _make_monitor(self, mock_web3, **kwargs):
        from arc_devkit.agents.monitor_agent import MonitorAgent

        return MonitorAgent(watched_address=_ADDR, interval_seconds=1, **kwargs)

    def test_on_low_balance_fires_once_per_crossing(self, mock_web3, tmp_path):
        monitor = self._make_monitor(mock_web3)
        fired: list[dict] = []
        monitor.on_low_balance(threshold_wei=100, action=fired.append)

        # Balance below threshold → fires
        monitor._evaluate_low_balance(_ADDR, 50)
        assert len(fired) == 1
        assert fired[0]["trigger"] == "on_low_balance"

        # Still below → does NOT fire again
        monitor._evaluate_low_balance(_ADDR, 60)
        assert len(fired) == 1

        # Recovers, then drops again → re-arms and fires
        monitor._evaluate_low_balance(_ADDR, 500)
        monitor._evaluate_low_balance(_ADDR, 10)
        assert len(fired) == 2

    def test_on_incoming_transfer_fires_on_credit(self, mock_web3):
        monitor = self._make_monitor(mock_web3)
        fired: list[dict] = []
        monitor.on_incoming_transfer(fired.append)

        monitor._emit({"type": "credit", "address": _ADDR}, callback=None)
        monitor._emit({"type": "debit", "address": _ADDR}, callback=None)

        assert len(fired) == 1
        assert fired[0]["trigger"] == "on_incoming_transfer"

    def test_on_block_interval_fires_every_n_blocks(self, mock_web3):
        monitor = self._make_monitor(mock_web3)
        fired: list[dict] = []
        monitor.on_block_interval(10, fired.append)

        monitor._evaluate_block_interval(100)  # initializes cursor
        monitor._evaluate_block_interval(105)  # +5 → no fire
        monitor._evaluate_block_interval(110)  # +10 → fires
        monitor._evaluate_block_interval(115)  # +5 → no fire

        assert len(fired) == 1
        assert fired[0]["block_number"] == 110

    def test_on_block_interval_rejects_non_positive(self, mock_web3):
        monitor = self._make_monitor(mock_web3)
        with pytest.raises(ValueError):
            monitor.on_block_interval(0, lambda e: None)

    def test_trigger_action_failure_does_not_break_loop(self, mock_web3):
        monitor = self._make_monitor(mock_web3)

        def _boom(event: dict) -> None:
            raise RuntimeError("action failed")

        monitor.on_low_balance(100, _boom)
        monitor._evaluate_low_balance(_ADDR, 1)  # must not raise

    def test_kill_switch_stops_monitor_loop(self, mock_web3, tmp_path):
        monitor = self._make_monitor(mock_web3)
        with patch("arc_devkit.agents.guardrails.kill_switch_active", return_value=True):
            result = monitor.execute(max_iterations=5)
        assert result["status"] == "killed"
        assert result["iterations"] == 0


# ---------------------------------------------------------------------------
# AutoRefueler
# ---------------------------------------------------------------------------


class TestAutoRefueler:
    def _make_refueler(self, tmp_path, payment_result: dict):
        from arc_devkit.agents.autonomous import AutoRefueler
        from arc_devkit.agents.guardrails import Guardrails

        payment_agent = MagicMock()
        payment_agent._guardrails = None
        payment_agent.execute.return_value = payment_result
        guardrails = Guardrails(state_dir=tmp_path)

        refueler = AutoRefueler(
            target_address=_ADDR,
            threshold_usdc=Decimal("0.5"),
            top_up_amount_usdc=Decimal("1.0"),
            payment_agent=payment_agent,
            guardrails=guardrails,
        )
        return refueler, payment_agent

    def test_attach_registers_low_balance_trigger(self, mock_web3, tmp_path):
        from arc_devkit.agents.monitor_agent import MonitorAgent

        refueler, _ = self._make_refueler(tmp_path, {"status": "sent", "tx_hash": "0xabc"})
        monitor = MonitorAgent(watched_address=_ADDR, interval_seconds=1)
        refueler.attach(monitor)
        assert len(monitor._low_balance_triggers) == 1
        # threshold 0.5 USDC = 5e17 wei
        assert monitor._low_balance_triggers[0][0] == 5 * 10**17

    def test_refuel_executes_guarded_payment(self, tmp_path):
        refueler, payment_agent = self._make_refueler(
            tmp_path, {"status": "sent", "tx_hash": "0xabc"}
        )
        refueler._refuel({"address": _ADDR, "balance_wei": "10"})

        payment_agent.execute.assert_called_once()
        kwargs = payment_agent.execute.call_args.kwargs
        assert kwargs["enviar"] is True
        assert kwargs["trigger"] == "on_low_balance"
        assert kwargs["amount_usdc"] == 1.0

    def test_refuel_blocked_is_audited(self, tmp_path):
        refueler, _ = self._make_refueler(tmp_path, {"status": "blocked", "error": "whitelist"})
        refueler._refuel({"address": _ADDR, "balance_wei": "10"})

        audit = (tmp_path / "audit.log").read_text()
        assert "refuel_denied" in audit


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------


class TestEventBus:
    def test_publish_delivers_to_sync_and_async_handlers(self):
        from arc_devkit.agents.event_bus import EventBus

        bus = EventBus()
        received: list[dict] = []

        async def async_handler(event: dict) -> None:
            received.append({"async": True, **event})

        bus.subscribe("topic.a", received.append)
        bus.subscribe("topic.a", async_handler)

        delivered = asyncio.run(bus.publish("topic.a", {"x": 1}))
        assert delivered == 2
        assert len(received) == 2

    def test_handler_failure_is_isolated(self):
        from arc_devkit.agents.event_bus import EventBus

        bus = EventBus()
        received: list[dict] = []
        bus.subscribe("t", lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        bus.subscribe("t", received.append)

        asyncio.run(bus.publish("t", {"ok": True}))
        assert received == [{"ok": True}]

    def test_unsubscribe_and_history(self):
        from arc_devkit.agents.event_bus import EventBus

        bus = EventBus()
        handler = MagicMock()
        bus.subscribe("t", handler)
        bus.unsubscribe("t", handler)

        assert asyncio.run(bus.publish("t", {"n": 1})) == 0
        assert bus.history == [("t", {"n": 1})]

    def test_publish_sync_without_running_loop(self):
        from arc_devkit.agents.event_bus import EventBus

        bus = EventBus()
        received: list[dict] = []
        bus.subscribe("t", received.append)
        bus.publish_sync("t", {"n": 2})
        assert received == [{"n": 2}]


# ---------------------------------------------------------------------------
# CoordinatorAgent
# ---------------------------------------------------------------------------


class TestCoordinator:
    def test_plan_uses_copilot_agent_mode(self, tmp_path):
        from arc_devkit.agents.coordinator import CoordinatorAgent
        from arc_devkit.agents.guardrails import Guardrails

        coordinator = CoordinatorAgent(guardrails=Guardrails(state_dir=tmp_path))
        with patch(
            "arc_devkit.copilot.agent.DevCopilot.run_agent",
            return_value={"response": "1. check balance", "tool_calls": [], "iterations": 1},
        ) as mock_run:
            result = coordinator.plan("keep wallet funded")

        assert result["response"] == "1. check balance"
        assert "keep wallet funded" in mock_run.call_args.args[0]
        assert "generate_plan" in (tmp_path / "audit.log").read_text()

    def test_execute_transfer_requires_payment_agent(self, tmp_path):
        from arc_devkit.agents.coordinator import CoordinatorAgent
        from arc_devkit.agents.guardrails import Guardrails

        coordinator = CoordinatorAgent(guardrails=Guardrails(state_dir=tmp_path))
        result = coordinator.execute_transfer(_ADDR, 1.0)
        assert result["status"] == "error"

    def test_execute_transfer_delegates_to_guarded_agent(self, tmp_path):
        from arc_devkit.agents.coordinator import CoordinatorAgent
        from arc_devkit.agents.guardrails import Guardrails

        coordinator = CoordinatorAgent(guardrails=Guardrails(state_dir=tmp_path))
        agent = MagicMock()
        agent._guardrails = None
        agent.execute.return_value = {"status": "sent", "tx_hash": "0xabc"}
        coordinator.register_payment_agent(agent)

        result = coordinator.execute_transfer(_ADDR, 1.0, trigger="test")
        assert result["status"] == "sent"
        assert agent._guardrails is not None  # guardrails were injected

    def test_hire_agent_requires_payment_agent(self, tmp_path):
        from arc_devkit.agents.coordinator import CoordinatorAgent
        from arc_devkit.agents.guardrails import Guardrails

        coordinator = CoordinatorAgent(guardrails=Guardrails(state_dir=tmp_path))
        job = coordinator.hire_agent(MagicMock(), _ADDR, 25.0, "summarize this PDF")
        assert job.error is not None

    def test_hire_agent_delegates_to_job_registry(self, tmp_path):
        from decimal import Decimal

        from arc_devkit.agents.coordinator import CoordinatorAgent
        from arc_devkit.agents.guardrails import Guardrails
        from arc_devkit.agents.jobs import Job

        coordinator = CoordinatorAgent(guardrails=Guardrails(state_dir=tmp_path))
        payment_agent = MagicMock()
        payment_agent._guardrails = None
        payment_agent._private_key = (
            "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        )
        coordinator.register_payment_agent(payment_agent)

        job_registry = MagicMock()
        job_registry.create_job.return_value = Job(
            job_id=1, requester=_ADDR, agent=_ADDR, amount_usdc=Decimal("25"), spec="spec"
        )

        job = coordinator.hire_agent(job_registry, _ADDR, 25.0, "summarize this PDF")

        assert job.job_id == 1
        job_registry.create_job.assert_called_once_with(
            _ADDR, Decimal("25.0"), "summarize this PDF", payment_agent._private_key
        )


# ---------------------------------------------------------------------------
# AgentDashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_run_renders_and_returns_monitor_result(self):
        from arc_devkit.agents.dashboard import AgentDashboard

        monitor = MagicMock()
        monitor.get_balance.return_value = {
            _ADDR: {"address": _ADDR, "balance_wei": str(10**18), "balance_eth": "1"}
        }

        def _execute(callback=None, max_iterations=0):
            callback({"type": "credit", "change_wei": "500", "event_type": "native"})
            return {"status": "done", "iterations": 1}

        monitor.execute.side_effect = _execute

        dashboard = AgentDashboard(monitor)
        result = dashboard.run(max_iterations=1)

        assert result["status"] == "done"
        assert len(dashboard._events) == 1
