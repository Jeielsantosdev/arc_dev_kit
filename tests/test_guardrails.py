"""Unit tests for autonomous-agent guardrails."""

import json
from decimal import Decimal

import pytest

from arc_devkit.agents.guardrails import (
    Guardrails,
    GuardrailViolation,
    activate_kill_switch,
    clear_kill_switch,
    kill_switch_active,
)

_ADDR_OK = "0x" + "b" * 40
_ADDR_OTHER = "0x" + "c" * 40


class TestKillSwitch:
    def test_activate_and_clear(self, tmp_path):
        assert not kill_switch_active(tmp_path)
        activate_kill_switch(tmp_path)
        assert kill_switch_active(tmp_path)
        assert clear_kill_switch(tmp_path) is True
        assert not kill_switch_active(tmp_path)

    def test_clear_when_inactive_returns_false(self, tmp_path):
        assert clear_kill_switch(tmp_path) is False

    def test_guardrails_check_raises_when_active(self, tmp_path):
        g = Guardrails(state_dir=tmp_path)
        activate_kill_switch(tmp_path)
        with pytest.raises(GuardrailViolation):
            g.check_kill_switch()


class TestRecipientWhitelist:
    def test_whitelisted_recipient_passes(self, tmp_path):
        g = Guardrails(allowed_recipients=[_ADDR_OK], state_dir=tmp_path)
        g.check_recipient(_ADDR_OK)  # no raise

    def test_non_whitelisted_recipient_blocked(self, tmp_path):
        g = Guardrails(allowed_recipients=[_ADDR_OK], state_dir=tmp_path)
        with pytest.raises(GuardrailViolation):
            g.check_recipient(_ADDR_OTHER)

    def test_empty_whitelist_allows_all(self, tmp_path):
        g = Guardrails(state_dir=tmp_path)
        g.check_recipient(_ADDR_OTHER)  # no raise, just a warning log


class TestSpendLimit:
    def test_within_limit_passes(self, tmp_path):
        g = Guardrails(max_spend_per_day_usdc=Decimal("10"), state_dir=tmp_path)
        g.check_spend(Decimal("5"))
        g.record_spend(Decimal("5"))
        g.check_spend(Decimal("4"))  # 5 + 4 <= 10

    def test_exceeding_limit_blocked(self, tmp_path):
        g = Guardrails(max_spend_per_day_usdc=Decimal("10"), state_dir=tmp_path)
        g.record_spend(Decimal("8"))
        with pytest.raises(GuardrailViolation):
            g.check_spend(Decimal("3"))

    def test_no_limit_configured_allows_any(self, tmp_path):
        g = Guardrails(state_dir=tmp_path)
        g.check_spend(Decimal("1000000"))  # no raise

    def test_spend_persists_across_instances(self, tmp_path):
        Guardrails(max_spend_per_day_usdc=Decimal("10"), state_dir=tmp_path).record_spend(
            Decimal("9")
        )
        g2 = Guardrails(max_spend_per_day_usdc=Decimal("10"), state_dir=tmp_path)
        with pytest.raises(GuardrailViolation):
            g2.check_spend(Decimal("2"))


class TestAuditLog:
    def test_audit_appends_json_lines(self, tmp_path):
        g = Guardrails(state_dir=tmp_path)
        g.audit(agent="PaymentAgent", trigger="manual", action="transfer", amount_usdc=1.5)
        g.audit(agent="AutoRefueler", trigger="on_low_balance", action="refuel_denied")

        lines = (tmp_path / "audit.log").read_text().strip().splitlines()
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["agent"] == "PaymentAgent"
        assert first["action"] == "transfer"
        assert "timestamp" in first
