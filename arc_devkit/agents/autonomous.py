"""Autonomous agent behaviors — actions that run without a human in the loop.

Every autonomous behavior REQUIRES Guardrails: kill switch, recipient whitelist,
and daily spend limit are enforced on each action, and every execution is
recorded in the audit log.
"""

import logging
from decimal import Decimal

from arc_devkit.agents.guardrails import Guardrails
from arc_devkit.agents.monitor_agent import MonitorAgent
from arc_devkit.agents.payment_agent import PaymentAgent
from arc_devkit.core.validation import validate_address, validate_amount

logger = logging.getLogger(__name__)


class AutoRefueler:
    """
    Keeps a target address funded: when its native balance drops below a
    threshold, a PaymentAgent automatically tops it up.

    The refuel transfer goes through all guardrails (kill switch, whitelist,
    daily spend limit) and mandatory simulation before broadcast.

    Example:
        guardrails = Guardrails.from_settings()
        refueler = AutoRefueler(
            target_address="0xServiceWallet...",
            threshold_usdc=Decimal("0.5"),
            top_up_amount_usdc=Decimal("1.0"),
            payment_agent=PaymentAgent(guardrails=guardrails),
            guardrails=guardrails,
        )
        monitor = MonitorAgent(watched_address="0xServiceWallet...", interval_seconds=30)
        refueler.attach(monitor)
        monitor.execute()
    """

    def __init__(
        self,
        target_address: str,
        threshold_usdc: Decimal,
        top_up_amount_usdc: Decimal,
        payment_agent: PaymentAgent,
        guardrails: Guardrails,
    ) -> None:
        """
        Args:
            target_address: Address to keep funded.
            threshold_usdc: Refuel when balance drops below this value.
            top_up_amount_usdc: Amount transferred on each refuel.
            payment_agent: Funded PaymentAgent used to send the top-up.
            guardrails: Required autonomy guardrails.
        """
        self._target = validate_address(target_address)
        self._threshold = validate_amount(threshold_usdc)
        self._top_up = validate_amount(top_up_amount_usdc)
        self._payment_agent = payment_agent
        self._guardrails = guardrails
        # Ensure the payment agent enforces the same guardrails
        if self._payment_agent._guardrails is None:
            self._payment_agent._guardrails = guardrails

    def attach(self, monitor: MonitorAgent) -> None:
        """Register the refuel action on a monitor's low-balance trigger."""
        threshold_wei = int(self._threshold * Decimal(10**18))
        monitor.on_low_balance(threshold_wei, self._refuel)
        logger.info(
            "AutoRefueler attached: %s below %s USDC → top up %s USDC",
            self._target[:10],
            self._threshold,
            self._top_up,
        )

    def _refuel(self, event: dict) -> None:
        """Trigger action: execute the guarded top-up transfer."""
        address = event.get("address", self._target)
        logger.info(
            "AutoRefueler firing for %s (balance %s wei)", address, event.get("balance_wei")
        )

        result = self._payment_agent.execute(
            to=self._target,
            amount_usdc=float(self._top_up),
            enviar=True,
            wait_receipt=False,
            trigger="on_low_balance",
        )

        status = result.get("status")
        if status in {"blocked", "error", "simulation_failed"}:
            logger.warning("AutoRefueler blocked/failed: %s", result.get("error"))
            self._guardrails.audit(
                agent="AutoRefueler",
                trigger="on_low_balance",
                action="refuel_denied",
                target=self._target,
                reason=result.get("error", status),
            )
        else:
            logger.info(
                "AutoRefueler sent %s USDC → %s (%s)",
                self._top_up,
                self._target,
                result.get("tx_hash"),
            )
