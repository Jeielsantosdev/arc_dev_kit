"""Coordinator agent — plans multi-agent workflows from natural-language goals.

The coordinator uses the DevCopilot in agentic mode (read-only tools) to inspect
on-chain state and produce an execution plan. Steps that move funds are only
executed when a PaymentAgent with Guardrails is registered — and every action
passes the kill switch, whitelist, and spend-limit checks.
"""

import logging

from arc_devkit.agents.event_bus import EventBus
from arc_devkit.agents.guardrails import Guardrails
from arc_devkit.agents.jobs import Job, JobRegistry
from arc_devkit.agents.monitor_agent import MonitorAgent
from arc_devkit.agents.payment_agent import PaymentAgent

logger = logging.getLogger(__name__)

_PLAN_PROMPT = """\
You are coordinating economic agents on the Arc blockchain. Analyze the goal
below using your read-only tools (balances, gas, block info) and produce a plan.

Goal: {goal}

Respond with:
1. **Current state** — relevant on-chain data you gathered
2. **Plan** — numbered steps; mark each step as [read-only] or [requires-funds]
3. **Risks** — what could go wrong and which guardrails apply
"""


class CoordinatorAgent:
    """
    Orchestrates DevCopilot, PaymentAgent, and MonitorAgent around a goal.

    Example:
        coordinator = CoordinatorAgent(guardrails=Guardrails.from_settings())
        coordinator.register_payment_agent(PaymentAgent(guardrails=guardrails))
        result = coordinator.plan("keep 0xAbc... above 0.5 USDC")
    """

    def __init__(self, guardrails: Guardrails | None = None, bus: EventBus | None = None) -> None:
        self._guardrails = guardrails or Guardrails.from_settings()
        self.bus = bus or EventBus()
        self._payment_agent: PaymentAgent | None = None
        self._monitors: list[MonitorAgent] = []

    def register_payment_agent(self, agent: PaymentAgent) -> None:
        """Register the payment agent used for fund-moving steps (guardrails enforced)."""
        if agent._guardrails is None:
            agent._guardrails = self._guardrails
        self._payment_agent = agent

    def register_monitor(self, monitor: MonitorAgent) -> None:
        """Register a monitor whose events feed the coordinator's bus."""
        self._monitors.append(monitor)

    def plan(self, goal: str, max_iterations: int = 10) -> dict:
        """
        Produce an execution plan for a natural-language goal.

        Uses DevCopilot agentic mode with read-only tools; no funds are moved.

        Returns:
            Dict with 'response' (the plan), 'tool_calls', and 'iterations'.
        """
        from arc_devkit.copilot.agent import DevCopilot

        self._guardrails.check_kill_switch()
        copilot = DevCopilot()
        result = copilot.run_agent(_PLAN_PROMPT.format(goal=goal), max_iterations=max_iterations)
        self.bus.publish_sync("coordinator.plan", {"goal": goal, "plan": result["response"]})
        self._guardrails.audit(
            agent="CoordinatorAgent",
            trigger="plan",
            action="generate_plan",
            goal=goal,
            tool_calls=len(result["tool_calls"]),
        )
        return result

    def execute_transfer(self, to: str, amount_usdc: float, trigger: str = "coordinator") -> dict:
        """
        Execute a fund-moving step through the registered (guarded) PaymentAgent.

        Returns:
            The PaymentAgent result dict; status "blocked" when a guardrail denies it.
        """
        if self._payment_agent is None:
            return {"status": "error", "error": "No PaymentAgent registered."}
        result = self._payment_agent.execute(
            to=to, amount_usdc=amount_usdc, enviar=True, trigger=trigger
        )
        self.bus.publish_sync("coordinator.transfer", {"to": to, "result": result})
        return result

    def hire_agent(
        self,
        job_registry: JobRegistry,
        agent_address: str,
        amount_usdc: float,
        spec: str,
    ) -> Job:
        """
        Create a job (with USDC escrow) hiring another agent — planning a
        workflow that contracts other agents via ERC-8183 jobs.

        Requires a PaymentAgent registered with a private key (its wallet
        signs the job-creation tx and funds the escrow). The caller must have
        already approved `job_registry`'s contract to spend `amount_usdc` USDC.
        """
        from decimal import Decimal

        if self._payment_agent is None or self._payment_agent._private_key is None:
            return Job(
                job_id=0,
                requester="",
                agent=agent_address,
                amount_usdc=Decimal(str(amount_usdc)),
                spec=spec,
                error="No PaymentAgent with a private key registered.",
            )

        job = job_registry.create_job(
            agent_address,
            Decimal(str(amount_usdc)),
            spec,
            self._payment_agent._private_key,
        )
        self.bus.publish_sync(
            "coordinator.hire", {"agent": agent_address, "job_id": job.job_id, "spec": spec}
        )
        return job

    def maintain_balance(
        self,
        address: str,
        min_usdc: float,
        top_up_usdc: float,
        interval_seconds: int = 30,
        max_iterations: int = 0,
    ) -> dict:
        """
        Declarative workflow: keep an address above a minimum balance.

        Wires an AutoRefueler to a MonitorAgent and runs the monitoring loop
        (blocking). Requires a registered PaymentAgent with funds.
        """
        from decimal import Decimal

        from arc_devkit.agents.autonomous import AutoRefueler

        if self._payment_agent is None:
            return {"status": "error", "error": "No PaymentAgent registered."}

        monitor = MonitorAgent(watched_address=address, interval_seconds=interval_seconds)
        refueler = AutoRefueler(
            target_address=address,
            threshold_usdc=Decimal(str(min_usdc)),
            top_up_amount_usdc=Decimal(str(top_up_usdc)),
            payment_agent=self._payment_agent,
            guardrails=self._guardrails,
        )
        refueler.attach(monitor)
        self.register_monitor(monitor)
        logger.info("maintain_balance workflow started for %s", address)
        return monitor.execute(max_iterations=max_iterations)
