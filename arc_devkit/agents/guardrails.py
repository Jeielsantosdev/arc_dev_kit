"""Guardrails for autonomous agent actions — spend limits, whitelists, audit log, kill switch.

Any action executed without a human in the loop must pass through these checks:

    guardrails = Guardrails.from_settings()
    guardrails.check_recipient(to)
    guardrails.check_spend(amount)
    ... broadcast ...
    guardrails.record_spend(amount)
    guardrails.audit(agent="PaymentAgent", trigger="on_low_balance", action="transfer", ...)
"""

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from arc_devkit.core.validation import validate_address

logger = logging.getLogger(__name__)

_STATE_DIR = Path.home() / ".arc_devkit"
_KILL_SWITCH_FILE = _STATE_DIR / "agents.stop"
_SPEND_FILE = _STATE_DIR / "spend_tracker.json"
_AUDIT_FILE = _STATE_DIR / "audit.log"


class GuardrailViolation(Exception):
    """Raised when an autonomous action violates a configured guardrail."""


def kill_switch_active(state_dir: Path | None = None) -> bool:
    """True when the kill switch file exists — all autonomous agents must halt."""
    path = (state_dir / "agents.stop") if state_dir else _KILL_SWITCH_FILE
    return path.exists()


def activate_kill_switch(state_dir: Path | None = None) -> Path:
    """Create the kill switch file, halting all autonomous agents."""
    path = (state_dir / "agents.stop") if state_dir else _KILL_SWITCH_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(datetime.now(UTC).isoformat())
    logger.warning("Kill switch ACTIVATED: %s", path)
    return path


def clear_kill_switch(state_dir: Path | None = None) -> bool:
    """Remove the kill switch file; returns True if it existed."""
    path = (state_dir / "agents.stop") if state_dir else _KILL_SWITCH_FILE
    if path.exists():
        path.unlink()
        logger.info("Kill switch cleared: %s", path)
        return True
    return False


class Guardrails:
    """
    Enforces autonomy limits for agents that act without human confirmation.

    Args:
        max_spend_per_day_usdc: Daily spend ceiling; None disables the check.
        allowed_recipients: Whitelist of recipient addresses; empty allows any
                            (a warning is logged — configure a whitelist in production).
        state_dir: Directory for the spend tracker, audit log, and kill switch.
    """

    def __init__(
        self,
        max_spend_per_day_usdc: Decimal | None = None,
        allowed_recipients: tuple[str, ...] | list[str] = (),
        state_dir: str | Path | None = None,
    ) -> None:
        self._max_spend = max_spend_per_day_usdc
        self._whitelist = {validate_address(a).lower() for a in allowed_recipients}
        self._state_dir = Path(state_dir) if state_dir else _STATE_DIR
        self._state_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_settings(cls) -> "Guardrails":
        """Build guardrails from MAX_SPEND_PER_DAY_USDC and AGENT_ALLOWED_RECIPIENTS."""
        from arc_devkit.config import settings

        return cls(
            max_spend_per_day_usdc=settings.max_spend_per_day_usdc,
            allowed_recipients=settings.agent_allowed_recipients,
        )

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check_kill_switch(self) -> None:
        """Raise if the kill switch is active."""
        if kill_switch_active(self._state_dir):
            raise GuardrailViolation(
                "Kill switch is active — autonomous actions are halted. "
                "Run 'arcdevkit agent resume' to re-enable."
            )

    def check_recipient(self, to: str) -> None:
        """Raise if the recipient is not on the configured whitelist."""
        if not self._whitelist:
            logger.warning(
                "No recipient whitelist configured (AGENT_ALLOWED_RECIPIENTS) — "
                "autonomous transfers are unrestricted by destination."
            )
            return
        if validate_address(to).lower() not in self._whitelist:
            raise GuardrailViolation(f"Recipient {to} is not on the autonomous-agent whitelist.")

    def _spent_today(self) -> Decimal:
        spend_file = self._state_dir / "spend_tracker.json"
        today = datetime.now(UTC).date().isoformat()
        if spend_file.exists():
            try:
                data = json.loads(spend_file.read_text())
                if data.get("date") == today:
                    return Decimal(data.get("spent", "0"))
            except Exception as exc:
                logger.warning("Failed to read spend tracker: %s", exc)
        return Decimal("0")

    def check_spend(self, amount: Decimal) -> None:
        """Raise if amount would exceed the daily spend ceiling."""
        if self._max_spend is None:
            return
        spent = self._spent_today()
        if spent + amount > self._max_spend:
            raise GuardrailViolation(
                f"Daily spend limit exceeded: {spent} + {amount} > "
                f"{self._max_spend} USDC (MAX_SPEND_PER_DAY_USDC)."
            )

    def record_spend(self, amount: Decimal) -> None:
        """Persist a completed spend against today's counter."""
        spend_file = self._state_dir / "spend_tracker.json"
        today = datetime.now(UTC).date().isoformat()
        total = self._spent_today() + amount
        spend_file.write_text(json.dumps({"date": today, "spent": str(total)}))

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def audit(self, agent: str, trigger: str, action: str, **details: object) -> None:
        """Append an autonomous-action record to the audit log (JSON lines)."""
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "agent": agent,
            "trigger": trigger,
            "action": action,
            **{k: str(v) for k, v in details.items()},
        }
        audit_file = self._state_dir / "audit.log"
        try:
            with audit_file.open("a") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.error("Failed to write audit log: %s", exc)
        logger.info("AUDIT %s", record)
